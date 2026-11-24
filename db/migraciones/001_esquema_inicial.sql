-- =====================================================================
-- GASTRO-SIM · Diseño físico de la base de datos · v1.0 · 25/10/2026
-- SGBD: PostgreSQL 15 (Supabase). Equipo ITEVOLUTION.
-- Ejecutar en el editor SQL de Supabase o con: psql -f este_archivo.sql
-- Las contraseñas y los factores TOTP los gestiona Supabase Auth (esquema auth).
-- =====================================================================
create extension if not exists pgcrypto;

-- ---------- Tipos de dominio ----------
create type rol_t           as enum ('estudiante', 'docente', 'admin');
create type region_t        as enum ('esofago', 'estomago', 'duodeno');
create type dificultad_t    as enum ('basico', 'intermedio', 'avanzado');
create type estado_caso_t   as enum ('pendiente', 'aprobado', 'descartado');
create type estado_intento_t as enum ('explorando', 'hallazgo_capturado', 'decision_inicial',
                                      'recomendacion', 'finalizado', 'abandonado');

-- Los datos de investigación se separan de los datos de cuenta (RNF-08)
create schema if not exists investigacion;

-- =====================================================================
-- 1. Cuentas, roles y gamificación  (EDT 4.6 y 4.5)
-- =====================================================================
create table public.grupo (
  id          uuid primary key default gen_random_uuid(),
  nombre      text not null,
  periodo     text not null,                         -- ej. 2026-B
  docente_id  uuid,                                  -- FK agregada tras crear perfil
  creado_en   timestamptz not null default now(),
  unique (nombre, periodo)
);

create table public.perfil (
  id                 uuid primary key references auth.users(id) on delete cascade,
  nombre_visible     text not null check (length(nombre_visible) between 1 and 60),
  rol                rol_t not null default 'estudiante',          -- RF-01.1
  grupo_id           uuid references public.grupo(id) on delete set null,
  seudonimo          uuid not null unique default gen_random_uuid(), -- RF-15, RNF-08
  aviso_aceptado_en  timestamptz,                                  -- RF-01.4
  version_aviso      text,
  mfa_activado       boolean not null default false,               -- RF-01.6
  puntos             integer not null default 0 check (puntos >= 0), -- RF-11
  nivel              smallint not null default 1 check (nivel between 1 and 10),
  creado_en          timestamptz not null default now()
);
alter table public.grupo
  add constraint grupo_docente_fk foreign key (docente_id) references public.perfil(id) on delete set null;

-- RF-01.1: al registrarse en Supabase Auth se crea el perfil con rol estudiante
create function public.crear_perfil() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.perfil (id, nombre_visible)
  values (new.id, left(coalesce(nullif(split_part(new.email, '@', 1), ''), 'usuario'), 60));
  return new;
end $$;
create trigger al_registrar_usuario after insert on auth.users
  for each row execute function public.crear_perfil();

create table public.codigo_recuperacion (             -- RF-01.6: 10 códigos de un solo uso
  id           uuid primary key default gen_random_uuid(),
  perfil_id    uuid not null references public.perfil(id) on delete cascade,
  codigo_hash  text not null,                         -- crypt(codigo, gen_salt('bf')); nunca en claro
  usado_en     timestamptz,
  creado_en    timestamptz not null default now()
);

create table public.auditoria_cuenta (                -- RF-01.3 y RF-01.7
  id           bigint generated always as identity primary key,
  actor_id     uuid not null references public.perfil(id),
  afectado_id  uuid not null references public.perfil(id),
  accion       text not null check (accion in ('asignar_rol', 'retirar_rol', 'restablecer_2fa')),
  detalle      jsonb not null default '{}',
  creado_en    timestamptz not null default now()
);

create table public.insignia (                        -- RF-11
  id           smallint generated always as identity primary key,
  codigo       text not null unique,
  nombre       text not null,
  descripcion  text not null,
  criterio     jsonb not null                         -- ej. {"errores_ia_detectados": 1}
);

create table public.perfil_insignia (
  perfil_id    uuid references public.perfil(id) on delete cascade,
  insignia_id  smallint references public.insignia(id),
  obtenida_en  timestamptz not null default now(),
  primary key (perfil_id, insignia_id)
);

-- =====================================================================
-- 2. Contenido: dataset, IA de visión y casos  (EDT 4.2, 4.3, 4.1)
-- =====================================================================
create table public.clase_hallazgo (
  id             smallint generated always as identity primary key,
  codigo         text not null unique,                -- etiqueta HyperKvasir
  nombre_es      text not null,
  region         region_t not null,
  es_patologico  boolean not null
);

create table public.hito_anatomico (                  -- RF-03.3
  id      smallint generated always as identity primary key,
  codigo  text not null unique,
  nombre  text not null,
  region  region_t not null,
  orden   smallint not null unique
);

create table public.ubicacion_3d (                    -- RF-14.3: tabla de correspondencia clase → ruta 3D
  id        integer generated always as identity primary key,
  clase_id  smallint not null references public.clase_hallazgo(id),
  hito_id   smallint not null references public.hito_anatomico(id),
  x real not null, y real not null, z real not null,
  radio_visibilidad real not null default 1.5 check (radio_visibilidad > 0)
);

create table public.imagen (                          -- RF-14.1
  id              integer generated always as identity primary key,
  archivo_origen  text not null unique,               -- nombre en HyperKvasir
  ruta_storage    text not null,                      -- bucket imagenes
  clase_id        smallint not null references public.clase_hallazgo(id),
  dificultad      dificultad_t not null,
  licencia        text not null default 'CC BY 4.0',
  sha256          char(64) not null unique,
  activa          boolean not null default true
);

create table public.prediccion (                      -- RF-06.1, RF-06.2, RF-06.3 (precalculada)
  id                 integer generated always as identity primary key,
  imagen_id          integer not null references public.imagen(id) on delete cascade,
  version_modelo     text not null,
  clase_predicha_id  smallint not null references public.clase_hallazgo(id),
  confianza          numeric(5,4) not null check (confianza between 0 and 1),
  roi_x real not null check (roi_x between 0 and 1),  -- coordenadas normalizadas
  roi_y real not null check (roi_y between 0 and 1),
  roi_w real not null check (roi_w > 0 and roi_w <= 1),
  roi_h real not null check (roi_h > 0 and roi_h <= 1),
  ruta_gradcam       text,
  creado_en          timestamptz not null default now(),
  unique (imagen_id, version_modelo)
);

create table public.caso (                            -- RF-14.2 a RF-14.6
  id                   uuid primary key default gen_random_uuid(),
  imagen_id            integer not null references public.imagen(id),
  ubicacion_id         integer not null references public.ubicacion_3d(id),
  dificultad           dificultad_t not null,
  historia             jsonb not null,                -- {edad, sexo, motivo, antecedentes, sintomas, texto}
  referencia_id        smallint not null references public.clase_hallazgo(id),
  modelo_llm           text not null,
  version_prompt       text not null,
  semilla              integer not null,
  validacion           jsonb not null,                -- resultado de cada validador
  tiempo_generacion_ms integer check (tiempo_generacion_ms >= 0),  -- RNF-14
  estado               estado_caso_t not null default 'pendiente',
  motivo_descarte      text,
  revisado_por         uuid references public.perfil(id),
  revisado_en          timestamptz,
  creado_en            timestamptz not null default now(),
  check (historia ? 'edad' and historia ? 'motivo' and historia ? 'sintomas'),
  check (estado <> 'descartado' or motivo_descarte is not null)
);

create table public.reporte_caso (                    -- RF-14.7
  id          integer generated always as identity primary key,
  caso_id     uuid not null references public.caso(id) on delete cascade,
  perfil_id   uuid not null references public.perfil(id) on delete cascade,
  comentario  text not null check (length(comentario) between 5 and 1000),
  estado      text not null default 'abierto' check (estado in ('abierto', 'atendido')),
  creado_en   timestamptz not null default now()
);

create table public.generacion_fallida (               -- RF-14.4: registro tras 3 intentos fallidos
  id          bigint generated always as identity primary key,
  perfil_id   uuid not null references public.perfil(id) on delete cascade,
  dificultad  dificultad_t not null,
  region      region_t,                               -- null = aleatoria
  intentos    smallint not null check (intentos between 1 and 3),
  motivos     jsonb not null,                         -- motivo de rechazo de cada intento
  modelo_llm  text,
  creado_en   timestamptz not null default now()
);

create table public.config_alteracion (               -- RF-08.1, RF-08.2 (histórico: la vigente es la más reciente)
  id             integer generated always as identity primary key,
  grupo_id       uuid references public.grupo(id),    -- null = configuración global
  porcentaje     numeric(4,1) not null check (porcentaje between 0 and 50),
  tipos          text[] not null check (tipos <@ array['clase_incorrecta', 'confianza_alterada', 'roi_desplazada']),
  creado_por     uuid not null references public.perfil(id),
  vigente_desde  timestamptz not null default now()
);

-- =====================================================================
-- 3. Investigación: intentos, telemetría y tutor  (EDT 4.4 y 4.5)
--    Solo se identifica al participante por su seudónimo.
-- =====================================================================
create table investigacion.intento (
  id                      uuid primary key default gen_random_uuid(),
  participante            uuid not null references public.perfil(seudonimo) on update cascade,
  caso_id                 uuid not null references public.caso(id),
  config_id               integer references public.config_alteracion(id),
  estado                  estado_intento_t not null default 'explorando',
  decision_inicial_id     smallint references public.clase_hallazgo(id),     -- RF-05
  confianza_inicial       smallint check (confianza_inicial between 1 and 5),
  alterada                boolean,                                           -- RF-08.3
  tipo_alteracion         text check (tipo_alteracion in ('clase_incorrecta', 'confianza_alterada', 'roi_desplazada')),
  recomendacion_mostrada  jsonb,                                             -- lo que vio el usuario
  decision_final_id       smallint references public.clase_hallazgo(id),     -- RF-09
  confianza_final         smallint check (confianza_final between 1 and 5),
  cambio_decision         boolean generated always as (decision_final_id is distinct from decision_inicial_id) stored,
  acierto_usuario         boolean,                                           -- RF-10
  acierto_ia              boolean,
  puntaje                 integer check (puntaje >= 0),
  iniciado_en             timestamptz not null default now(),
  decision_inicial_en     timestamptz,
  finalizado_en           timestamptz,
  check (alterada is not true or tipo_alteracion is not null),
  check (estado <> 'finalizado' or (decision_inicial_id is not null and decision_final_id is not null))
);

create table investigacion.evento_telemetria (        -- RF-12, RF-03.3
  id           bigint generated always as identity primary key,
  intento_id   uuid not null references investigacion.intento(id) on delete cascade,
  tipo         text not null check (tipo in ('hito_visitado', 'hallazgo_capturado', 'hallazgo_omitido',
                                              'captura_invalida', 'pausa', 'reanudacion')),
  datos        jsonb not null default '{}',
  ocurrido_en  timestamptz not null
);

create table investigacion.mensaje_tutor (            -- RF-07.1 a RF-07.3, RNF-03
  id           bigint generated always as identity primary key,
  intento_id   uuid not null references investigacion.intento(id) on delete cascade,
  emisor       text not null check (emisor in ('estudiante', 'tutor', 'sistema')),
  contenido    text not null check (length(contenido) <= 4000),
  modelo_llm   text,
  latencia_ms  integer check (latencia_ms >= 0),
  es_respaldo  boolean not null default false,
  creado_en    timestamptz not null default now()
);

-- =====================================================================
-- 4. Índices (fase 5: optimización según las consultas frecuentes)
-- =====================================================================
create index ix_perfil_grupo          on public.perfil (grupo_id);
create index ix_codigo_rec_perfil     on public.codigo_recuperacion (perfil_id) where usado_en is null;
create index ix_imagen_seleccion      on public.imagen (clase_id, dificultad) where activa;
create index ix_ubicacion_clase       on public.ubicacion_3d (clase_id);
create index ix_caso_estado           on public.caso (estado, dificultad);
create index ix_caso_imagen           on public.caso (imagen_id);
create index ix_reporte_abierto       on public.reporte_caso (caso_id) where estado = 'abierto';
create index ix_config_vigente        on public.config_alteracion (grupo_id, vigente_desde desc);
create index ix_intento_participante  on investigacion.intento (participante, iniciado_en desc);
create index ix_intento_caso          on investigacion.intento (caso_id);
create index ix_evento_intento        on investigacion.evento_telemetria (intento_id, ocurrido_en);
create index ix_mensaje_intento       on investigacion.mensaje_tutor (intento_id, creado_en);

-- =====================================================================
-- 5. Vistas para tablero, clasificación y exportación
-- =====================================================================
create materialized view public.mv_desempeno as      -- RF-13 (se refresca al cerrar cada intento)
select i.participante,
       count(*)                                                     as intentos,
       avg(i.acierto_usuario::int)                                  as precision_decisiones,
       avg(case when i.alterada then (not (i.decision_final_id = (i.recomendacion_mostrada->>'clase_id')::smallint))::int end)
                                                                    as deteccion_errores_ia,
       avg(case when i.alterada then (i.decision_final_id = (i.recomendacion_mostrada->>'clase_id')::smallint)::int end)
                                                                    as sobre_dependencia,
       avg(i.confianza_final)                                       as confianza_media
from investigacion.intento i
where i.estado = 'finalizado'
group by i.participante;
create unique index ux_mv_desempeno on public.mv_desempeno (participante);

create view public.v_clasificacion_grupo as          -- RF-16
select p.grupo_id, p.seudonimo, p.puntos,
       rank() over (partition by p.grupo_id order by p.puntos desc) as puesto
from public.perfil p
where p.rol = 'estudiante';

create view investigacion.v_export_intentos as       -- RF-15: sin nombre ni correo
select i.participante, i.caso_id, c.dificultad, ch.codigo as referencia, i.alterada, i.tipo_alteracion,
       i.decision_inicial_id, i.confianza_inicial, i.decision_final_id, i.confianza_final, i.cambio_decision,
       i.acierto_usuario, i.acierto_ia, i.puntaje,
       extract(epoch from (i.finalizado_en - i.iniciado_en))::int as duracion_s,
       (select count(*) from investigacion.evento_telemetria e where e.intento_id = i.id and e.tipo = 'hito_visitado') as hitos_visitados,
       (select count(*) from investigacion.mensaje_tutor m where m.intento_id = i.id and m.emisor = 'estudiante') as mensajes_tutor,
       i.iniciado_en::date as fecha
from investigacion.intento i
join public.caso c on c.id = i.caso_id
join public.clase_hallazgo ch on ch.id = c.referencia_id
where i.estado = 'finalizado';

-- =====================================================================
-- 6. Seguridad: RLS activado en todas las tablas.
--    El navegador NO consulta tablas directamente: todo pasa por la API
--    (rol service_role), que valida el JWT con aal2. Así la respuesta de
--    referencia nunca llega al cliente antes de tiempo (RF-07.2, RNF-07).
-- =====================================================================
do $$
declare t text;
begin
  foreach t in array array['public.grupo','public.perfil','public.codigo_recuperacion','public.auditoria_cuenta',
    'public.insignia','public.perfil_insignia','public.clase_hallazgo','public.hito_anatomico','public.ubicacion_3d',
    'public.imagen','public.prediccion','public.caso','public.reporte_caso','public.generacion_fallida','public.config_alteracion',
    'investigacion.intento','investigacion.evento_telemetria','investigacion.mensaje_tutor']
  loop
    execute format('alter table %s enable row level security', t);
  end loop;
end $$;
-- Única política para el rol "authenticated": leer su propio perfil (para mostrar nombre y rol en la SPA).
create policy perfil_propio on public.perfil for select to authenticated using (id = auth.uid());
revoke all on schema investigacion from anon, authenticated;
revoke all on public.mv_desempeno from anon, authenticated;

-- =====================================================================
-- 7. Datos semilla (catálogos)
-- =====================================================================
insert into public.hito_anatomico (codigo, nombre, region, orden) values
 ('linea_z', 'Línea Z', 'esofago', 1), ('cardias', 'Cardias', 'estomago', 2), ('fondo', 'Fondo gástrico', 'estomago', 3),
 ('cuerpo', 'Cuerpo gástrico', 'estomago', 4), ('antro', 'Antro', 'estomago', 5), ('piloro', 'Píloro', 'estomago', 6),
 ('bulbo', 'Bulbo duodenal', 'duodeno', 7);

insert into public.clase_hallazgo (codigo, nombre_es, region, es_patologico) values
 ('z-line', 'Normal: línea Z', 'esofago', false),
 ('pylorus', 'Normal: píloro', 'estomago', false),
 ('retroflex-stomach', 'Normal: estómago en retroflexión', 'estomago', false),
 ('esophagitis-a', 'Esofagitis grado A', 'esofago', true),
 ('esophagitis-b-d', 'Esofagitis grado B–D', 'esofago', true),
 ('barretts', 'Esófago de Barrett', 'esofago', true),
 ('barretts-short-segment', 'Barrett de segmento corto', 'esofago', true);

insert into public.insignia (codigo, nombre, descripcion, criterio) values
 ('explorador', 'Explorador', 'Visitó los 7 hitos anatómicos en un caso', '{"hitos_visitados": 7}'),
 ('ojo_critico', 'Ojo crítico', 'Detectó una recomendación alterada de la IA', '{"errores_ia_detectados": 1}'),
 ('detector', 'Detector', 'Detectó 10 recomendaciones alteradas', '{"errores_ia_detectados": 10}'),
 ('constante', 'Constante', 'Completó 20 casos', '{"intentos_finalizados": 20}'),
 ('calibrado', 'Bien calibrado', 'Su confianza coincide con sus aciertos en 10 casos seguidos', '{"racha_calibrada": 10}');
-- Las coordenadas de ubicacion_3d se cargan cuando el modelo 3D (EDT 3.5) esté cerrado: db/semillas/ubicaciones.sql

-- =====================================================================
-- GASTRO-SIM · Migración 002: catálogo para generar casos clínicos
-- Responsable: Jahan Michelle Chará · Paquete 3.3 Modelo de datos
-- Requisitos: RF-14.1 (imagen), RF-14.3 (ubicación 3D), RF-14.5 (guardar)
--
-- Qué hace:
--   1. Llena ubicacion_3d: en qué punto de la ruta 3D aparece cada clase de
--      hallazgo. El generador de casos elige una de estas filas.
--   2. Crea el "bucket" privado imagenes en Supabase Storage, donde se suben
--      las imágenes de HyperKvasir. En la base local (Docker) no existe
--      Storage, así que ese paso se salta solo.
--   3. Agrega un índice para la bandeja de revisión del docente.
--
-- Se puede ejecutar más de una vez sin duplicar datos (idempotente).
-- Las coordenadas son una primera versión: Cristian las ajusta a la escena
-- 3D en la fase 4 con un UPDATE, sin cambiar el código de la API.
-- =====================================================================

-- ---------- 1. Ubicaciones de cada clase en la ruta 3D (RF-14.3) ----------
-- Eje y: profundidad del endoscopio (0 = boca, negativo = más adentro).
-- radio_visibilidad: distancia a la que el hallazgo se ve en la cámara.
insert into public.ubicacion_3d (clase_id, hito_id, x, y, z, radio_visibilidad)
select c.id, h.id, v.x::real, v.y::real, v.z::real, v.radio::real
from (values
  -- clase                     hito        x     y       z     radio
  ('z-line',                  'linea_z',  0.0, -20.0,  0.0,  1.5),
  ('esophagitis-a',           'linea_z',  0.3, -18.6,  0.2,  1.2),
  ('esophagitis-a',           'linea_z', -0.3, -19.0, -0.2,  1.2),
  ('esophagitis-b-d',         'linea_z',  0.0, -17.8,  0.4,  1.5),
  ('esophagitis-b-d',         'linea_z', -0.4, -18.4,  0.0,  1.5),
  ('barretts',                'linea_z',  0.2, -19.0,  0.0,  1.5),
  ('barretts-short-segment',  'linea_z',  0.0, -19.6,  0.2,  1.2),
  ('retroflex-stomach',       'cardias',  0.0, -22.5,  0.6,  2.0),
  ('pylorus',                 'piloro',   5.0, -28.0,  0.0,  1.8)
) as v(clase, hito, x, y, z, radio)
join public.clase_hallazgo c on c.codigo = v.clase
join public.hito_anatomico h on h.codigo = v.hito
where not exists (
  select 1 from public.ubicacion_3d u
  -- ::real: comparar con el mismo tipo de la columna (si no, 0.3 ≠ 0.3 y se duplicaría)
  where u.clase_id = c.id and u.x = v.x::real and u.y = v.y::real and u.z = v.z::real
);

-- ---------- 2. Bucket privado de imágenes (solo en Supabase) ----------
-- Privado: el navegador nunca lee el bucket directo; la API entrega una URL
-- firmada que vence en minutos (RNF-08).
do $$
begin
  if exists (select 1 from information_schema.schemata where schema_name = 'storage') then
    insert into storage.buckets (id, name, public)
    values ('imagenes', 'imagenes', false)
    on conflict (id) do nothing;
  end if;
end $$;

-- ---------- 3. Índice para la bandeja del docente (RF-14.6) ----------
-- La 001 ya trae el índice para elegir imagen (ix_imagen_seleccion).
-- Este ordena los casos por fecha dentro de cada estado.
create index if not exists ix_caso_estado_fecha
  on public.caso (estado, creado_en desc);

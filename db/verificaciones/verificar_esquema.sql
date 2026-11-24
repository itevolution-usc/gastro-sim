-- =====================================================================
-- GASTRO-SIM · Verificación del esquema en Supabase (solo lectura)
-- Responsable: Jahan Michelle Chará (paquete 3.3 · Modelo de datos)
--
-- Se ejecuta en Supabase → SQL Editor DESPUÉS de aplicar 001_esquema_inicial.sql.
-- No modifica nada: solo consulta. Cada fila debe decir "OK".
-- También funciona en la base local de Docker.
-- =====================================================================
with comprobaciones (orden, comprobacion, esperado, obtenido) as (
  values
  (1, 'Tablas en public e investigacion', '18',
      (select count(*)::text from information_schema.tables
        where table_schema in ('public', 'investigacion') and table_type = 'BASE TABLE')),
  (2, 'Tablas con RLS activado (RNF-07)', '18',
      (select count(*)::text from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname in ('public', 'investigacion') and c.relkind = 'r' and c.relrowsecurity)),
  (3, 'Disparador que crea el perfil al registrarse (RF-01.1)', '1',
      (select count(*)::text from pg_trigger where tgname = 'al_registrar_usuario' and not tgisinternal)),
  (4, 'Política: cada usuario lee solo su perfil', '1',
      (select count(*)::text from pg_policies where tablename = 'perfil' and policyname = 'perfil_propio')),
  (5, 'Hitos anatómicos (RF-03.3)', '7', (select count(*)::text from public.hito_anatomico)),
  (6, 'Clases de hallazgo del tracto superior', '7', (select count(*)::text from public.clase_hallazgo)),
  (7, 'Insignias (RF-11)', '5', (select count(*)::text from public.insignia)),
  (8, 'Tabla de códigos de recuperación (RF-01.6)', '1',
      (select count(*)::text from information_schema.tables
        where table_schema = 'public' and table_name = 'codigo_recuperacion')),
  (9, 'Esquema de investigación sin acceso para el navegador (RNF-08)', 'false',
      (select has_schema_privilege('authenticated', 'investigacion', 'USAGE')::text))
)
select orden, comprobacion, esperado, obtenido,
       case when esperado = obtenido then 'OK' else 'REVISAR' end as resultado
  from comprobaciones
 order by orden;

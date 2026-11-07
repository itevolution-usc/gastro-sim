-- =====================================================================
-- GASTRO-SIM · Migración 000 · SOLO PARA DESARROLLO LOCAL
-- Responsable: Jahan Michelle Chará (paquete 3.3 · Modelo de datos)
--
-- Supabase ya trae el esquema "auth", la función auth.uid() y los roles
-- "anon" y "authenticated". PostgreSQL local no los tiene, así que este
-- archivo los simula para que la migración 001 funcione igual en ambos.
--
-- ⚠️ NO ejecutar este archivo en Supabase.
-- =====================================================================
create schema if not exists auth;

-- Tabla mínima de usuarios: en Supabase la administra Auth.
create table if not exists auth.users (
  id    uuid primary key,
  email text unique
);

-- En Supabase devuelve el id del usuario del token; aquí no hay token.
create or replace function auth.uid() returns uuid
  language sql stable as 'select null::uuid';

-- Roles que usa Supabase para el navegador.
do $$
begin
  if not exists (select from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
end $$;

// Responsable: Cristian Cruz · Cliente de Supabase Auth
// El navegador usa Supabase SOLO para la autenticación (registro, contraseña y 2FA).
// Los datos (perfil, casos, intentos) siempre se piden a la API (ADR-04).
import { createClient } from '@supabase/supabase-js'

import { config, faltantes } from '../config'

// Con valores de relleno si falta la configuración: así la app puede mostrar
// la pantalla de ayuda en lugar de romperse al cargar.
export const supabase = createClient(
  faltantes.length ? 'https://sin-configurar.supabase.co' : config.supabaseUrl,
  faltantes.length ? 'sin-configurar' : config.supabaseAnonKey,
  { auth: { persistSession: true, autoRefreshToken: true } },
)

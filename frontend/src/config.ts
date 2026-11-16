// Responsable: Cristian Cruz · Lectura de la configuración del frontend (.env)
// Vite solo expone al navegador las variables que empiezan por VITE_.

export const config = {
  supabaseUrl: (import.meta.env.VITE_SUPABASE_URL ?? '').trim(),
  supabaseAnonKey: (import.meta.env.VITE_SUPABASE_ANON_KEY ?? '').trim(),
  apiUrl: (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').trim().replace(/\/$/, ''),
}

// Si falta algo, la app muestra una pantalla con instrucciones en lugar de fallar en silencio.
export const faltantes = [
  !config.supabaseUrl && 'VITE_SUPABASE_URL',
  !config.supabaseAnonKey && 'VITE_SUPABASE_ANON_KEY',
].filter(Boolean) as string[]

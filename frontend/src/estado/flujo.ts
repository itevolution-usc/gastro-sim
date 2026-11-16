// Responsable: Cristian Cruz · Reglas de navegación de la cuenta (RF-01.2, RF-01.4, RF-01.5)
// Función pura: recibe el estado de la sesión y decide a qué pantalla ir.
// Al no depender de React ni de Supabase, se prueba fácil (flujo.test.ts).
import type { Nivel } from '../servicios/auth'

export type Ruta = '/ingresar' | '/verificar' | '/activar' | '/inicio'

export interface EstadoCuenta {
  haySesion: boolean
  nivelActual: Nivel
  nivelSiguiente: Nivel
  perfil: { aviso_aceptado: boolean; mfa_activado: boolean } | null
}

export function siguientePantalla(e: EstadoCuenta): Ruta {
  // Sin sesión: a iniciar sesión (W01).
  if (!e.haySesion || !e.perfil) return '/ingresar'
  // Tiene 2FA activo pero aún no escribió el código en esta sesión: W04.
  if (e.nivelSiguiente === 'aal2' && e.nivelActual !== 'aal2') return '/verificar'
  // Falta el aviso, el 2FA o los códigos de recuperación: W03.
  if (!e.perfil.aviso_aceptado || e.nivelActual !== 'aal2' || !e.perfil.mfa_activado) return '/activar'
  // Todo en orden: inicio del estudiante (W06).
  return '/inicio'
}

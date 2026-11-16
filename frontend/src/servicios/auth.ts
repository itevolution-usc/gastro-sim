// Responsable: Cristian Cruz · Operaciones de autenticación con Supabase (patrón Facade)
// Las pantallas no hablan directamente con Supabase: llaman a estas funciones.
// Así, los mensajes de error quedan en español y en un solo lugar.
import { supabase } from './supabase'

export type Nivel = 'aal1' | 'aal2' | null

/** Traduce los errores más comunes de Supabase Auth al español. */
export function traducirError(mensaje: string): string {
  const m = mensaje.toLowerCase()
  if (m.includes('failed to fetch') || m.includes('network')) return 'No hay conexión con Supabase. Revisa tu internet y el archivo .env.'
  if (m.includes('invalid login credentials')) return 'Correo o contraseña incorrectos.'
  if (m.includes('email not confirmed')) return 'Debes confirmar tu correo antes de ingresar.'
  if (m.includes('user already registered')) return 'Ya existe una cuenta con ese correo.'
  if (m.includes('password should be')) return 'La contraseña no cumple los requisitos mínimos.'
  if (m.includes('rate limit')) return 'Demasiados intentos. Espera unos minutos.'
  if (m.includes('invalid totp') || m.includes('invalid code')) return 'Código incorrecto o vencido. Usa el código actual de tu app.'
  return mensaje
}

type Exito<R> = Exclude<R, { error: object }> extends { data: infer D } ? D : never

/** Supabase responde { data, error }: si hay error, se lanza en español; si no, se devuelven los datos. */
function revisar<R extends { data: unknown; error: { message: string } | null }>(resultado: R): Exito<R> {
  if (resultado.error) throw new Error(traducirError(resultado.error.message))
  return resultado.data as Exito<R>
}

export async function iniciarSesion(email: string, password: string) {
  revisar(await supabase.auth.signInWithPassword({ email, password }))
}

/** Devuelve true si la cuenta quedó con sesión; false si Supabase pide confirmar el correo. */
export async function registrar(email: string, password: string): Promise<boolean> {
  const datos = revisar(
    await supabase.auth.signUp({ email, password, options: { emailRedirectTo: window.location.origin } }),
  )
  return datos.session !== null
}

export async function cerrarSesion() {
  await supabase.auth.signOut()
}

/** Nivel actual de la sesión y el que podría alcanzar (aal2 si tiene 2FA activo). */
export async function niveles(): Promise<{ actual: Nivel; siguiente: Nivel }> {
  const datos = revisar(await supabase.auth.mfa.getAuthenticatorAssuranceLevel())
  return { actual: datos.currentLevel as Nivel, siguiente: datos.nextLevel as Nivel }
}

/** Paso 2 de W03: crea el factor TOTP y devuelve el QR para la app autenticadora. */
export async function iniciarActivacion() {
  // Borra intentos anteriores que quedaron a medias (factores sin verificar).
  const factores = revisar(await supabase.auth.mfa.listFactors())
  for (const f of factores.all) {
    if (f.factor_type === 'totp' && f.status === 'unverified') {
      revisar(await supabase.auth.mfa.unenroll({ factorId: f.id }))
    }
  }
  const datos = revisar(
    await supabase.auth.mfa.enroll({ factorType: 'totp', friendlyName: `GASTRO-SIM ${Date.now()}` }),
  )
  return { factorId: datos.id, qr: datos.totp.qr_code, secreto: datos.totp.secret }
}

/** Confirma el primer código: el factor queda activo y la sesión sube a aal2. */
export async function confirmarCodigo(factorId: string, codigo: string) {
  revisar(await supabase.auth.mfa.challengeAndVerify({ factorId, code: codigo }))
}

/** W04: verifica el código con el factor ya activo de la cuenta. */
export async function verificarCodigo(codigo: string) {
  const factores = revisar(await supabase.auth.mfa.listFactors())
  const factor = factores.totp[0]
  if (!factor) throw new Error('Esta cuenta no tiene 2FA activo.')
  await confirmarCodigo(factor.id, codigo)
}

/** Tras usar un código de recuperación: renueva el token para que refleje que ya no hay 2FA. */
export async function renovarSesion() {
  revisar(await supabase.auth.refreshSession())
}

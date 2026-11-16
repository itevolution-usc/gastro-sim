// Responsable: Cristian Cruz · Conexión con la API de Diego (FastAPI)
// Cada petición lleva el token de la sesión: la API lo valida y sabe quién es
// el usuario y si ya verificó el segundo factor (aal2).
import { config } from '../config'
import { supabase } from './supabase'

export interface Perfil {
  id: string
  email: string | null
  nombre_visible: string
  rol: 'estudiante' | 'docente' | 'admin'
  aviso_aceptado: boolean
  version_aviso_vigente: string
  mfa_activado: boolean
  codigos_disponibles: number
  nivel_sesion: 'aal1' | 'aal2'
}

/** Error con el mensaje en español que envía la API (formato problem+json). */
export class ErrorApi extends Error {
  readonly status: number
  constructor(status: number, mensaje: string) {
    super(mensaje)
    this.status = status
  }
}

async function pedir<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  let respuesta: Response
  try {
    respuesta = await fetch(`${config.apiUrl}${ruta}`, {
      ...opciones,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...opciones.headers,
      },
    })
  } catch {
    throw new ErrorApi(0, 'No hay conexión con la API. ¿Está corriendo Docker?')
  }
  if (!respuesta.ok) {
    const problema = await respuesta.json().catch(() => null)
    throw new ErrorApi(respuesta.status, problema?.detail ?? `Error ${respuesta.status}`)
  }
  return respuesta.json() as Promise<T>
}

export const api = {
  miPerfil: () => pedir<Perfil>('/cuentas/yo'),
  aceptarAviso: (version: string) =>
    pedir<{ aviso_aceptado: boolean }>('/cuentas/aviso', { method: 'POST', body: JSON.stringify({ version }) }),
  generarCodigos: () => pedir<{ codigos: string[] }>('/cuentas/2fa/codigos', { method: 'POST' }),
  recuperar: (codigo: string) =>
    pedir<{ recuperado: boolean; codigos_restantes: number }>('/cuentas/2fa/recuperar', {
      method: 'POST',
      body: JSON.stringify({ codigo }),
    }),
}

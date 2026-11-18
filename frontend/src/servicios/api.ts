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

// ---------- Fase 3: casos clínicos (RF-02.1, RF-04) ----------
export type Dificultad = 'basico' | 'intermedio' | 'avanzado'
export type Region = 'esofago' | 'estomago' | 'duodeno'

export interface Historia {
  edad: number
  sexo: 'femenino' | 'masculino'
  motivo: string
  antecedentes: string[]
  sintomas: string[]
  texto: string
}

/** Lo que ve el estudiante. La API nunca envía la respuesta correcta (la clase). */
export interface Caso {
  id: string
  dificultad: Dificultad
  region: Region
  historia: Historia
  imagen_url: string | null
  ubicacion: { hito: string; hito_nombre: string; x: number; y: number; z: number; radio_visibilidad: number }
  licencia_imagen: string
  creado_en: string
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
  generarCaso: (dificultad: Dificultad, region: Region | null) =>
    pedir<Caso>('/casos', { method: 'POST', body: JSON.stringify({ dificultad, region }) }),
  verCaso: (id: string) => pedir<Caso>(`/casos/${encodeURIComponent(id)}`),
}

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
  ubicacion: {
    hito: string
    hito_nombre: string
    x: number
    y: number
    z: number
    radio_visibilidad: number
    /** Fase 5 (RF-03.4): false en hallazgos normales; la escena no pinta lesión. */
    lesion_visible?: boolean
  }
  licencia_imagen: string
  creado_en: string
}

// ---------- Fase 4: resolver un caso (RF-05, RF-07, RF-09 a RF-11) ----------
export type EstadoIntento =
  | 'explorando'
  | 'hallazgo_capturado'
  | 'decision_inicial'
  | 'recomendacion'
  | 'finalizado'
  | 'abandonado'

export interface Opcion {
  clase: string
  nombre: string
}

export interface DecisionTomada extends Opcion {
  confianza: number // 1 a 5
}

/** Lo que sugiere la IA. Puede estar alterada a propósito: el estudiante no lo sabe hasta el final. */
export interface Recomendacion extends Opcion {
  confianza: number // 0 a 1
  roi: { x: number; y: number; w: number; h: number } // recuadro, en fracciones de la imagen
}

export interface MensajeTutor {
  emisor: 'estudiante' | 'tutor' | 'sistema'
  contenido: string
  es_respaldo: boolean
  creado_en: string
}

export interface Insignia {
  codigo: string
  nombre: string
  descripcion: string
}

export interface Retroalimentacion {
  referencia: Opcion
  acierto_usuario: boolean
  acierto_ia: boolean
  alterada: boolean
  tipo_alteracion: 'clase_incorrecta' | 'confianza_alterada' | 'roi_desplazada' | null
  cambio_decision: boolean
  detecto_error_ia: boolean
  puntaje: number
  desglose: { acierto: number; deteccion: number; calibracion: number; total: number }
  explicacion: string[]
  puntos_totales: number
  nivel: number
  subio_de_nivel: boolean
  insignias_nuevas: Insignia[]
}

/** Evento de la escena 3D (RF-12). Lo arma el bus de la escena (escena/bus.ts). */
export interface EventoTelemetria {
  tipo: 'hito_visitado' | 'hallazgo_capturado' | 'hallazgo_omitido' | 'captura_invalida' | 'pausa' | 'reanudacion'
  datos: Record<string, string | number | boolean>
  ocurrido_en: string
}

export interface Intento {
  id: string
  caso_id: string
  estado: EstadoIntento
  region: Region
  opciones: Opcion[]
  decision_inicial: DecisionTomada | null
  recomendacion: Recomendacion | null
  mensajes: MensajeTutor[]
  mensajes_restantes: number
  decision_final: DecisionTomada | null
  retroalimentacion: Retroalimentacion | null // solo al final: aquí llega la respuesta correcta
  /** Fase 5: códigos de los hitos ya visitados en la escena 3D (para retomar tras recargar). */
  hitos_visitados?: string[]
}

export interface RespuestaTutor {
  respuesta: string
  es_respaldo: boolean
  mensajes_restantes: number
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
  // Fase 4
  iniciarIntento: (casoId: string) =>
    pedir<Intento>('/intentos', { method: 'POST', body: JSON.stringify({ caso_id: casoId }) }),
  verIntento: (id: string) => pedir<Intento>(`/intentos/${encodeURIComponent(id)}`),
  decisionInicial: (id: string, clase: string, confianza: number) =>
    pedir<Intento>(`/intentos/${encodeURIComponent(id)}/decision-inicial`, {
      method: 'POST',
      body: JSON.stringify({ clase, confianza }),
    }),
  preguntarTutor: (id: string, mensaje: string) =>
    pedir<RespuestaTutor>(`/intentos/${encodeURIComponent(id)}/tutor`, {
      method: 'POST',
      body: JSON.stringify({ mensaje }),
    }),
  decisionFinal: (id: string, clase: string, confianza: number) =>
    pedir<Intento>(`/intentos/${encodeURIComponent(id)}/decision-final`, {
      method: 'POST',
      body: JSON.stringify({ clase, confianza }),
    }),
  // Fase 5: telemetría de la escena 3D, en lotes de hasta 200 eventos (RF-12)
  registrarEventos: (id: string, eventos: EventoTelemetria[]) =>
    pedir<{ registrados: number }>(`/intentos/${encodeURIComponent(id)}/eventos`, {
      method: 'POST',
      body: JSON.stringify({ eventos }),
    }),
}

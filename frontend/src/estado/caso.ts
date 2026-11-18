// Responsable: Cristian Cruz · Reglas de presentación de casos (RF-02.1, RF-04)
// Funciones puras, sin React ni red: se prueban en caso.test.ts.
import type { Dificultad, Historia, Region } from '../servicios/api'

export const DIFICULTADES: { valor: Dificultad; etiqueta: string; ayuda: string }[] = [
  { valor: 'basico', etiqueta: 'Básico', ayuda: 'Síntomas típicos y hallazgos evidentes' },
  { valor: 'intermedio', etiqueta: 'Intermedio', ayuda: 'Síntomas mezclados' },
  { valor: 'avanzado', etiqueta: 'Avanzado', ayuda: 'Hallazgos sutiles y síntomas poco claros' },
]

export const REGIONES: { valor: Region | ''; etiqueta: string }[] = [
  { valor: '', etiqueta: 'Cualquier región' },
  { valor: 'esofago', etiqueta: 'Esófago' },
  { valor: 'estomago', etiqueta: 'Estómago' },
  { valor: 'duodeno', etiqueta: 'Duodeno' },
]

export function etiquetaDificultad(d: Dificultad): string {
  return DIFICULTADES.find((x) => x.valor === d)?.etiqueta ?? d
}

export function etiquetaRegion(r: Region): string {
  return REGIONES.find((x) => x.valor === r)?.etiqueta ?? r
}

/** Lee la solicitud desde la URL (?dificultad=...&region=...) y descarta valores inventados. */
export function leerSolicitud(params: URLSearchParams): { dificultad: Dificultad; region: Region | null } {
  const d = params.get('dificultad')
  const r = params.get('region')
  return {
    dificultad: DIFICULTADES.some((x) => x.valor === d) ? (d as Dificultad) : 'basico',
    region: REGIONES.some((x) => x.valor && x.valor === r) ? (r as Region) : null,
  }
}

/** "Mujer de 52 años" / "Hombre de 61 años". */
export function resumenPaciente(h: Pick<Historia, 'edad' | 'sexo'>): string {
  return `${h.sexo === 'femenino' ? 'Mujer' : 'Hombre'} de ${h.edad} años`
}

/** Mensaje de la pantalla de error W08 según la respuesta de la API. */
export function mensajeErrorCaso(status: number, detalle: string): string {
  if (status === 0) return detalle
  if (status === 503) return 'Todavía no hay imágenes cargadas para generar casos. Avisa al equipo.'
  if (status === 422) return 'La IA no logró un caso válido esta vez. Intenta de nuevo.'
  if (status === 404) return 'Ese caso no existe o fue retirado por el docente.'
  return detalle || 'Ocurrió un error inesperado.'
}

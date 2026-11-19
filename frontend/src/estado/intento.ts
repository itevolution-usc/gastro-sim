// Responsable: Cristian Cruz · Reglas de presentación del intento (RF-05, RF-07, RF-09, RF-10)
// Funciones puras, sin React ni red: se prueban en intento.test.ts.
import type { EstadoIntento, Recomendacion, Retroalimentacion } from '../servicios/api'

/** Escala de confianza del estudiante (1 a 5), igual en la decisión inicial y en la final. */
export const NIVELES_CONFIANZA: { valor: number; etiqueta: string }[] = [
  { valor: 1, etiqueta: 'Muy inseguro' },
  { valor: 2, etiqueta: 'Inseguro' },
  { valor: 3, etiqueta: 'Neutral' },
  { valor: 4, etiqueta: 'Seguro' },
  { valor: 5, etiqueta: 'Muy seguro' },
]

export function etiquetaConfianza(valor: number): string {
  return NIVELES_CONFIANZA.find((n) => n.valor === valor)?.etiqueta ?? String(valor)
}

/** 0.873 → "87 %" */
export function porcentaje(fraccion: number): string {
  return `${Math.round(Math.min(1, Math.max(0, fraccion)) * 100)} %`
}

/** Qué pantalla corresponde a cada estado del intento (W10, W11 o W14). */
export function pantallaDe(estado: EstadoIntento): 'decision_inicial' | 'recomendacion' | 'retroalimentacion' | 'cerrado' {
  if (estado === 'recomendacion') return 'recomendacion'
  if (estado === 'finalizado') return 'retroalimentacion'
  if (estado === 'abandonado') return 'cerrado'
  return 'decision_inicial'
}

/** Estilo CSS del recuadro (ROI) sobre la imagen, en porcentajes. Se recorta para no salirse. */
export function estiloRoi(roi: Recomendacion['roi']): { left: string; top: string; width: string; height: string } {
  const recortar = (v: number) => Math.min(1, Math.max(0, v))
  const x = recortar(roi.x)
  const y = recortar(roi.y)
  return {
    left: `${(x * 100).toFixed(1)}%`,
    top: `${(y * 100).toFixed(1)}%`,
    width: `${(Math.min(recortar(roi.w), 1 - x) * 100).toFixed(1)}%`,
    height: `${(Math.min(recortar(roi.h), 1 - y) * 100).toFixed(1)}%`,
  }
}

const ALTERACIONES: Record<NonNullable<Retroalimentacion['tipo_alteracion']>, string> = {
  clase_incorrecta: 'Clase incorrecta',
  confianza_alterada: 'Confianza alterada',
  roi_desplazada: 'Recuadro desplazado',
}

export function etiquetaAlteracion(tipo: Retroalimentacion['tipo_alteracion']): string {
  return tipo ? ALTERACIONES[tipo] : 'Sin alteración'
}

/** Mensaje de error según la respuesta de la API al resolver un caso. */
export function mensajeErrorIntento(status: number, detalle: string): string {
  if (status === 0) return detalle
  if (status === 404) return 'Este intento no existe o no es tuyo.'
  if (status === 409) return detalle || 'Esa acción ya no está disponible en este paso.'
  return detalle || 'Ocurrió un error inesperado.'
}

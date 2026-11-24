// Responsable: Cristian Cruz · Reglas de presentación del docente (W18 y W19, RF-14.6, RF-08.1, RF-15)
// Funciones puras, sin React ni red: se prueban en docente.test.ts.
import type { CasoDocente, EstadoCaso, Perfil, TipoAlteracion } from '../servicios/api'

/** Solo docentes y administradores entran a W18 y W19 (la API también lo exige: 403). */
export function esDocente(perfil: Pick<Perfil, 'rol'> | null): boolean {
  return perfil?.rol === 'docente' || perfil?.rol === 'admin'
}

export const PESTANAS: { estado: EstadoCaso; etiqueta: string }[] = [
  { estado: 'pendiente', etiqueta: 'Pendientes' },
  { estado: 'aprobado', etiqueta: 'Aprobados' },
  { estado: 'descartado', etiqueta: 'Descartados' },
]

/** Las 4 reglas de la validación automática (RF-14.4), en el orden de la cadena. */
export const REGLAS: { codigo: string; etiqueta: string }[] = [
  { codigo: 'campos_completos', etiqueta: 'Campos completos' },
  { codigo: 'coherencia_region', etiqueta: 'Coherencia etiqueta–región' },
  { codigo: 'sin_respuesta', etiqueta: 'Sin respuesta en la historia' },
  { codigo: 'terminos_prohibidos', etiqueta: 'Sin términos prohibidos' },
]

/** Estado de cada regla para mostrar ✓ o ✗ en el W18. */
export function estadoReglas(validacion: CasoDocente['validacion']): { etiqueta: string; ok: boolean }[] {
  const aprobadas = new Set(validacion?.reglas_aprobadas ?? [])
  return REGLAS.map((r) => ({ etiqueta: r.etiqueta, ok: aprobadas.has(r.codigo) }))
}

/** 9400 → "9,4 s" (formato colombiano, con coma decimal). */
export function segundos(ms: number | null): string {
  if (ms === null || ms === undefined) return '—'
  return `${(ms / 1000).toLocaleString('es-CO', { maximumFractionDigits: 1 })} s`
}

/** "hace 5 min", "hace 2 h", "hace 3 d". */
export function haceCuanto(fechaIso: string, ahora: Date = new Date()): string {
  const minutos = Math.max(0, Math.round((ahora.getTime() - new Date(fechaIso).getTime()) / 60000))
  if (minutos < 1) return 'hace un momento'
  if (minutos < 60) return `hace ${minutos} min`
  const horas = Math.round(minutos / 60)
  if (horas < 24) return `hace ${horas} h`
  return `hace ${Math.round(horas / 24)} d`
}

/** Código corto para la lista: los primeros 6 caracteres del id. */
export function codigoCaso(id: string): string {
  return `#${id.slice(0, 6).toUpperCase()}`
}

/** Para descartar hay que escribir el motivo (la API también lo exige: 422). */
export function motivoValido(motivo: string): boolean {
  return motivo.trim().length >= 3 && motivo.length <= 500
}

// ---------- W19: alteraciones de la IA (RF-08.1, RF-08.2) ----------
export const PORCENTAJE_MAXIMO = 50 // igual que la API y el check de la base de datos

export const TIPOS_ALTERACION: { tipo: TipoAlteracion; etiqueta: string; ayuda: string }[] = [
  { tipo: 'clase_incorrecta', etiqueta: 'Clase incorrecta', ayuda: 'La IA sugiere otro hallazgo de la misma región' },
  { tipo: 'confianza_alterada', etiqueta: 'Confianza alterada', ayuda: 'Muestra mucha seguridad cuando no la tiene, o al revés' },
  { tipo: 'roi_desplazada', etiqueta: 'Región de interés desplazada', ayuda: 'El recuadro señala otra zona de la imagen' },
]

/** Lleva el porcentaje al rango permitido, en pasos de 5. */
export function ajustarPorcentaje(valor: number): number {
  if (!Number.isFinite(valor)) return 0
  return Math.min(PORCENTAJE_MAXIMO, Math.max(0, Math.round(valor / 5) * 5))
}

/** Aviso cuando la configuración no tendrá efecto (la API guarda 0 % si no hay tipos). */
export function avisoConfiguracion(porcentaje: number, tipos: TipoAlteracion[]): string | null {
  if (porcentaje > 0 && tipos.length === 0) return 'Elige al menos un tipo de alteración o la IA no se alterará.'
  if (porcentaje === 0) return 'Con 0 % la IA nunca se altera.'
  return null
}

/** Nombre del archivo que se descarga (igual al que propone la API). */
export function nombreCsv(hoy: Date = new Date()): string {
  const dos = (n: number) => String(n).padStart(2, '0')
  return `gastro-sim-intentos-${hoy.getFullYear()}-${dos(hoy.getMonth() + 1)}-${dos(hoy.getDate())}.csv`
}

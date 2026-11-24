// Responsable: Cristian Cruz · Progreso e historial del estudiante en el W06 (RF-02.3, RF-11)
// Funciones puras, sin React ni red: se prueban en docente.test.ts.
import type { Progreso, ResumenIntento } from '../servicios/api'

/** Cuánto le falta al estudiante para el siguiente nivel y el % de la barra. */
export function avanceNivel(p: Pick<Progreso, 'puntos' | 'nivel' | 'puntos_por_nivel' | 'puntos_siguiente_nivel'>): {
  faltan: number
  porcentaje: number
} {
  if (p.puntos_siguiente_nivel === null) return { faltan: 0, porcentaje: 100 }
  const inicio = (p.nivel - 1) * p.puntos_por_nivel
  const ganados = Math.max(0, p.puntos - inicio)
  return {
    faltan: Math.max(0, p.puntos_siguiente_nivel - p.puntos),
    porcentaje: Math.min(100, Math.round((ganados / p.puntos_por_nivel) * 100)),
  }
}

/** Texto de la columna "Resultado" del historial. */
export function resultado(f: Pick<ResumenIntento, 'estado' | 'acierto'>): string {
  if (f.estado === 'finalizado') return f.acierto ? '✓ Acierto' : '✗ Error'
  if (f.estado === 'abandonado') return 'Abandonado'
  return 'En curso'
}

/** Qué ofrece el botón de cada fila: seguir el intento abierto, repetir el caso o nada. */
export function accionHistorial(f: Pick<ResumenIntento, 'estado' | 'puede_repetir'>): 'continuar' | 'repetir' | null {
  if (f.estado !== 'finalizado' && f.estado !== 'abandonado') return 'continuar'
  return f.puede_repetir ? 'repetir' : null
}

/** "24/11/2026" (formato colombiano). */
export function fechaCorta(iso: string): string {
  return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

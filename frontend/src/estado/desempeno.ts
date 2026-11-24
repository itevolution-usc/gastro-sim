// Responsable: Cristian Cruz · Reglas del tablero de desempeño (W16, RF-13) y de usuarios (W20, W21)
// Funciones puras, sin React ni red: se prueban en desempeno.test.ts.
import type { CambioAuditoria, Perfil, SemanaDesempeno, UsuarioAdmin } from '../servicios/api'

/** 0.78 → "78 %"; null → "—" (todavía no hay casos para calcularlo). */
export function porcentaje(valor: number | null): string {
  return valor === null ? '—' : `${Math.round(valor * 100)} %`
}

/** 0.71 → "0,71". */
export function decimal(valor: number | null): string {
  return valor === null ? '—' : valor.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export interface Punto {
  x: number
  y: number
}

/**
 * Coordenadas de una línea de la gráfica "por semana": x reparte las semanas en el ancho,
 * y va de 0 % (abajo) a 100 % (arriba). Las semanas sin dato (null) cortan la línea.
 */
export function lineaSemanal(
  serie: SemanaDesempeno[],
  campo: 'precision' | 'deteccion',
  ancho: number,
  alto: number,
  margen = 24,
): Punto[][] {
  const paso = serie.length > 1 ? (ancho - 2 * margen) / (serie.length - 1) : 0
  const tramos: Punto[][] = [[]]
  serie.forEach((s, i) => {
    const v = s[campo]
    if (v === null) {
      if (tramos[tramos.length - 1].length) tramos.push([])
      return
    }
    const x = serie.length > 1 ? margen + i * paso : ancho / 2
    tramos[tramos.length - 1].push({ x: Math.round(x), y: Math.round(alto - margen - v * (alto - 2 * margen)) })
  })
  return tramos.filter((t) => t.length)
}

/** "2026-11-23" → "23/11". */
export function etiquetaSemana(lunes: string): string {
  const [, mes, dia] = lunes.split('-')
  return `${dia}/${mes}`
}

// ---------- W20 y W21 ----------

/** RF-01.3: docentes y administradores cambian el rol de otras cuentas, nunca el propio ni el de un admin. */
export function puedeCambiarRol(yo: Pick<Perfil, 'id' | 'rol'>, cuenta: Pick<UsuarioAdmin, 'id' | 'rol'>): boolean {
  return (yo.rol === 'docente' || yo.rol === 'admin') && cuenta.id !== yo.id && cuenta.rol !== 'admin'
}

/** RF-01.7: solo un administrador restablece el 2FA de otra cuenta. */
export function puedeRestablecer(yo: Pick<Perfil, 'id' | 'rol'>, cuenta: Pick<UsuarioAdmin, 'id' | 'rol'>): boolean {
  return yo.rol === 'admin' && cuenta.id !== yo.id && cuenta.rol !== 'admin'
}

/** Texto de una fila del registro de cambios. */
export function describirCambio(c: Pick<CambioAuditoria, 'accion' | 'actor' | 'afectado'>): string {
  if (c.accion === 'asignar_rol') return `${c.actor} dio el rol docente a ${c.afectado}`
  if (c.accion === 'retirar_rol') return `${c.actor} dejó como estudiante a ${c.afectado}`
  return `${c.actor} restableció el 2FA de ${c.afectado}`
}

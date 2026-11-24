// Responsable: Nestor Velasco (calidad) · Pruebas de la fase 6 sin navegador (npm test)
// Código bajo prueba: Cristian Cruz (estado/docente.ts y estado/progreso.ts).
// Requisitos: RF-02.3 (historial), RF-11 (progreso), RF-14.6 (W18), RF-08.1 y RF-15 (W19).
import { describe, expect, it } from 'vitest'

import {
  ajustarPorcentaje,
  avisoConfiguracion,
  codigoCaso,
  esDocente,
  estadoReglas,
  haceCuanto,
  motivoValido,
  nombreCsv,
  segundos,
} from './docente'
import { accionHistorial, avanceNivel, resultado } from './progreso'

describe('acceso del docente', () => {
  it('solo docentes y administradores entran a W18 y W19', () => {
    expect(esDocente({ rol: 'docente' })).toBe(true)
    expect(esDocente({ rol: 'admin' })).toBe(true)
    expect(esDocente({ rol: 'estudiante' })).toBe(false)
    expect(esDocente(null)).toBe(false)
  })
})

describe('revisión de casos (W18, RF-14.6)', () => {
  it('muestra las 4 reglas de la validación en orden, con ✓ o ✗', () => {
    const reglas = estadoReglas({ ok: false, reglas_aprobadas: ['campos_completos', 'coherencia_region'], fallo: null })
    expect(reglas.map((r) => r.ok)).toEqual([true, true, false, false])
    expect(reglas[2].etiqueta).toBe('Sin respuesta en la historia')
    expect(estadoReglas(null).every((r) => !r.ok)).toBe(true)
  })

  it('pide un motivo para descartar', () => {
    expect(motivoValido('')).toBe(false)
    expect(motivoValido('   ')).toBe(false)
    expect(motivoValido('Historia poco clara')).toBe(true)
    expect(motivoValido('x'.repeat(501))).toBe(false)
  })

  it('formatea tiempos y códigos', () => {
    expect(segundos(9400)).toBe('9,4 s')
    expect(segundos(null)).toBe('—')
    expect(codigoCaso('a1b2c3d4-0000')).toBe('#A1B2C3')
    const ahora = new Date('2026-11-24T12:00:00Z')
    expect(haceCuanto('2026-11-24T11:59:50Z', ahora)).toBe('hace un momento')
    expect(haceCuanto('2026-11-24T11:15:00Z', ahora)).toBe('hace 45 min')
    expect(haceCuanto('2026-11-24T09:00:00Z', ahora)).toBe('hace 3 h')
    expect(haceCuanto('2026-11-21T12:00:00Z', ahora)).toBe('hace 3 d')
  })
})

describe('configuración y exportación (W19, RF-08.1 y RF-15)', () => {
  it('mantiene el porcentaje entre 0 y 50, en pasos de 5', () => {
    expect(ajustarPorcentaje(22)).toBe(20)
    expect(ajustarPorcentaje(23)).toBe(25)
    expect(ajustarPorcentaje(80)).toBe(50)
    expect(ajustarPorcentaje(-5)).toBe(0)
    expect(ajustarPorcentaje(Number.NaN)).toBe(0)
  })

  it('avisa cuando la configuración no tendrá efecto', () => {
    expect(avisoConfiguracion(20, [])).toMatch(/al menos un tipo/)
    expect(avisoConfiguracion(0, ['clase_incorrecta'])).toMatch(/nunca se altera/)
    expect(avisoConfiguracion(20, ['clase_incorrecta'])).toBeNull()
  })

  it('nombra el archivo con la fecha', () => {
    expect(nombreCsv(new Date(2026, 10, 4))).toBe('gastro-sim-intentos-2026-11-04.csv')
  })
})

describe('progreso e historial del estudiante (W06, RF-11 y RF-02.3)', () => {
  const base = { puntos_por_nivel: 500 }

  it('calcula cuánto falta para el siguiente nivel', () => {
    expect(avanceNivel({ ...base, puntos: 0, nivel: 1, puntos_siguiente_nivel: 500 })).toEqual({ faltan: 500, porcentaje: 0 })
    expect(avanceNivel({ ...base, puntos: 1240, nivel: 3, puntos_siguiente_nivel: 1500 })).toEqual({ faltan: 260, porcentaje: 48 })
    expect(avanceNivel({ ...base, puntos: 5200, nivel: 10, puntos_siguiente_nivel: null })).toEqual({ faltan: 0, porcentaje: 100 })
  })

  it('muestra el resultado de cada intento', () => {
    expect(resultado({ estado: 'finalizado', acierto: true })).toBe('✓ Acierto')
    expect(resultado({ estado: 'finalizado', acierto: false })).toBe('✗ Error')
    expect(resultado({ estado: 'explorando', acierto: null })).toBe('En curso')
  })

  it('ofrece continuar, repetir o nada', () => {
    expect(accionHistorial({ estado: 'recomendacion', puede_repetir: true })).toBe('continuar')
    expect(accionHistorial({ estado: 'finalizado', puede_repetir: true })).toBe('repetir')
    expect(accionHistorial({ estado: 'finalizado', puede_repetir: false })).toBeNull() // caso descartado
  })
})

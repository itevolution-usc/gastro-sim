// Responsable: Nestor Velasco (calidad) · Pruebas de la fase 7 sin navegador (npm test)
// Código bajo prueba: Cristian Cruz (estado/desempeno.ts).
// Requisitos: RF-13 (tablero W16), RF-01.3 (roles, W20) y RF-01.7 (restablecer 2FA, W21).
import { describe, expect, it } from 'vitest'

import {
  decimal,
  describirCambio,
  etiquetaSemana,
  lineaSemanal,
  porcentaje,
  puedeCambiarRol,
  puedeRestablecer,
} from './desempeno'

describe('tablero de desempeño (W16, RF-13)', () => {
  it('muestra porcentajes y decimales, y una raya si no hay datos', () => {
    expect(porcentaje(0.78)).toBe('78 %')
    expect(porcentaje(0)).toBe('0 %')
    expect(porcentaje(null)).toBe('—')
    expect(decimal(0.71)).toBe('0,71')
    expect(decimal(null)).toBe('—')
  })

  it('dibuja la línea por semana entre 0 % (abajo) y 100 % (arriba)', () => {
    const serie = [
      { semana: '2026-11-09', intentos: 2, precision: 0, deteccion: null },
      { semana: '2026-11-16', intentos: 3, precision: 1, deteccion: 0.5 },
    ]
    expect(lineaSemanal(serie, 'precision', 640, 220)).toEqual([[{ x: 24, y: 196 }, { x: 616, y: 24 }]])
    // Una semana sin dato no inventa un punto: la línea empieza en la siguiente.
    expect(lineaSemanal(serie, 'deteccion', 640, 220)).toEqual([[{ x: 616, y: 110 }]])
    expect(lineaSemanal([], 'precision', 640, 220)).toEqual([])
  })

  it('una sola semana queda centrada', () => {
    expect(lineaSemanal([{ semana: '2026-11-23', intentos: 1, precision: 0.5, deteccion: null }], 'precision', 640, 220)).toEqual([
      [{ x: 320, y: 110 }],
    ])
    expect(etiquetaSemana('2026-11-23')).toBe('23/11')
  })
})

describe('usuarios y roles (W20 y W21, RF-01.3 y RF-01.7)', () => {
  const estudiante = { id: 'e', rol: 'estudiante' as const }
  const docente = { id: 'd', rol: 'docente' as const }
  const admin = { id: 'a', rol: 'admin' as const }

  it('docentes y administradores cambian el rol de otras cuentas, nunca el propio ni el de un admin', () => {
    expect(puedeCambiarRol(docente, estudiante)).toBe(true)
    expect(puedeCambiarRol(admin, docente)).toBe(true)
    expect(puedeCambiarRol(docente, docente)).toBe(false) // su propia cuenta
    expect(puedeCambiarRol(docente, admin)).toBe(false)
    expect(puedeCambiarRol(estudiante, { id: 'x', rol: 'estudiante' })).toBe(false)
  })

  it('solo el administrador restablece el 2FA de otra cuenta', () => {
    expect(puedeRestablecer(admin, estudiante)).toBe(true)
    expect(puedeRestablecer(docente, estudiante)).toBe(false)
    expect(puedeRestablecer(admin, admin)).toBe(false)
  })

  it('describe cada cambio del registro', () => {
    const base = { actor: 'Laura', afectado: 'ana@usc.edu.co' }
    expect(describirCambio({ ...base, accion: 'asignar_rol' })).toBe('Laura dio el rol docente a ana@usc.edu.co')
    expect(describirCambio({ ...base, accion: 'retirar_rol' })).toBe('Laura dejó como estudiante a ana@usc.edu.co')
    expect(describirCambio({ ...base, accion: 'restablecer_2fa' })).toBe('Laura restableció el 2FA de ana@usc.edu.co')
  })
})

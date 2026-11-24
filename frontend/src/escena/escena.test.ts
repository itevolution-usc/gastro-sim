// Responsable: Nestor Velasco (calidad) · Pruebas de la escena 3D sin navegador (npm test)
// Código bajo prueba: Cristian Cruz (escena/ruta.ts, escena/bus.ts, escena/telemetria.ts).
// Requisitos: RF-03.2 a RF-03.6 y RF-12. No necesitan WebGL: prueban las reglas, no el dibujo.
import { describe, expect, it, vi } from 'vitest'

import { BusEscena, type EventoEscena } from './bus'
import {
  anguloHacia,
  cronometro,
  datosCaptura,
  evaluarVisibilidad,
  HITOS,
  hitosNuevos,
  moverAvance,
  proyectarMinimapa,
  RUTA,
} from './ruta'
import { MAX_LOTE, TelemetriaBuffer } from './telemetria'

// Posiciones de los hitos en el modelo de Cristian (v3, 23/11/2026).
const POS = {
  linea_z: { x: 0, y: -20, z: 0 },
  cardias: { x: 0, y: -22.5, z: 0 },
  fondo: { x: -3, y: -24.5, z: 0 },
  cuerpo: { x: -4, y: -29, z: 0 },
  antro: { x: 0, y: -32, z: 0 },
  piloro: { x: 5, y: -28, z: 0 },
  bulbo: { x: 7, y: -26, z: 0 },
}
const ABAJO = { x: 0, y: -1, z: 0 } // mirar hacia el estómago

describe('ruta del endoscopio', () => {
  it('tiene el inicio y los 7 hitos en el orden del recorrido', () => {
    expect(RUTA[0]).toBe('camara_inicio')
    expect(HITOS).toEqual(['linea_z', 'cardias', 'fondo', 'cuerpo', 'antro', 'piloro', 'bulbo'])
  })

  it('marca un hito al pasar cerca y una sola vez (RF-03.3)', () => {
    expect(hitosNuevos({ x: 0, y: -10, z: 0 }, POS, new Set())).toEqual([])
    expect(hitosNuevos({ x: 0, y: -19, z: 0 }, POS, new Set())).toEqual(['linea_z'])
    expect(hitosNuevos({ x: 0, y: -19, z: 0 }, POS, new Set(['linea_z']))).toEqual([])
    // Entre la línea Z y el cardias (2,5 cm) se alcanzan los dos.
    expect(hitosNuevos({ x: 0, y: -21.25, z: 0 }, POS, new Set())).toEqual(['linea_z', 'cardias'])
  })

  it('no se sale del recorrido al avanzar o retroceder (RF-03.2)', () => {
    expect(moverAvance(0.5, 0.1)).toBeCloseTo(0.6)
    expect(moverAvance(0.95, 0.2)).toBe(1)
    expect(moverAvance(0.05, -0.2)).toBe(0)
  })
})

describe('captura del hallazgo (RF-03.5)', () => {
  const hallazgo = { x: 0, y: -20, z: 0.9 } // en la pared, a la altura de la línea Z

  it('mide el ángulo entre la mirada y el hallazgo', () => {
    expect(anguloHacia({ x: 0, y: 0, z: 0 }, ABAJO, { x: 0, y: -5, z: 0 })).toBeCloseTo(0)
    expect(anguloHacia({ x: 0, y: 0, z: 0 }, ABAJO, { x: 5, y: 0, z: 0 })).toBeCloseTo(90)
    expect(anguloHacia({ x: 0, y: 0, z: 0 }, ABAJO, { x: 0, y: 5, z: 0 })).toBeCloseTo(180)
  })

  it('se puede capturar si está cerca y en el centro de la vista', () => {
    const v = evaluarVisibilidad({ x: 0, y: -17.5, z: 0 }, ABAJO, hallazgo, 1.5)
    expect(v.enVista).toBe(true)
    expect(v.distancia).toBeLessThan(3.5)
  })

  it('no se puede capturar de lejos, aunque esté centrado', () => {
    expect(evaluarVisibilidad({ x: 0, y: -10, z: 0 }, ABAJO, hallazgo, 1.5).enVista).toBe(false)
  })

  it('no se puede capturar si no se está mirando hacia él', () => {
    const arriba = { x: 0, y: 1, z: 0 }
    expect(evaluarVisibilidad({ x: 0, y: -18.5, z: 0 }, arriba, hallazgo, 1.5).enVista).toBe(false)
  })

  it('los datos de la captura no llevan la clase del hallazgo', () => {
    const v = evaluarVisibilidad({ x: 0, y: -17.5, z: 0 }, ABAJO, hallazgo, 1.5)
    const datos = datosCaptura(v, 'linea_z', 42.6)
    expect(Object.keys(datos).sort()).toEqual(['angulo', 'distancia', 'hito', 'segundos'])
    expect(datos.segundos).toBe(43)
  })
})

describe('minimapa y cronómetro (RF-03.6)', () => {
  it('ajusta la ruta al cuadro, con la boca arriba', () => {
    const p = proyectarMinimapa([{ x: 0, y: 0, z: 0 }, { x: 0, y: -30, z: 0 }, { x: 8, y: -26, z: 0 }], 180, 200)
    for (const q of p) {
      expect(q.x).toBeGreaterThanOrEqual(0)
      expect(q.x).toBeLessThanOrEqual(180)
      expect(q.y).toBeGreaterThanOrEqual(0)
      expect(q.y).toBeLessThanOrEqual(200)
    }
    expect(p[0].y).toBeLessThan(p[1].y) // la boca queda arriba del estómago
    expect(proyectarMinimapa([], 180, 200)).toEqual([])
  })

  it('muestra el tiempo como mm:ss', () => {
    expect(cronometro(0)).toBe('00:00')
    expect(cronometro(125.9)).toBe('02:05')
  })
})

describe('bus de la escena (patrón Observer)', () => {
  it('avisa a los suscriptores del tipo y a los de todos los eventos', () => {
    const bus = new BusEscena()
    const hitos: EventoEscena[] = []
    const todos: EventoEscena[] = []
    bus.suscribir('hito_visitado', (e) => hitos.push(e))
    const cancelar = bus.suscribir('*', (e) => todos.push(e))
    bus.emitir('hito_visitado', { hito: 'linea_z' }, new Date('2026-11-23T10:00:00Z'))
    bus.emitir('pausa')
    expect(hitos).toHaveLength(1)
    expect(hitos[0]).toEqual({ tipo: 'hito_visitado', datos: { hito: 'linea_z' }, ocurrido_en: '2026-11-23T10:00:00.000Z' })
    expect(todos.map((e) => e.tipo)).toEqual(['hito_visitado', 'pausa'])
    cancelar()
    bus.emitir('reanudacion')
    expect(todos).toHaveLength(2)
  })
})

describe('telemetría en lotes (RF-12)', () => {
  const evento = (i: number): EventoEscena => ({ tipo: 'pausa', datos: { i }, ocurrido_en: '2026-11-23T10:00:00Z' })

  it('envía en lotes de máximo 200 y en orden', async () => {
    const enviar = vi.fn().mockResolvedValue(undefined)
    const buffer = new TelemetriaBuffer(enviar)
    for (let i = 0; i < 450; i++) buffer.agregar(evento(i))
    await buffer.enviarLote()
    expect(enviar.mock.calls.map((c) => c[0].length)).toEqual([MAX_LOTE, MAX_LOTE, 50])
    expect(enviar.mock.calls[0][0][0].datos.i).toBe(0)
    expect(buffer.cantidad).toBe(0)
  })

  it('si la red falla, no pierde eventos y los reenvía después', async () => {
    const enviar = vi.fn().mockRejectedValueOnce(new Error('sin red')).mockResolvedValue(undefined)
    const buffer = new TelemetriaBuffer(enviar)
    buffer.agregar(evento(1))
    await expect(buffer.enviarLote()).rejects.toThrow('sin red')
    expect(buffer.cantidad).toBe(1)
    buffer.agregar(evento(2))
    await buffer.enviarLote()
    expect(enviar.mock.calls[1][0].map((e: EventoEscena) => e.datos.i)).toEqual([1, 2])
  })

  it('no llama a la API si no hay nada pendiente', async () => {
    const enviar = vi.fn()
    await new TelemetriaBuffer(enviar).enviarLote()
    expect(enviar).not.toHaveBeenCalled()
  })
})

describe('porcentaje de hitos (RF-03.3)', () => {
  it('se muestra redondeado y nunca pasa de 100', async () => {
    const { porcentajeHitos } = await import('./ruta')
    expect(porcentajeHitos(0)).toBe(0)
    expect(porcentajeHitos(2)).toBe(29)
    expect(porcentajeHitos(7)).toBe(100)
    expect(porcentajeHitos(9)).toBe(100)
  })
})

// Responsable: Cristian Cruz · Pruebas de presentación del intento (npm test)
import { describe, expect, it } from 'vitest'

import { estiloRoi, etiquetaAlteracion, etiquetaConfianza, mensajeErrorIntento, pantallaDe, porcentaje } from './intento'

describe('intento', () => {
  it('elige la pantalla según el estado', () => {
    expect(pantallaDe('explorando')).toBe('decision_inicial')
    expect(pantallaDe('hallazgo_capturado')).toBe('decision_inicial')
    expect(pantallaDe('recomendacion')).toBe('recomendacion')
    expect(pantallaDe('finalizado')).toBe('retroalimentacion')
    expect(pantallaDe('abandonado')).toBe('cerrado')
  })

  it('muestra la confianza en palabras y en porcentaje', () => {
    expect(etiquetaConfianza(1)).toBe('Muy inseguro')
    expect(etiquetaConfianza(5)).toBe('Muy seguro')
    expect(porcentaje(0.873)).toBe('87 %')
    expect(porcentaje(1.4)).toBe('100 %')
  })

  it('ubica el recuadro sin salirse de la imagen', () => {
    expect(estiloRoi({ x: 0.1, y: 0.2, w: 0.3, h: 0.4 })).toEqual({ left: '10.0%', top: '20.0%', width: '30.0%', height: '40.0%' })
    expect(estiloRoi({ x: 0.9, y: 0.9, w: 0.5, h: 0.5 })).toEqual({ left: '90.0%', top: '90.0%', width: '10.0%', height: '10.0%' })
  })

  it('traduce alteraciones y errores', () => {
    expect(etiquetaAlteracion('clase_incorrecta')).toBe('Clase incorrecta')
    expect(etiquetaAlteracion(null)).toBe('Sin alteración')
    expect(mensajeErrorIntento(404, '')).toMatch(/no existe/)
    expect(mensajeErrorIntento(409, 'Ya usaste los 8 mensajes del tutor en este caso')).toMatch(/8 mensajes/)
  })
})

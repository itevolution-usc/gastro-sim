// Responsable: Cristian Cruz · Pruebas de presentación de casos (npm test)
import { describe, expect, it } from 'vitest'

import { etiquetaDificultad, etiquetaRegion, leerSolicitud, mensajeErrorCaso, resumenPaciente } from './caso'

describe('leerSolicitud', () => {
  it('lee dificultad y región válidas', () => {
    expect(leerSolicitud(new URLSearchParams('dificultad=avanzado&region=estomago'))).toEqual({
      dificultad: 'avanzado',
      region: 'estomago',
    })
  })

  it('sin parámetros pide un caso básico de cualquier región', () => {
    expect(leerSolicitud(new URLSearchParams(''))).toEqual({ dificultad: 'basico', region: null })
  })

  it('ignora valores inventados en la URL', () => {
    expect(leerSolicitud(new URLSearchParams('dificultad=experto&region=colon'))).toEqual({
      dificultad: 'basico',
      region: null,
    })
  })
})

describe('textos', () => {
  it('resume al paciente', () => {
    expect(resumenPaciente({ edad: 52, sexo: 'femenino' })).toBe('Mujer de 52 años')
    expect(resumenPaciente({ edad: 61, sexo: 'masculino' })).toBe('Hombre de 61 años')
  })

  it('traduce dificultad y región', () => {
    expect(etiquetaDificultad('intermedio')).toBe('Intermedio')
    expect(etiquetaRegion('esofago')).toBe('Esófago')
  })

  it('explica cada error de la API', () => {
    expect(mensajeErrorCaso(503, '')).toMatch(/imágenes/)
    expect(mensajeErrorCaso(422, '')).toMatch(/Intenta de nuevo/)
    expect(mensajeErrorCaso(0, 'No hay conexión con la API.')).toBe('No hay conexión con la API.')
  })
})

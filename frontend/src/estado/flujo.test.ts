// Responsable: Cristian Cruz · Pruebas de las reglas de navegación (se ejecutan con: npm test)
import { describe, expect, it } from 'vitest'

import { siguientePantalla } from './flujo'

const completo = { aviso_aceptado: true, mfa_activado: true }

describe('siguientePantalla', () => {
  it('sin sesión va a iniciar sesión', () => {
    expect(siguientePantalla({ haySesion: false, nivelActual: null, nivelSiguiente: null, perfil: null })).toBe('/ingresar')
  })

  it('cuenta nueva sin aviso va a activar', () => {
    const perfil = { aviso_aceptado: false, mfa_activado: false }
    expect(siguientePantalla({ haySesion: true, nivelActual: 'aal1', nivelSiguiente: 'aal1', perfil })).toBe('/activar')
  })

  it('aviso aceptado pero sin 2FA va a activar', () => {
    const perfil = { aviso_aceptado: true, mfa_activado: false }
    expect(siguientePantalla({ haySesion: true, nivelActual: 'aal1', nivelSiguiente: 'aal1', perfil })).toBe('/activar')
  })

  it('con 2FA activo e inicio solo con contraseña pide el código', () => {
    expect(siguientePantalla({ haySesion: true, nivelActual: 'aal1', nivelSiguiente: 'aal2', perfil: completo })).toBe('/verificar')
  })

  it('verificó el código pero no recibió los códigos de recuperación: vuelve a activar', () => {
    const perfil = { aviso_aceptado: true, mfa_activado: false }
    expect(siguientePantalla({ haySesion: true, nivelActual: 'aal2', nivelSiguiente: 'aal2', perfil })).toBe('/activar')
  })

  it('todo completo va al inicio', () => {
    expect(siguientePantalla({ haySesion: true, nivelActual: 'aal2', nivelSiguiente: 'aal2', perfil: completo })).toBe('/inicio')
  })

  it('nunca entra al inicio con sesión aal1 aunque el perfil diga 2FA activo', () => {
    expect(siguientePantalla({ haySesion: true, nivelActual: 'aal1', nivelSiguiente: 'aal1', perfil: completo })).not.toBe('/inicio')
  })
})

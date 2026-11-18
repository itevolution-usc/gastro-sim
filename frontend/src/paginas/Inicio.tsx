// Responsable: Cristian Cruz · W06 Inicio del estudiante (versión de la fase 2) y W17 cerrar sesión
// En la fase 3 aquí aparecerá el botón "Nuevo caso" del generador de casos (Emmanuel).
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { DIFICULTADES, REGIONES } from '../estado/caso'
import { useSesion } from '../estado/sesion'
import type { Dificultad } from '../servicios/api'
import { cerrarSesion } from '../servicios/auth'

export function Inicio() {
  const navegar = useNavigate()
  const perfil = useSesion((s) => s.perfil)
  // Fase 3 (RF-02.1, RF-02.2): el estudiante elige dificultad y, si quiere, región.
  const [dificultad, setDificultad] = useState<Dificultad>('basico')
  const [region, setRegion] = useState('')
  if (!perfil) return null

  function nuevoCaso(e: FormEvent) {
    e.preventDefault()
    const params = new URLSearchParams({ dificultad, ...(region ? { region } : {}) })
    navegar(`/caso/nuevo?${params}`)
  }

  async function salir() {
    await cerrarSesion()
    navegar('/ingresar', { replace: true })
  }

  return (
    <Marco codigo="W06" titulo={`Hola, ${perfil.nombre_visible}`} subtitulo="Tu cuenta está lista.">
      <dl className="datos">
        <dt>Rol</dt>
        <dd>{perfil.rol}</dd>
        <dt>Seguridad</dt>
        <dd>Sesión verificada con doble factor ✔</dd>
        <dt>Códigos de recuperación</dt>
        <dd>{perfil.codigos_disponibles} disponibles</dd>
      </dl>
      {perfil.codigos_disponibles < 3 && (
        <Mensaje tipo="info">Te quedan pocos códigos de recuperación. Pronto podrás generar nuevos.</Mensaje>
      )}
      <form className="formulario nuevo-caso" onSubmit={nuevoCaso}>
        <h2>Nuevo caso clínico</h2>
        <label>
          Dificultad
          <select value={dificultad} onChange={(e) => setDificultad(e.target.value as Dificultad)}>
            {DIFICULTADES.map((d) => (
              <option key={d.valor} value={d.valor}>
                {d.etiqueta} · {d.ayuda}
              </option>
            ))}
          </select>
        </label>
        <label>
          Región
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            {REGIONES.map((r) => (
              <option key={r.valor} value={r.valor}>
                {r.etiqueta}
              </option>
            ))}
          </select>
        </label>
        <button className="primario" type="submit">
          Generar caso
        </button>
      </form>
      <button className="secundario" onClick={salir}>
        Cerrar sesión
      </button>
    </Marco>
  )
}

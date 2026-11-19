// Responsable: Cristian Cruz · Formulario de decisión + confianza (RF-05 inicial y RF-09 final)
import { useState, type FormEvent } from 'react'

import { NIVELES_CONFIANZA } from '../estado/intento'
import type { Opcion } from '../servicios/api'

interface Props {
  titulo: string
  opciones: Opcion[]
  inicial?: { clase: string; confianza: number }
  textoBoton: string
  ocupado: boolean
  onEnviar: (clase: string, confianza: number) => void
}

export function FormDecision({ titulo, opciones, inicial, textoBoton, ocupado, onEnviar }: Props) {
  const [clase, setClase] = useState(inicial?.clase ?? '')
  const [confianza, setConfianza] = useState(inicial?.confianza ?? 0)

  function enviar(e: FormEvent) {
    e.preventDefault()
    if (clase && confianza) onEnviar(clase, confianza)
  }

  return (
    <form className="formulario decision" onSubmit={enviar}>
      <fieldset>
        <legend>{titulo}</legend>
        {opciones.map((o) => (
          <label key={o.clase} className="opcion">
            <input type="radio" name="clase" value={o.clase} checked={clase === o.clase} onChange={() => setClase(o.clase)} />
            {o.nombre}
          </label>
        ))}
      </fieldset>
      <fieldset>
        <legend>¿Qué tan seguro estás?</legend>
        <div className="escala">
          {NIVELES_CONFIANZA.map((n) => (
            <label key={n.valor} className={confianza === n.valor ? 'nivel elegido' : 'nivel'}>
              <input type="radio" name="confianza" value={n.valor} checked={confianza === n.valor} onChange={() => setConfianza(n.valor)} />
              <strong>{n.valor}</strong>
              <small>{n.etiqueta}</small>
            </label>
          ))}
        </div>
      </fieldset>
      <button className="primario" type="submit" disabled={!clase || !confianza || ocupado}>
        {ocupado ? 'Guardando…' : textoBoton}
      </button>
    </form>
  )
}

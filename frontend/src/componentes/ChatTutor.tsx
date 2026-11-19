// Responsable: Cristian Cruz · Chat con el tutor socrático (W11 y W13, RF-07)
import { useState, type FormEvent } from 'react'

import type { MensajeTutor } from '../servicios/api'

interface Props {
  mensajes: MensajeTutor[]
  restantes: number
  ocupado: boolean
  onPreguntar: (texto: string) => void
}

export function ChatTutor({ mensajes, restantes, ocupado, onPreguntar }: Props) {
  const [texto, setTexto] = useState('')
  const usoRespaldo = mensajes.some((m) => m.es_respaldo)

  function enviar(e: FormEvent) {
    e.preventDefault()
    const limpio = texto.trim()
    if (!limpio) return
    onPreguntar(limpio)
    setTexto('')
  }

  return (
    <section className="tutor" aria-label="Tutor">
      <h2>Tutor</h2>
      <p className="ayuda">Te guía con preguntas. No te dirá la respuesta.</p>
      <ol className="mensajes" aria-live="polite">
        {mensajes.map((m, i) => (
          <li key={i} className={m.emisor === 'estudiante' ? 'yo' : 'tutor-msg'}>
            {m.contenido}
          </li>
        ))}
        {ocupado && <li className="tutor-msg pensando">El tutor está pensando…</li>}
      </ol>
      {usoRespaldo && (
        <p className="mensaje info">El tutor con IA no estuvo disponible: algunas respuestas son la guía básica.</p>
      )}
      {restantes > 0 ? (
        <form className="preguntar" onSubmit={enviar}>
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            maxLength={500}
            placeholder="Escribe tu pregunta…"
            aria-label="Pregunta para el tutor"
            disabled={ocupado}
          />
          <button className="primario" type="submit" disabled={ocupado || !texto.trim()}>
            Preguntar
          </button>
        </form>
      ) : (
        <p className="ayuda">Ya usaste todas las preguntas de este caso.</p>
      )}
      <p className="ayuda">Te quedan {restantes} preguntas.</p>
    </section>
  )
}

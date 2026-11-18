// Responsable: Cristian Cruz · W10 Presentación del caso clínico (RF-04)
// Muestra la historia sintética y la imagen. Nunca muestra la respuesta: la API no la envía.
// La exploración 3D (RF-03) y las decisiones (RF-05, RF-09) se agregan en las fases 4 y 5.
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { etiquetaDificultad, etiquetaRegion, mensajeErrorCaso, resumenPaciente } from '../estado/caso'
import { api, ErrorApi, type Caso as TipoCaso } from '../servicios/api'

export function Caso() {
  const { id = '' } = useParams()
  const navegar = useNavigate()
  const [caso, setCaso] = useState<TipoCaso | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let vigente = true
    api
      .verCaso(id)
      .then((c) => vigente && setCaso(c))
      .catch((e) => vigente && setError(e instanceof ErrorApi ? mensajeErrorCaso(e.status, e.message) : 'Error inesperado'))
    return () => {
      vigente = false
    }
  }, [id])

  if (error) {
    return (
      <Marco codigo="W10" titulo="Caso no disponible">
        <Mensaje tipo="error">{error}</Mensaje>
        <button className="secundario" onClick={() => navegar('/inicio')}>
          Volver al inicio
        </button>
      </Marco>
    )
  }
  if (!caso) return <p className="cargando">Cargando caso…</p>

  const h = caso.historia
  return (
    <Marco
      codigo="W10"
      titulo={resumenPaciente(h)}
      subtitulo={`${etiquetaDificultad(caso.dificultad)} · ${etiquetaRegion(caso.region)}`}
      ancho
    >
      <div className="caso">
        <figure className="caso-imagen">
          {caso.imagen_url ? (
            <img src={caso.imagen_url} alt="Imagen endoscópica del caso" />
          ) : (
            <div className="sin-imagen">La imagen se verá cuando el equipo cargue el dataset en Supabase.</div>
          )}
          <figcaption>{caso.licencia_imagen}</figcaption>
        </figure>

        <section className="historia" aria-label="Historia clínica">
          <h2>Motivo de consulta</h2>
          <p>{h.motivo}</p>
          <h2>Historia clínica</h2>
          <p>{h.texto}</p>
          <h2>Síntomas</h2>
          <ul>
            {h.sintomas.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
          <h2>Antecedentes</h2>
          <ul>
            {h.antecedentes.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </section>
      </div>

      <Mensaje tipo="info">
        Zona a explorar: <strong>{caso.ubicacion.hito_nombre}</strong>. La exploración 3D y tus decisiones llegan en
        la siguiente fase.
      </Mensaje>
      <Mensaje tipo="info">Caso sintético generado por IA con fines académicos.</Mensaje>
      <button className="primario" onClick={() => navegar('/inicio')}>
        Volver al inicio
      </button>
    </Marco>
  )
}

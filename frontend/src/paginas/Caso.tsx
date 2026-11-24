// Responsable: Cristian Cruz · W10 Presentación del caso clínico (RF-04)
// Muestra la historia sintética y la imagen. Nunca muestra la respuesta: la API no la envía.
// Fase 4: el botón "Resolver este caso" abre un intento (decisiones, IA y tutor).
// Fase 5: al resolver, el estudiante primero recorre el tracto en el simulador 3D (W09).
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { HistoriaCaso, ImagenCaso } from '../componentes/CasoClinico'
import { Marco, Mensaje } from '../componentes/Marco'
import { etiquetaDificultad, etiquetaRegion, mensajeErrorCaso, resumenPaciente } from '../estado/caso'
import { api, ErrorApi, type Caso as TipoCaso } from '../servicios/api'

export function Caso() {
  const { id = '' } = useParams()
  const navegar = useNavigate()
  const [caso, setCaso] = useState<TipoCaso | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [abriendo, setAbriendo] = useState(false)
  const pedido = useRef(false) // evita abrir dos intentos con doble clic

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

  async function resolver() {
    if (pedido.current) return
    pedido.current = true
    setAbriendo(true)
    try {
      const intento = await api.iniciarIntento(id)
      navegar(`/intento/${intento.id}`)
    } catch (e) {
      setError(e instanceof ErrorApi ? mensajeErrorCaso(e.status, e.message) : 'Error inesperado')
      pedido.current = false
      setAbriendo(false)
    }
  }

  if (error && !caso) {
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

  return (
    <Marco
      codigo="W10"
      titulo={resumenPaciente(caso.historia)}
      subtitulo={`${etiquetaDificultad(caso.dificultad)} · ${etiquetaRegion(caso.region)}`}
      ancho
    >
      <div className="caso">
        <ImagenCaso caso={caso} />
        <HistoriaCaso caso={caso} />
      </div>

      <Mensaje tipo="info">
        Zona a explorar: <strong>{caso.ubicacion.hito_nombre}</strong>. Al resolver, recorrerás el tracto con el
        endoscopio virtual y capturarás el hallazgo.
      </Mensaje>
      <Mensaje tipo="info">Caso sintético generado por IA con fines académicos.</Mensaje>
      {error && <Mensaje tipo="error">{error}</Mensaje>}
      <button className="primario" onClick={resolver} disabled={abriendo}>
        {abriendo ? 'Abriendo…' : 'Resolver este caso'}
      </button>
      <button className="secundario" onClick={() => navegar('/inicio')}>
        Volver al inicio
      </button>
    </Marco>
  )
}

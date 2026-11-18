// Responsable: Cristian Cruz · W07 Generando el caso y W08 Error al generar (RF-02.1, RF-14.4)
// Pide a la API un caso nuevo y, cuando está listo, abre su presentación (W10).
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { etiquetaDificultad, etiquetaRegion, leerSolicitud, mensajeErrorCaso } from '../estado/caso'
import { api, ErrorApi } from '../servicios/api'

export function NuevoCaso() {
  const navegar = useNavigate()
  const [params] = useSearchParams()
  const { dificultad, region } = leerSolicitud(params)
  const [error, setError] = useState<string | null>(null)
  // React (modo estricto) monta dos veces en desarrollo: esto evita pedir dos casos.
  const pedido = useRef(false)

  const generar = useCallback(async () => {
    setError(null)
    try {
      const caso = await api.generarCaso(dificultad, region)
      navegar(`/caso/${caso.id}`, { replace: true })
    } catch (e) {
      setError(e instanceof ErrorApi ? mensajeErrorCaso(e.status, e.message) : 'Ocurrió un error inesperado.')
    }
  }, [dificultad, region, navegar])

  useEffect(() => {
    if (pedido.current) return
    pedido.current = true
    void generar()
  }, [generar])

  const detalle = `${etiquetaDificultad(dificultad)} · ${region ? etiquetaRegion(region) : 'cualquier región'}`

  if (error) {
    return (
      <Marco codigo="W08" titulo="No se pudo generar el caso" subtitulo={detalle}>
        <Mensaje tipo="error">{error}</Mensaje>
        <button className="primario" onClick={generar}>
          Intentar de nuevo
        </button>
        <button className="secundario" onClick={() => navegar('/inicio')}>
          Volver al inicio
        </button>
      </Marco>
    )
  }

  return (
    <Marco codigo="W07" titulo="Generando tu caso…" subtitulo={detalle}>
      <div className="generando" role="status" aria-live="polite">
        <span className="girando" aria-hidden="true" />
        <p>La IA está eligiendo una imagen y redactando la historia clínica. Tarda unos segundos.</p>
      </div>
    </Marco>
  )
}

// Responsable: Cristian Cruz · Minimapa (RF-03.6) y lista de hitos (RF-03.3) del W09
// Los dos son suscriptores del bus de la escena (patrón Observer): se marcan solos
// cuando el endoscopio emite "hito_visitado".
import { useEffect, useState } from 'react'

import type { BusEscena } from '../escena/bus'
import { HITOS, NOMBRE_HITO, porcentajeHitos, proyectarMinimapa, type Hito, type Punto } from '../escena/ruta'

/** Hitos visitados según el bus. Arranca con los que ya estaban (al recargar la página). */
function useVisitados(bus: BusEscena | null, iniciales: string[]): Set<string> {
  const [visitados, setVisitados] = useState(() => new Set(iniciales))
  useEffect(() => {
    if (!bus) return
    return bus.suscribir('hito_visitado', (e) => {
      setVisitados((v) => new Set(v).add(String(e.datos.hito)))
    })
  }, [bus])
  return visitados
}

interface Props {
  bus: BusEscena | null
  iniciales: string[]
  ruta: Punto[]
  posiciones: Partial<Record<Hito, Punto>>
  posicion: Punto | null
  objetivo: string
}

const ANCHO = 180
const ALTO = 200

export function PanelEscena({ bus, iniciales, ruta, posiciones, posicion, objetivo }: Props) {
  const visitados = useVisitados(bus, iniciales)
  const [verMapa, setVerMapa] = useState(true) // RF-03.6: el minimapa se puede ocultar
  // Se proyectan juntos la ruta, los hitos y la cámara para que compartan la misma escala.
  const hitosConPunto = HITOS.filter((h) => posiciones[h])
  const todos = proyectarMinimapa(
    [...ruta, ...hitosConPunto.map((h) => posiciones[h]!), ...(posicion ? [posicion] : [])],
    ANCHO,
    ALTO,
  )
  const linea = todos.slice(0, ruta.length)
  const puntosHitos = todos.slice(ruta.length, ruta.length + hitosConPunto.length)
  const yo = posicion ? todos[todos.length - 1] : null

  return (
    <aside className="panel-escena" aria-label="Minimapa e hitos anatómicos">
      <section>
        <div className="titulo-mapa">
          <h2>Minimapa</h2>
          <button type="button" className="enlace" onClick={() => setVerMapa((v) => !v)} aria-expanded={verMapa}>
            {verMapa ? 'Ocultar' : 'Mostrar'}
          </button>
        </div>
        {verMapa && (
          <>
            <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="minimapa" role="img" aria-label="Recorrido del endoscopio">
              <polyline points={linea.map((p) => `${p.x},${p.y}`).join(' ')} className="minimapa-ruta" />
              {hitosConPunto.map((h, i) => (
                <circle
                  key={h}
                  cx={puntosHitos[i].x}
                  cy={puntosHitos[i].y}
                  r={h === objetivo ? 6 : 4}
                  className={`minimapa-hito${visitados.has(h) ? ' visitado' : ''}${h === objetivo ? ' objetivo' : ''}`}
                >
                  <title>{NOMBRE_HITO[h]}</title>
                </circle>
              ))}
              {yo && <circle cx={yo.x} cy={yo.y} r={5} className="minimapa-yo" />}
            </svg>
            <p className="ayuda leyenda">
              <span className="punto yo" /> Tú · <span className="punto objetivo" /> Zona del caso
            </p>
          </>
        )}
      </section>
      <section>
        <h2>Hitos anatómicos</h2>
        <ul className="hitos">
          {HITOS.map((h) => (
            <li key={h} className={visitados.has(h) ? 'visitado' : ''}>
              <span aria-hidden="true">{visitados.has(h) ? '✓' : '○'}</span> {NOMBRE_HITO[h]}
              {visitados.has(h) && <span className="sr-only"> (visitado)</span>}
            </li>
          ))}
        </ul>
        <p className="ayuda" role="status">
          {visitados.size} de {HITOS.length} visitados ({porcentajeHitos(visitados.size)} %)
        </p>
      </section>
    </aside>
  )
}

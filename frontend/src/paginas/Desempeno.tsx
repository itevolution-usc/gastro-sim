// Responsable: Cristian Cruz · W16 Tablero de desempeño del estudiante (RF-13)
// Muestra cómo decide el estudiante frente a la IA: precisión, errores de la IA que detecta,
// sobredependencia (se cambia a la IA equivocada) y calibración de su confianza.
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { decimal, etiquetaSemana, lineaSemanal, porcentaje } from '../estado/desempeno'
import { api, ErrorApi, type Desempeno as TipoDesempeno } from '../servicios/api'

const ANCHO = 640
const ALTO = 220

export function Desempeno() {
  const navegar = useNavigate()
  const [datos, setDatos] = useState<TipoDesempeno | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let vigente = true
    api
      .miDesempeno()
      .then((d) => vigente && setDatos(d))
      .catch((e) => vigente && setError(e instanceof ErrorApi ? e.message : 'No se pudo cargar tu desempeño'))
    return () => {
      vigente = false
    }
  }, [])

  return (
    <Marco codigo="W16" titulo="Mi desempeño" subtitulo="Cómo decides frente a la recomendación de la IA." ancho>
      {error && <Mensaje tipo="error">{error}</Mensaje>}
      {!datos && !error && <p className="ayuda">Cargando…</p>}
      {datos && datos.intentos === 0 && (
        <Mensaje tipo="info">Aún no has terminado casos. Resuelve el primero y aquí verás tus resultados.</Mensaje>
      )}
      {datos && datos.intentos > 0 && (
        <>
          <div className="indicadores">
            <article className="indicador">
              <h2>Precisión de decisiones</h2>
              <p className="cifra">{porcentaje(datos.precision)}</p>
              <p className="ayuda">
                {datos.aciertos} de {datos.intentos} casos
              </p>
            </article>
            <article className="indicador">
              <h2>Errores de la IA detectados</h2>
              <p className="cifra">{porcentaje(datos.deteccion)}</p>
              <p className="ayuda">
                {datos.errores_ia
                  ? `${datos.errores_ia_detectados} de ${datos.errores_ia}`
                  : 'La IA aún no se ha equivocado en tus casos'}
              </p>
            </article>
            <article className="indicador">
              <h2>Sobredependencia</h2>
              <p className="cifra">{porcentaje(datos.sobredependencia)}</p>
              <p className="ayuda">
                Te cambiaste a la IA equivocada {datos.siguio_ia_errada} {datos.siguio_ia_errada === 1 ? 'vez' : 'veces'}
              </p>
            </article>
            <article className="indicador">
              <h2>Calibración de confianza</h2>
              <p className="cifra">{decimal(datos.calibracion)}</p>
              <p className="ayuda">{datos.calibracion_etiqueta ?? '—'} · 1,00 es perfecta</p>
            </article>
          </div>

          <section className="grafica" aria-labelledby="titulo-grafica">
            <h2 id="titulo-grafica">Precisión por semana</h2>
            <Grafica datos={datos} />
            <p className="leyenda">
              <span className="muestra precision" /> Precisión <span className="muestra deteccion" /> Detección de errores de
              la IA
            </p>
          </section>

          <details className="historia-plegada">
            <summary>¿Cómo se calcula?</summary>
            <ul className="explicacion">
              <li>
                <strong>Precisión:</strong> casos con la decisión final correcta.
              </li>
              <li>
                <strong>Errores de la IA detectados:</strong> de los casos en que la IA sugirió algo equivocado (a propósito o
                no), en cuántos no la seguiste.
              </li>
              <li>
                <strong>Sobredependencia:</strong> de esos casos en que empezaste con otra respuesta, en cuántos te cambiaste a
                la de la IA.
              </li>
              <li>
                <strong>Calibración:</strong> si dices que estás muy seguro (5), deberías acertar casi siempre; si dices 1, casi
                nunca.
              </li>
            </ul>
          </details>
        </>
      )}
      <button className="secundario" onClick={() => navegar('/inicio')}>
        Volver al inicio
      </button>
    </Marco>
  )
}

function Grafica({ datos }: { datos: TipoDesempeno }) {
  const serie = datos.por_semana
  const precision = lineaSemanal(serie, 'precision', ANCHO, ALTO)
  const deteccion = lineaSemanal(serie, 'deteccion', ANCHO, ALTO)
  const puntos = (t: { x: number; y: number }[]) => t.map((p) => `${p.x},${p.y}`).join(' ')
  return (
    <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="lienzo-grafica" role="img" aria-label="Precisión y detección de errores de la IA por semana">
      {[0, 0.5, 1].map((v) => {
        const y = ALTO - 24 - v * (ALTO - 48)
        return (
          <g key={v}>
            <line x1={24} x2={ANCHO - 24} y1={y} y2={y} className="guia" />
            <text x={4} y={y + 4} className="eje">
              {v * 100}
            </text>
          </g>
        )
      })}
      {precision.map((t, i) => (
        <g key={`p${i}`} className="serie precision">
          <polyline points={puntos(t)} />
          {t.map((p) => (
            <circle key={`${p.x}`} cx={p.x} cy={p.y} r={4} />
          ))}
        </g>
      ))}
      {deteccion.map((t, i) => (
        <g key={`d${i}`} className="serie deteccion">
          <polyline points={puntos(t)} />
          {t.map((p) => (
            <circle key={`${p.x}`} cx={p.x} cy={p.y} r={4} />
          ))}
        </g>
      ))}
      {serie.map((s, i) => {
        const x = serie.length > 1 ? 24 + (i * (ANCHO - 48)) / (serie.length - 1) : ANCHO / 2
        return (
          <text key={s.semana} x={x} y={ALTO - 4} className="eje" textAnchor="middle">
            {etiquetaSemana(s.semana)}
          </text>
        )
      })}
    </svg>
  )
}

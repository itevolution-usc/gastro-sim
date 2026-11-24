// Responsable: Cristian Cruz · Resolver un caso: W09 simulador 3D (fase 5), W10 decisión inicial,
// W11 recomendación y tutor, W13 tutor no disponible (aviso dentro del chat) y W14 retroalimentación.
// La pantalla cambia según el estado que devuelve la API; la respuesta correcta solo llega al final.
import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { ChatTutor } from '../componentes/ChatTutor'
import { FormDecision } from '../componentes/FormDecision'
import { HistoriaCaso, ImagenCaso } from '../componentes/CasoClinico'
import { Marco, Mensaje } from '../componentes/Marco'
import type { BusEscena } from '../escena/bus'
import { TelemetriaBuffer } from '../escena/telemetria'

// RNF-02: three.js pesa ~700 KB; se descarga solo al abrir el simulador, no al iniciar sesión.
const Escena3D = lazy(() => import('../componentes/Escena3D').then((m) => ({ default: m.Escena3D })))
import { etiquetaDificultad, etiquetaRegion, resumenPaciente } from '../estado/caso'
import { etiquetaAlteracion, etiquetaConfianza, mensajeErrorIntento, pantallaDe, porcentaje } from '../estado/intento'
import { api, ErrorApi, type Caso, type Intento as TipoIntento, type MensajeTutor } from '../servicios/api'

export function Intento() {
  const { id = '' } = useParams()
  const navegar = useNavigate()
  const [intento, setIntento] = useState<TipoIntento | null>(null)
  const [caso, setCaso] = useState<Caso | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const repitiendo = useRef(false)
  // Fase 5: telemetría de la escena 3D (RF-12) y "decidir con la imagen" si no encuentra el hallazgo.
  const telemetria = useRef<TelemetriaBuffer | null>(null)
  const [omitido, setOmitido] = useState(false)

  const fallar = useCallback((e: unknown) => {
    setError(e instanceof ErrorApi ? mensajeErrorIntento(e.status, e.message) : 'Error inesperado')
  }, [])

  useEffect(() => {
    let vigente = true
    api
      .verIntento(id)
      .then(async (i) => {
        const c = await api.verCaso(i.caso_id)
        if (vigente) {
          setIntento(i)
          setCaso(c)
        }
      })
      .catch((e) => vigente && fallar(e))
    return () => {
      vigente = false
    }
  }, [id, fallar])

  // Cada 3 s se envía lo que juntó la escena; al salir de la página, lo que quede.
  useEffect(() => {
    if (!id) return
    const buffer = new TelemetriaBuffer((eventos) => api.registrarEventos(id, eventos))
    telemetria.current = buffer
    const enviar = () => buffer.enviarLote().catch(() => undefined) // si falla, se reintenta en el siguiente envío
    const reloj = window.setInterval(enviar, 3000)
    return () => {
      window.clearInterval(reloj)
      void enviar()
      telemetria.current = null
    }
  }, [id])

  const conectarBus = useCallback((bus: BusEscena) => {
    bus.suscribir('*', (e) => telemetria.current?.agregar(e))
  }, [])

  /** Hallazgo capturado: se envía la telemetría y se recarga el intento (estado "hallazgo_capturado"). */
  async function alCapturar() {
    setOcupado(true)
    try {
      await telemetria.current?.enviarLote()
      setIntento(await api.verIntento(id))
    } catch (e) {
      fallar(e)
    } finally {
      setOcupado(false)
    }
  }

  function alOmitir() {
    void telemetria.current?.enviarLote().catch(() => undefined)
    setOmitido(true)
  }

  async function accion(hacer: () => Promise<TipoIntento>) {
    setOcupado(true)
    setError(null)
    try {
      setIntento(await hacer())
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (e) {
      fallar(e)
    } finally {
      setOcupado(false)
    }
  }

  async function preguntar(texto: string) {
    if (!intento) return
    const propio: MensajeTutor = { emisor: 'estudiante', contenido: texto, es_respaldo: false, creado_en: '' }
    setIntento({ ...intento, mensajes: [...intento.mensajes, propio] })
    setOcupado(true)
    setError(null)
    try {
      const r = await api.preguntarTutor(intento.id, texto)
      const respuesta: MensajeTutor = { emisor: 'tutor', contenido: r.respuesta, es_respaldo: r.es_respaldo, creado_en: '' }
      setIntento((i) => i && { ...i, mensajes: [...i.mensajes, respuesta], mensajes_restantes: r.mensajes_restantes })
    } catch (e) {
      fallar(e)
    } finally {
      setOcupado(false)
    }
  }

  async function repetir() {
    if (!caso || repitiendo.current) return
    repitiendo.current = true
    try {
      const nuevo = await api.iniciarIntento(caso.id)
      navegar(`/intento/${nuevo.id}`)
    } catch (e) {
      fallar(e)
    } finally {
      repitiendo.current = false
    }
  }

  if (!intento || !caso) {
    return error ? (
      <Marco codigo="W10" titulo="No se pudo abrir el caso">
        <Mensaje tipo="error">{error}</Mensaje>
        <button className="secundario" onClick={() => navegar('/inicio')}>
          Volver al inicio
        </button>
      </Marco>
    ) : (
      <p className="cargando">Cargando caso…</p>
    )
  }

  const pantalla = pantallaDe(intento.estado, omitido)
  const subtitulo = `${etiquetaDificultad(caso.dificultad)} · ${etiquetaRegion(caso.region)}`

  if (pantalla === 'retroalimentacion' && intento.retroalimentacion) {
    const r = intento.retroalimentacion
    return (
      <Marco codigo="W14" titulo={r.acierto_usuario ? '¡Acertaste!' : 'Esta vez no acertaste'} subtitulo={subtitulo} ancho>
        <div className="caso">
          <ImagenCaso caso={caso} />
          <section className="resultado" aria-label="Retroalimentación">
            <p className={r.acierto_usuario ? 'veredicto bien' : 'veredicto mal'}>
              Respuesta correcta: <strong>{r.referencia.nombre}</strong>
            </p>
            <dl className="datos">
              <dt>Tu decisión inicial</dt>
              <dd>
                {intento.decision_inicial?.nombre} ({etiquetaConfianza(intento.decision_inicial?.confianza ?? 0)})
              </dd>
              <dt>Recomendación de la IA</dt>
              <dd>
                {intento.recomendacion?.nombre} ({porcentaje(intento.recomendacion?.confianza ?? 0)})
              </dd>
              <dt>Tu decisión final</dt>
              <dd>
                {intento.decision_final?.nombre} ({etiquetaConfianza(intento.decision_final?.confianza ?? 0)})
              </dd>
              <dt>¿La IA fue alterada?</dt>
              <dd>{r.alterada ? `Sí · ${etiquetaAlteracion(r.tipo_alteracion)}` : 'No'}</dd>
            </dl>
            <ul className="explicacion">
              {r.explicacion.map((linea) => (
                <li key={linea}>{linea}</li>
              ))}
            </ul>
            <div className="puntaje" aria-label="Puntaje">
              <span>
                Acierto <strong>+{r.desglose.acierto}</strong>
              </span>
              <span>
                Detectar a la IA <strong>+{r.desglose.deteccion}</strong>
              </span>
              <span>
                Calibración <strong>+{r.desglose.calibracion}</strong>
              </span>
              <span className="total">
                Total <strong>{r.puntaje}</strong>
              </span>
            </div>
            <p>
              Llevas <strong>{r.puntos_totales}</strong> puntos · Nivel <strong>{r.nivel}</strong>
              {r.subio_de_nivel && ' · ¡Subiste de nivel! 🎉'}
            </p>
            {r.insignias_nuevas.map((i) => (
              <Mensaje key={i.codigo} tipo="info">
                🏅 Nueva insignia: <strong>{i.nombre}</strong>. {i.descripcion}
              </Mensaje>
            ))}
          </section>
        </div>
        {error && <Mensaje tipo="error">{error}</Mensaje>}
        <button className="primario" onClick={() => navegar('/inicio')}>
          Nuevo caso
        </button>
        <button className="secundario" onClick={repetir}>
          Repetir este caso
        </button>
      </Marco>
    )
  }

  if (pantalla === 'cerrado') {
    return (
      <Marco codigo="W14" titulo="Intento cerrado" subtitulo={subtitulo}>
        <Mensaje tipo="info">Este intento se cerró por inactividad.</Mensaje>
        <button className="primario" onClick={repetir}>
          Volver a intentarlo
        </button>
      </Marco>
    )
  }

  if (pantalla === 'recomendacion' && intento.recomendacion && intento.decision_inicial) {
    const rec = intento.recomendacion
    return (
      <Marco codigo="W11" titulo="Recomendación de la IA" subtitulo={subtitulo} ancho>
        <div className="caso">
          <ImagenCaso caso={caso} roi={rec.roi} />
          <section className="recomendacion" aria-label="Recomendación de la IA">
            <p className="ayuda">La IA puede equivocarse. Contrasta su sugerencia con lo que ves.</p>
            <p className="sugerencia">{rec.nombre}</p>
            <div className="barra" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(rec.confianza * 100)} aria-label="Confianza de la IA">
              <span style={{ width: porcentaje(rec.confianza).replace(' ', '') }} />
            </div>
            <p>
              Confianza de la IA: <strong>{porcentaje(rec.confianza)}</strong>. El recuadro marca la zona que la IA
              considera importante.
            </p>
            <p className="ayuda">
              Tu decisión inicial: <strong>{intento.decision_inicial.nombre}</strong> (
              {etiquetaConfianza(intento.decision_inicial.confianza)})
            </p>
          </section>
        </div>
        <div className="caso">
          <ChatTutor mensajes={intento.mensajes} restantes={intento.mensajes_restantes} ocupado={ocupado} onPreguntar={preguntar} />
          <FormDecision
            titulo="Tu decisión final"
            opciones={intento.opciones}
            inicial={intento.decision_inicial}
            textoBoton="Confirmar decisión final"
            ocupado={ocupado}
            onEnviar={(clase, confianza) => accion(() => api.decisionFinal(intento.id, clase, confianza))}
          />
        </div>
        {error && <Mensaje tipo="error">{error}</Mensaje>}
        <details className="historia-plegada">
          <summary>Ver la historia clínica</summary>
          <HistoriaCaso caso={caso} />
        </details>
      </Marco>
    )
  }

  // W09: el estudiante recorre el tracto en 3D y captura el hallazgo (RF-03).
  if (pantalla === 'exploracion') {
    return (
      <Marco codigo="W09" titulo="Simulador 3D" subtitulo={`${subtitulo} · Busca el hallazgo y captúralo`} ancho>
        <Suspense fallback={<p className="cargando-escena">Preparando el simulador 3D…</p>}>
          <Escena3D
          hallazgo={caso.ubicacion}
          etiqueta={subtitulo}
          zona={caso.ubicacion.hito_nombre}
          visitadosPrevios={intento.hitos_visitados ?? []}
          onBus={conectarBus}
          onCapturado={alCapturar}
          onOmitir={alOmitir}
          />
        </Suspense>
        {error && <Mensaje tipo="error">{error}</Mensaje>}
        <details className="historia-plegada">
          <summary>Ver la historia clínica</summary>
          <HistoriaCaso caso={caso} />
        </details>
      </Marco>
    )
  }

  // W10: el estudiante revisa imagen e historia y toma su decisión inicial (RF-05).
  return (
    <Marco codigo="W10" titulo={resumenPaciente(caso.historia)} subtitulo={subtitulo} ancho>
      <div className="caso">
        <ImagenCaso caso={caso} />
        <HistoriaCaso caso={caso} />
      </div>
      <Mensaje tipo="info">
        {intento.estado === 'explorando' ? (
          <>
            Decides con la imagen, sin captura 3D. Zona del caso: <strong>{caso.ubicacion.hito_nombre}</strong>.
          </>
        ) : (
          <>
            ✓ Hallazgo capturado en <strong>{caso.ubicacion.hito_nombre}</strong>. Esta es la imagen de la captura.
          </>
        )}{' '}
        Decide antes de ver la recomendación de la IA.
      </Mensaje>
      <FormDecision
        titulo="¿Qué hallazgo ves?"
        opciones={intento.opciones}
        textoBoton="Registrar decisión inicial"
        ocupado={ocupado}
        onEnviar={(clase, confianza) => accion(() => api.decisionInicial(intento.id, clase, confianza))}
      />
      {error && <Mensaje tipo="error">{error}</Mensaje>}
      <p className="ayuda">Caso sintético generado por IA con fines académicos.</p>
    </Marco>
  )
}

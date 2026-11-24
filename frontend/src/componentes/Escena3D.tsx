// Responsable: Cristian Cruz · W09 Simulador 3D (RF-03.1 a RF-03.6)
// Envoltorio de React para el motor three.js: muestra el lienzo, el cronómetro, la mira,
// el botón de captura, el minimapa y la lista de hitos. Los eventos salen por el bus.
import { useEffect, useRef, useState } from 'react'

import type { BusEscena } from '../escena/bus'
import { MotorEscena, type EstadoEscena, type ObjetivoHallazgo } from '../escena/motor'
import { cronometro, type Hito, type Punto } from '../escena/ruta'
import { PanelEscena } from './PanelEscena'

interface Props {
  hallazgo: ObjetivoHallazgo
  /** Texto de la cabecera, por ejemplo "Intermedio · Esófago". */
  etiqueta: string
  /** Nombre de la zona donde está el hallazgo, por ejemplo "Línea Z". */
  zona: string
  visitadosPrevios?: string[]
  /** Se llama una vez creado el motor, para que la página conecte la telemetría al bus. */
  onBus?: (bus: BusEscena) => void
  onCapturado: () => void
  onOmitir: () => void
  /** Ruta del modelo (las pruebas y la demo pueden usar otra). */
  urlModelo?: string
  /** Solo demo: posición inicial [avance 0–1, giro °, inclinación °]. */
  inicio?: [number, number, number]
}

type Carga = { fase: 'cargando'; progreso: number } | { fase: 'lista' } | { fase: 'error'; mensaje: string }

export function Escena3D({ hallazgo, etiqueta, zona, visitadosPrevios = [], onBus, onCapturado, onOmitir, urlModelo, inicio }: Props) {
  const lienzo = useRef<HTMLDivElement>(null)
  const motor = useRef<MotorEscena | null>(null)
  const ultimo = useRef<EstadoEscena | null>(null)
  const [bus, setBus] = useState<BusEscena | null>(null)
  const [carga, setCarga] = useState<Carga>({ fase: 'cargando', progreso: 0 })
  const [enVista, setEnVista] = useState(false)
  const [vista, setVista] = useState<{ segundos: number; posicion: Punto | null }>({ segundos: 0, posicion: null })
  const [ruta, setRuta] = useState<{ puntos: Punto[]; hitos: Partial<Record<Hito, Punto>> }>({ puntos: [], hitos: {} })
  const [aviso, setAviso] = useState<string | null>(null)
  const capturado = useRef(false)

  // Las funciones de la página pueden cambiar en cada render: se guardan en una referencia
  // para no reiniciar la escena 3D cada vez.
  const avisos = useRef({ onBus, onCapturado })
  avisos.current = { onBus, onCapturado }

  useEffect(() => {
    const contenedor = lienzo.current
    if (!contenedor) return
    let m: MotorEscena
    try {
      m = new MotorEscena(contenedor, hallazgo, (estado) => {
        ultimo.current = estado
        setEnVista(estado.visibilidad.enVista) // React ignora el cambio si el valor es el mismo
      })
    } catch {
      setCarga({ fase: 'error', mensaje: 'Tu navegador o tu equipo no permiten gráficos 3D (WebGL).' })
      return
    }
    motor.current = m
    m.marcarVisitados(visitadosPrevios)
    setBus(m.bus)
    avisos.current.onBus?.(m.bus)

    let vigente = true
    m.cargar(urlModelo, (p) => vigente && setCarga({ fase: 'cargando', progreso: p }))
      .then(() => {
        if (!vigente) return
        if (inicio) m.irA(...inicio)
        setRuta({ puntos: m.puntosRuta(), hitos: m.posicionesHitos() })
        setCarga({ fase: 'lista' })
        contenedor.focus()
      })
      .catch((e: unknown) => {
        if (vigente) setCarga({ fase: 'error', mensaje: e instanceof Error ? e.message : 'No se pudo cargar el modelo 3D.' })
      })

    // El cronómetro y el minimapa se refrescan 4 veces por segundo: suficiente y no recarga React.
    const reloj = window.setInterval(() => {
      const e = ultimo.current
      if (e) setVista({ segundos: e.segundos, posicion: e.posicion })
    }, 250)
    const visibilidad = () => m.pausar(document.hidden)
    document.addEventListener('visibilitychange', visibilidad)

    return () => {
      vigente = false
      window.clearInterval(reloj)
      document.removeEventListener('visibilitychange', visibilidad)
      m.destruir()
      motor.current = null
    }
    // La escena se crea una sola vez por hallazgo; los hitos previos solo cuentan al inicio.
  }, [hallazgo.x, hallazgo.y, hallazgo.z, hallazgo.radio_visibilidad, urlModelo])

  function capturar() {
    if (!motor.current || capturado.current) return
    if (motor.current.capturar()) {
      capturado.current = true
      avisos.current.onCapturado()
    } else {
      setAviso('Acércate a la zona del caso y céntrala en la mira antes de capturar.')
      window.setTimeout(() => setAviso(null), 2500)
    }
  }

  function omitir() {
    motor.current?.omitir()
    onOmitir()
  }

  const boton = (sentido: -1 | 0 | 1) => () => motor.current?.moverConBoton(sentido)

  return (
    <div className="simulador">
      <div className="escena">
        <div
          ref={lienzo}
          className="lienzo-3d"
          tabIndex={0}
          role="application"
          aria-label="Simulador de endoscopia. W y S avanzan, A y D giran, Q y E rotan, arrastra con el mouse para orientar la punta."
        />
        <div className="hud arriba-izq">
          <strong>{etiqueta}</strong>
          <span>
            Zona: {zona} · ⏱ {cronometro(vista.segundos)}
          </span>
        </div>
        <div className={`mira${enVista ? ' en-vista' : ''}`} aria-hidden="true" />
        {enVista && <div className="hud etiqueta-hallazgo">Zona del caso en el campo de visión</div>}
        {aviso && (
          <div className="hud aviso" role="alert">
            {aviso}
          </div>
        )}
        <div className="hud abajo-izq">W/S avanzar · A/D girar · mouse orientar punta · Q/E rotar</div>
        <div className="mandos" aria-label="Mover el endoscopio">
          <button
            type="button"
            className="secundario"
            onPointerDown={boton(-1)}
            onPointerUp={boton(0)}
            onPointerLeave={boton(0)}
            aria-label="Retroceder"
          >
            ◀ Retroceder
          </button>
          <button
            type="button"
            className="secundario"
            onPointerDown={boton(1)}
            onPointerUp={boton(0)}
            onPointerLeave={boton(0)}
            aria-label="Avanzar"
          >
            Avanzar ▶
          </button>
        </div>
        <button type="button" className="capturar" onClick={capturar} disabled={carga.fase !== 'lista'}>
          📷 Capturar hallazgo
        </button>
        {carga.fase === 'cargando' && (
          <div className="velo" role="status">
            <div className="girando" />
            Cargando el modelo 3D… {Math.round(carga.progreso * 100)} %
          </div>
        )}
        {carga.fase === 'error' && (
          <div className="velo" role="alert">
            <p>{carga.mensaje}</p>
            <button type="button" className="primario" onClick={omitir}>
              Continuar con la imagen del caso
            </button>
          </div>
        )}
      </div>
      <PanelEscena
        bus={bus}
        iniciales={visitadosPrevios}
        ruta={ruta.puntos}
        posiciones={ruta.hitos}
        posicion={vista.posicion}
        objetivo={hallazgo.hito}
      />
      {carga.fase === 'lista' && (
        <button type="button" className="enlace omitir" onClick={omitir}>
          No encuentro el hallazgo: decidir con la imagen
        </button>
      )}
    </div>
  )
}

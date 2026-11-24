// Responsable: Cristian Cruz · W19 Docente: configuración de errores de la IA y exportación
// RF-08.1 y RF-08.2: qué % de intentos recibe una recomendación alterada y de qué tipos.
// RF-15: descarga del CSV seudonimizado con los intentos (sin nombres ni correos).
import { useEffect, useState, type FormEvent } from 'react'

import { Marco, Mensaje } from '../componentes/Marco'
import { NavDocente } from '../componentes/NavDocente'
import { ajustarPorcentaje, avisoConfiguracion, nombreCsv, PORCENTAJE_MAXIMO, TIPOS_ALTERACION } from '../estado/docente'
import { fechaCorta } from '../estado/progreso'
import { api, ErrorApi, type ConfigAlteraciones, type TipoAlteracion } from '../servicios/api'

function mensajeError(e: unknown): string {
  return e instanceof ErrorApi ? e.message : 'Error inesperado'
}

export function DocenteConfig() {
  const [config, setConfig] = useState<ConfigAlteraciones | null>(null)
  const [porcentaje, setPorcentaje] = useState(0)
  const [tipos, setTipos] = useState<TipoAlteracion[]>([])
  const [guardando, setGuardando] = useState(false)
  const [descargando, setDescargando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  useEffect(() => {
    let vigente = true
    api
      .verAlteraciones()
      .then((c) => {
        if (!vigente) return
        setConfig(c)
        setPorcentaje(ajustarPorcentaje(c.porcentaje))
        setTipos(c.tipos)
      })
      .catch((e) => vigente && setError(mensajeError(e)))
    return () => {
      vigente = false
    }
  }, [])

  function alternar(tipo: TipoAlteracion) {
    setAviso(null)
    setTipos((t) => (t.includes(tipo) ? t.filter((x) => x !== tipo) : [...t, tipo]))
  }

  async function guardar(e: FormEvent) {
    e.preventDefault()
    setGuardando(true)
    setError(null)
    try {
      const c = await api.guardarAlteraciones(porcentaje, tipos)
      setConfig(c)
      setPorcentaje(ajustarPorcentaje(c.porcentaje))
      setTipos(c.tipos)
      setAviso('Configuración guardada. Se aplica a los intentos que empiecen desde ahora.')
    } catch (err) {
      setError(mensajeError(err))
    } finally {
      setGuardando(false)
    }
  }

  async function descargar() {
    setDescargando(true)
    setError(null)
    try {
      const archivo = await api.exportarIntentos()
      const url = URL.createObjectURL(archivo)
      const enlace = document.createElement('a')
      enlace.href = url
      enlace.download = nombreCsv()
      enlace.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000) // Firefox necesita la URL un momento más
    } catch (err) {
      setError(mensajeError(err))
    } finally {
      setDescargando(false)
    }
  }

  const advertencia = avisoConfiguracion(porcentaje, tipos)

  return (
    <Marco codigo="W19" titulo="Configuración y exportación" ancho>
      <NavDocente />
      {error && <Mensaje tipo="error">{error}</Mensaje>}
      <div className="config-docente">
        <form className="formulario panel" onSubmit={guardar}>
          <h2>Inyección de errores de la IA</h2>
          {!config && !error && <p className="ayuda">Cargando configuración…</p>}
          {config && (
            <>
              <label>
                Porcentaje de intentos con recomendación alterada
                <span className="valor-porcentaje" aria-live="polite">
                  {porcentaje} %
                </span>
                <input
                  type="range"
                  min={0}
                  max={PORCENTAJE_MAXIMO}
                  step={5}
                  value={porcentaje}
                  onChange={(e) => {
                    setAviso(null)
                    setPorcentaje(ajustarPorcentaje(Number(e.target.value)))
                  }}
                />
                <span className="extremos">
                  <small>0 %</small>
                  <small>{PORCENTAJE_MAXIMO} %</small>
                </span>
              </label>
              <fieldset>
                <legend>Tipos de alteración</legend>
                {TIPOS_ALTERACION.map((t) => (
                  <label key={t.tipo} className="casilla">
                    <input type="checkbox" checked={tipos.includes(t.tipo)} onChange={() => alternar(t.tipo)} />
                    <span>
                      {t.etiqueta}
                      <br />
                      <small>{t.ayuda}</small>
                    </span>
                  </label>
                ))}
              </fieldset>
              {advertencia && <Mensaje tipo="info">{advertencia}</Mensaje>}
              <p className="ayuda">El estudiante solo sabe si hubo alteración en la retroalimentación (W14).</p>
              <p className="ayuda">
                {config.por_defecto
                  ? 'Ahora se usa la configuración por defecto.'
                  : `Vigente desde el ${fechaCorta(config.vigente_desde!)}.`}
              </p>
              {aviso && <Mensaje tipo="info">{aviso}</Mensaje>}
              <button className="primario" type="submit" disabled={guardando}>
                {guardando ? 'Guardando…' : 'Guardar'}
              </button>
            </>
          )}
        </form>

        <section className="panel" aria-labelledby="titulo-exportar">
          <h2 id="titulo-exportar">Exportar datos de los intentos</h2>
          <p>Descarga un archivo CSV con todos los intentos terminados.</p>
          <p className="ayuda">
            Columnas: participante (seudónimo), caso, dificultad, referencia, alteración, decisiones y confianza,
            aciertos, puntaje, tiempos, hitos visitados y mensajes al tutor.
          </p>
          <Mensaje tipo="info">🔒 Datos seudonimizados: el archivo no incluye nombres ni correos electrónicos.</Mensaje>
          <button className="primario" type="button" onClick={descargar} disabled={descargando}>
            {descargando ? 'Preparando…' : '⬇ Descargar CSV'}
          </button>
        </section>
      </div>
    </Marco>
  )
}

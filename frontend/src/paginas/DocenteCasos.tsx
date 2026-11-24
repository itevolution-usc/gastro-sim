// Responsable: Cristian Cruz · W18 Docente: revisión de casos generados (RF-14.6)
// El docente ve la respuesta, cómo se generó el caso y la validación automática.
// Aprueba o descarta con motivo; un caso descartado ya no se asigna ni se puede repetir.
import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { HistoriaCaso, ImagenCaso } from '../componentes/CasoClinico'
import { Marco, Mensaje } from '../componentes/Marco'
import { NavDocente } from '../componentes/NavDocente'
import { etiquetaDificultad, etiquetaRegion } from '../estado/caso'
import { codigoCaso, estadoReglas, haceCuanto, motivoValido, PESTANAS, segundos } from '../estado/docente'
import { api, ErrorApi, type CasoDocente, type EstadoCaso } from '../servicios/api'

function mensajeError(e: unknown): string {
  return e instanceof ErrorApi ? e.message : 'Error inesperado'
}

export function DocenteCasos() {
  const [pestana, setPestana] = useState<EstadoCaso>('pendiente')
  const [conteo, setConteo] = useState<Record<EstadoCaso, number> | null>(null)
  const [casos, setCasos] = useState<CasoDocente[] | null>(null)
  const [elegido, setElegido] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  const cargar = useCallback(async (estado: EstadoCaso) => {
    setCasos(null)
    setError(null)
    try {
      const [lista, resumen] = await Promise.all([api.casosDocente(estado), api.resumenCasos()])
      setCasos(lista)
      setConteo(resumen)
      setElegido((actual) => (lista.some((c) => c.id === actual) ? actual : (lista[0]?.id ?? null)))
    } catch (e) {
      setError(mensajeError(e))
      setCasos([])
    }
  }, [])

  useEffect(() => {
    // Carga inicial y al cambiar de pestaña (datos externos: la API).
    void cargar(pestana)
  }, [pestana, cargar])

  const caso = casos?.find((c) => c.id === elegido) ?? null

  async function revisado(texto: string) {
    setAviso(texto)
    await cargar(pestana)
    window.scrollTo({ top: 0, behavior: 'smooth' }) // el aviso queda arriba, a la vista
  }

  return (
    <Marco codigo="W18" titulo="Revisión de casos generados" subtitulo="Aprueba o descarta los casos que generó la IA." ancho>
      <NavDocente />
      <div className="pestanas" role="tablist" aria-label="Estado de los casos">
        {PESTANAS.map((p) => (
          <button
            key={p.estado}
            role="tab"
            type="button"
            aria-selected={pestana === p.estado}
            className={pestana === p.estado ? 'activa' : undefined}
            onClick={() => {
              setAviso(null)
              setPestana(p.estado)
            }}
          >
            {p.etiqueta} {conteo && <span className="conteo">({conteo[p.estado]})</span>}
          </button>
        ))}
      </div>
      {aviso && <Mensaje tipo="info">{aviso}</Mensaje>}
      {error && <Mensaje tipo="error">{error}</Mensaje>}
      {casos === null && <p className="ayuda">Cargando casos…</p>}
      {casos?.length === 0 && !error && <p className="ayuda">No hay casos en esta pestaña.</p>}

      {casos && casos.length > 0 && (
        <div className="revision">
          <ul className="lista-casos" aria-label="Casos">
            {casos.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  className={c.id === elegido ? 'elegido' : undefined}
                  aria-current={c.id === elegido}
                  onClick={() => setElegido(c.id)}
                >
                  <span>
                    <strong>{codigoCaso(c.id)}</strong> · {c.clase_nombre}
                  </span>
                  <small>
                    {etiquetaDificultad(c.dificultad)} · {haceCuanto(c.creado_en)} ·{' '}
                    {c.validacion?.ok ? 'validación ✓' : 'validación ✗'}
                  </small>
                </button>
              </li>
            ))}
          </ul>
          {caso && <DetalleCaso key={caso.id} caso={caso} alRevisar={revisado} />}
        </div>
      )}
    </Marco>
  )
}

function DetalleCaso({ caso, alRevisar }: { caso: CasoDocente; alRevisar: (aviso: string) => Promise<void> }) {
  const [motivo, setMotivo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // El caso del docente trae todo lo que usan ImagenCaso e HistoriaCaso (y además la respuesta).
  const paraVer = caso

  async function revisar(estado: 'aprobado' | 'descartado', e?: FormEvent) {
    e?.preventDefault()
    if (estado === 'descartado' && !motivoValido(motivo)) {
      setError('Para descartar un caso escribe el motivo.')
      return
    }
    setEnviando(true)
    setError(null)
    try {
      await api.revisarCaso(caso.id, estado, estado === 'descartado' ? motivo.trim() : undefined)
      await alRevisar(`Caso ${codigoCaso(caso.id)} ${estado === 'aprobado' ? 'aprobado' : 'descartado'}.`)
    } catch (err) {
      setError(mensajeError(err))
      setEnviando(false)
    }
  }

  return (
    <article className="detalle-caso" aria-label={`Caso ${codigoCaso(caso.id)}`}>
      <h2>Caso {codigoCaso(caso.id)}</h2>
      <div className="caso">
        <ImagenCaso caso={paraVer} />
        <dl className="datos ficha">
          <dt>Etiqueta</dt>
          <dd>{caso.clase_nombre}</dd>
          <dt>Región / ubicación 3D</dt>
          <dd>
            {etiquetaRegion(caso.region)} · {caso.ubicacion.hito_nombre}
          </dd>
          <dt>Modelo / instrucciones</dt>
          <dd>
            {caso.modelo_llm ?? '—'} · {caso.version_prompt ?? '—'}
          </dd>
          <dt>Semilla</dt>
          <dd>{caso.semilla ?? '—'}</dd>
          <dt>Tiempo de generación</dt>
          <dd>{segundos(caso.tiempo_generacion_ms)}</dd>
          {caso.motivo_descarte && (
            <>
              <dt>Motivo del descarte</dt>
              <dd>{caso.motivo_descarte}</dd>
            </>
          )}
        </dl>
      </div>
      <h3>Validación automática</h3>
      <ul className="reglas">
        {estadoReglas(caso.validacion).map((r) => (
          <li key={r.etiqueta} className={r.ok ? 'bien' : 'mal'}>
            {r.ok ? '✓' : '✗'} {r.etiqueta}
          </li>
        ))}
      </ul>
      <details className="historia-plegada" open>
        <summary>Historia clínica</summary>
        <HistoriaCaso caso={paraVer} />
      </details>

      {caso.estado === 'pendiente' ? (
        <form className="formulario acciones-revision" onSubmit={(e) => revisar('descartado', e)}>
          <label>
            Motivo del descarte <small>(obligatorio solo para descartar)</small>
            <input value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={500} placeholder="Ej.: la historia no es coherente con la imagen" />
          </label>
          {error && <Mensaje tipo="error">{error}</Mensaje>}
          <div className="botones">
            <button type="button" className="primario" disabled={enviando} onClick={() => revisar('aprobado')}>
              Aprobar
            </button>
            <button type="submit" className="peligro" disabled={enviando}>
              Descartar
            </button>
          </div>
        </form>
      ) : (
        <p className="ayuda">
          Este caso ya fue {caso.estado}
          {caso.revisado_en ? ` (${haceCuanto(caso.revisado_en)})` : ''}.
        </p>
      )}
    </article>
  )
}

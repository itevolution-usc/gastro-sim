// Responsable: Cristian Cruz · W06 Inicio del estudiante y W17 cerrar sesión
// Fase 3: formulario "Nuevo caso" (RF-02.1, RF-02.2).
// Fase 6: "Mi progreso" (nivel, puntos e insignias, RF-11), "Historial de casos" con
// Repetir (RF-02.3) y, para docentes, el acceso a W18 y W19.
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { DIFICULTADES, etiquetaDificultad, etiquetaRegion, mensajeErrorCaso, REGIONES } from '../estado/caso'
import { esDocente } from '../estado/docente'
import { accionHistorial, avanceNivel, fechaCorta, resultado } from '../estado/progreso'
import { useSesion } from '../estado/sesion'
import { api, ErrorApi, type Dificultad, type Progreso, type ResumenIntento } from '../servicios/api'
import { cerrarSesion } from '../servicios/auth'

export function Inicio() {
  const navegar = useNavigate()
  const perfil = useSesion((s) => s.perfil)
  // Fase 3 (RF-02.1, RF-02.2): el estudiante elige dificultad y, si quiere, región.
  const [dificultad, setDificultad] = useState<Dificultad>('basico')
  const [region, setRegion] = useState('')
  // Fase 6
  const [progreso, setProgreso] = useState<Progreso | null>(null)
  const [historial, setHistorial] = useState<ResumenIntento[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const repitiendo = useRef(false) // evita abrir dos intentos con doble clic

  useEffect(() => {
    let vigente = true
    Promise.all([api.miProgreso(), api.misIntentos()])
      .then(([p, h]) => {
        if (!vigente) return
        setProgreso(p)
        setHistorial(h)
      })
      .catch((e) => vigente && setError(e instanceof ErrorApi ? e.message : 'No se pudo cargar tu progreso'))
    return () => {
      vigente = false
    }
  }, [])

  if (!perfil) return null

  function nuevoCaso(e: FormEvent) {
    e.preventDefault()
    const params = new URLSearchParams({ dificultad, ...(region ? { region } : {}) })
    navegar(`/caso/nuevo?${params}`)
  }

  async function abrir(fila: ResumenIntento) {
    const accion = accionHistorial(fila)
    if (accion === 'continuar') return navegar(`/intento/${fila.id}`)
    if (accion !== 'repetir' || repitiendo.current) return
    repitiendo.current = true
    try {
      const intento = await api.iniciarIntento(fila.caso_id) // repetir = nuevo intento del mismo caso
      navegar(`/intento/${intento.id}`)
    } catch (e) {
      setError(e instanceof ErrorApi ? mensajeErrorCaso(e.status, e.message) : 'Error inesperado')
      repitiendo.current = false
    }
  }

  async function salir() {
    await cerrarSesion()
    navegar('/ingresar', { replace: true })
  }

  const avance = progreso ? avanceNivel(progreso) : null

  return (
    <Marco codigo="W06" titulo={`Hola, ${perfil.nombre_visible}`} subtitulo="¿Listo para un caso nuevo?" ancho>
      <div className="inicio">
        <div>
          <dl className="datos">
            <dt>Rol</dt>
            <dd>{perfil.rol}</dd>
            <dt>Seguridad</dt>
            <dd>Sesión verificada con doble factor ✔</dd>
            <dt>Códigos de recuperación</dt>
            <dd>{perfil.codigos_disponibles} disponibles</dd>
          </dl>
          {perfil.codigos_disponibles < 3 && (
            <Mensaje tipo="info">Te quedan pocos códigos de recuperación. Pronto podrás generar nuevos.</Mensaje>
          )}
          {esDocente(perfil) && (
            <nav className="accesos-docente" aria-label="Herramientas del docente">
              <h2>Docente</h2>
              <Link to="/docente/casos">Revisión de casos (W18)</Link>
              <Link to="/docente/configuracion">Configuración y exportación (W19)</Link>
            </nav>
          )}
          <form className="formulario nuevo-caso" onSubmit={nuevoCaso}>
            <h2>Nuevo caso clínico</h2>
            <label>
              Dificultad
              <select value={dificultad} onChange={(e) => setDificultad(e.target.value as Dificultad)}>
                {DIFICULTADES.map((d) => (
                  <option key={d.valor} value={d.valor}>
                    {d.etiqueta} · {d.ayuda}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Región
              <select value={region} onChange={(e) => setRegion(e.target.value)}>
                {REGIONES.map((r) => (
                  <option key={r.valor} value={r.valor}>
                    {r.etiqueta}
                  </option>
                ))}
              </select>
            </label>
            <button className="primario" type="submit">
              Generar caso
            </button>
          </form>
        </div>

        <section className="progreso" aria-labelledby="titulo-progreso">
          <h2 id="titulo-progreso">Mi progreso</h2>
          {!progreso && !error && <p className="ayuda">Cargando…</p>}
          {progreso && avance && (
            <>
              <p className="nivel-actual">
                Nivel {progreso.nivel} · <strong>{progreso.puntos.toLocaleString('es-CO')} puntos</strong>
              </p>
              <div className="barra" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={avance.porcentaje} aria-label="Avance al siguiente nivel">
                <span style={{ width: `${avance.porcentaje}%` }} />
              </div>
              <p className="ayuda">
                {progreso.puntos_siguiente_nivel === null
                  ? '¡Llegaste al nivel máximo!'
                  : `Faltan ${avance.faltan} puntos para el nivel ${progreso.nivel + 1}`}
              </p>
              <ul className="insignias">
                {progreso.insignias.map((i) => (
                  <li key={i.codigo} className={i.obtenida ? 'obtenida' : 'pendiente'} title={i.descripcion}>
                    <span aria-hidden="true">{i.obtenida ? '★' : '?'}</span> {i.obtenida ? i.nombre : 'Por descubrir'}
                    <span className="sr-only"> · {i.descripcion}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>

      <section className="historial" aria-labelledby="titulo-historial">
        <h2 id="titulo-historial">Historial de casos</h2>
        {error && <Mensaje tipo="error">{error}</Mensaje>}
        {historial?.length === 0 && <p className="ayuda">Aún no has resuelto casos. ¡Genera el primero!</p>}
        {historial && historial.length > 0 && (
          <div className="tabla-desplazable">
            <table>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Región</th>
                  <th scope="col">Dificultad</th>
                  <th scope="col">Resultado</th>
                  <th scope="col">Puntaje</th>
                  <th scope="col">
                    <span className="sr-only">Acción</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {historial.map((f) => {
                  const accion = accionHistorial(f)
                  return (
                    <tr key={f.id}>
                      <td>{fechaCorta(f.fecha)}</td>
                      <td>{etiquetaRegion(f.region)}</td>
                      <td>{etiquetaDificultad(f.dificultad)}</td>
                      <td className={f.acierto === false ? 'mal' : f.acierto ? 'bien' : undefined}>{resultado(f)}</td>
                      <td>{f.puntaje ?? '—'}</td>
                      <td>
                        {accion ? (
                          <button type="button" className="enlace" onClick={() => abrir(f)}>
                            {accion === 'repetir' ? 'Repetir' : 'Continuar'}
                          </button>
                        ) : (
                          <small className="ayuda">Caso retirado</small>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <button className="secundario cerrar-sesion" onClick={salir}>
        Cerrar sesión
      </button>
    </Marco>
  )
}

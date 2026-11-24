// Responsable: Cristian Cruz · W20 Usuarios y roles (RF-01.3) y W21 Confirmar restablecimiento de 2FA (RF-01.7)
// Docentes y administradores cambian el rol estudiante ↔ docente de otras cuentas.
// Solo el administrador restablece el 2FA, y antes debe confirmarlo (W21). Todo queda registrado.
import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { Marco, Mensaje } from '../componentes/Marco'
import { NavDocente } from '../componentes/NavDocente'
import { describirCambio, puedeCambiarRol, puedeRestablecer } from '../estado/desempeno'
import { haceCuanto } from '../estado/docente'
import { useSesion } from '../estado/sesion'
import { api, ErrorApi, type CambioAuditoria, type UsuarioAdmin } from '../servicios/api'

function mensajeError(e: unknown): string {
  return e instanceof ErrorApi ? e.message : 'Error inesperado'
}

export function Usuarios() {
  const yo = useSesion((s) => s.perfil)
  const [buscar, setBuscar] = useState('')
  const [usuarios, setUsuarios] = useState<UsuarioAdmin[] | null>(null)
  const [cambios, setCambios] = useState<CambioAuditoria[]>([])
  const [confirmar, setConfirmar] = useState<UsuarioAdmin | null>(null)
  const [ocupado, setOcupado] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  const cargar = useCallback(async (texto: string) => {
    setError(null)
    try {
      const [lista, registro] = await Promise.all([api.usuarios(texto), api.auditoria()])
      setUsuarios(lista)
      setCambios(registro)
    } catch (e) {
      setError(mensajeError(e))
      setUsuarios([])
    }
  }, [])

  useEffect(() => {
    void cargar('')
  }, [cargar])

  if (!yo) return null

  function buscarUsuarios(e: FormEvent) {
    e.preventDefault()
    setAviso(null)
    void cargar(buscar)
  }

  async function cambiarRol(u: UsuarioAdmin, rol: 'estudiante' | 'docente') {
    setOcupado(u.id)
    setError(null)
    try {
      await api.cambiarRol(u.id, rol)
      setAviso(`${u.correo} ahora es ${rol}. El cambio aplica de inmediato.`)
      await cargar(buscar)
    } catch (e) {
      setError(mensajeError(e))
    } finally {
      setOcupado(null)
    }
  }

  async function restablecer() {
    if (!confirmar) return
    const cuenta = confirmar
    setOcupado(cuenta.id)
    setError(null)
    try {
      await api.restablecer2fa(cuenta.id)
      setAviso(`Se restableció el 2FA de ${cuenta.correo}. En su próximo ingreso deberá activarlo de nuevo.`)
      setConfirmar(null)
      await cargar(buscar)
    } catch (e) {
      setError(mensajeError(e))
    } finally {
      setOcupado(null)
    }
  }

  return (
    <Marco codigo={confirmar ? 'W21' : 'W20'} titulo="Usuarios" ancho>
      <NavDocente />
      <form className="buscador" onSubmit={buscarUsuarios} role="search">
        <input
          type="search"
          value={buscar}
          onChange={(e) => setBuscar(e.target.value)}
          placeholder="🔍 Buscar por correo o nombre"
          aria-label="Buscar por correo o nombre"
          maxLength={100}
        />
        <button type="submit" className="secundario">
          Buscar
        </button>
      </form>
      {aviso && <Mensaje tipo="info">{aviso}</Mensaje>}
      {error && <Mensaje tipo="error">{error}</Mensaje>}
      {usuarios === null && <p className="ayuda">Cargando usuarios…</p>}
      {usuarios?.length === 0 && !error && <p className="ayuda">No hay cuentas que coincidan.</p>}

      {usuarios && usuarios.length > 0 && (
        <div className="tabla-desplazable">
          <table>
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Correo</th>
                <th scope="col">Rol</th>
                <th scope="col">Verificación 2FA</th>
                <th scope="col">Acción</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td>
                    {u.nombre}
                    {u.id === yo.id && <small className="ayuda"> (tú)</small>}
                  </td>
                  <td>{u.correo}</td>
                  <td>
                    {puedeCambiarRol(yo, u) ? (
                      <select
                        value={u.rol}
                        disabled={ocupado === u.id}
                        aria-label={`Rol de ${u.correo}`}
                        onChange={(e) => cambiarRol(u, e.target.value as 'estudiante' | 'docente')}
                      >
                        <option value="estudiante">Estudiante</option>
                        <option value="docente">Docente</option>
                      </select>
                    ) : (
                      <span className="rol">{u.rol}</span>
                    )}
                  </td>
                  <td className={u.mfa_activado ? 'bien' : 'pendiente'}>{u.mfa_activado ? '✓ Activa' : '⚠ Pendiente'}</td>
                  <td>
                    {puedeRestablecer(yo, u) ? (
                      <button type="button" className="enlace" disabled={ocupado === u.id} onClick={() => setConfirmar(u)}>
                        Restablecer 2FA
                      </button>
                    ) : (
                      <small className="ayuda">—</small>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="ayuda">
        El cambio de rol aplica de inmediato (RF-01.3). Las cuentas de administrador solo se cambian en la base de datos.
        {yo.rol !== 'admin' && ' Restablecer el 2FA es solo para administradores.'}
      </p>

      {cambios.length > 0 && (
        <section className="registro" aria-labelledby="titulo-registro">
          <h2 id="titulo-registro">Últimos cambios registrados</h2>
          <ul>
            {cambios.slice(0, 8).map((c, i) => (
              <li key={`${c.fecha}-${i}`}>
                {describirCambio(c)} <small className="ayuda">· {haceCuanto(c.fecha)}</small>
              </li>
            ))}
          </ul>
        </section>
      )}

      {confirmar && (
        <div className="fondo-modal" role="presentation" onClick={() => ocupado || setConfirmar(null)}>
          <div
            className="modal"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="titulo-w21"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.key === 'Escape' && !ocupado && setConfirmar(null)}
          >
            <h2 id="titulo-w21">Restablecer la verificación en dos pasos</h2>
            <p>
              Cuenta: <strong>{confirmar.correo}</strong>
            </p>
            <p>
              Se eliminarán su aplicación autenticadora y sus códigos de recuperación. En su próximo ingreso deberá activar de
              nuevo el 2FA.
            </p>
            <p className="ayuda">Quedará registrado: quién lo hizo, cuándo y a qué cuenta.</p>
            <div className="botones">
              <button type="button" className="secundario" disabled={!!ocupado} onClick={() => setConfirmar(null)} autoFocus>
                Cancelar
              </button>
              <button type="button" className="peligro" disabled={!!ocupado} onClick={restablecer}>
                {ocupado ? 'Restableciendo…' : 'Restablecer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Marco>
  )
}

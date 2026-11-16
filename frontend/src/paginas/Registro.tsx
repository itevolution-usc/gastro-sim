// Responsable: Cristian Cruz · W02 Crear cuenta (RF-01.1)
// La cuenta nace con rol "estudiante": el perfil lo crea la base de datos
// automáticamente (disparador de Jahan) al registrarse en Supabase.
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { useSesion } from '../estado/sesion'
import { registrar } from '../servicios/auth'

const MINIMO = 8

export function Registro() {
  const navegar = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [repetir, setRepetir] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [confirmarCorreo, setConfirmarCorreo] = useState(false)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < MINIMO) return setError(`La contraseña debe tener al menos ${MINIMO} caracteres.`)
    if (password !== repetir) return setError('Las contraseñas no coinciden.')
    setEnviando(true)
    try {
      const conSesion = await registrar(email.trim(), password)
      if (conSesion) navegar(await useSesion.getState().actualizar(), { replace: true })
      else setConfirmarCorreo(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear la cuenta')
    } finally {
      setEnviando(false)
    }
  }

  if (confirmarCorreo) {
    return (
      <Marco codigo="W02" titulo="Revisa tu correo">
        <Mensaje tipo="info">
          Te enviamos un enlace a <strong>{email}</strong>. Ábrelo para confirmar tu cuenta y luego inicia sesión.
        </Mensaje>
        <p className="enlaces">
          <Link to="/ingresar">Ir a iniciar sesión</Link>
        </p>
      </Marco>
    )
  }

  return (
    <Marco codigo="W02" titulo="Crea tu cuenta" subtitulo="Tu cuenta inicia con el rol de estudiante.">
      <form onSubmit={enviar} className="formulario">
        <label>
          Correo
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          <span>
            Contraseña <small>(mínimo {MINIMO} caracteres)</small>
          </span>
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={MINIMO}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label>
          Repite la contraseña
          <input
            type="password"
            autoComplete="new-password"
            required
            value={repetir}
            onChange={(e) => setRepetir(e.target.value)}
          />
        </label>
        {error && <Mensaje tipo="error">{error}</Mensaje>}
        <button className="primario" disabled={enviando}>
          {enviando ? 'Creando…' : 'Crear cuenta'}
        </button>
      </form>
      <p className="enlaces">
        ¿Ya tienes cuenta? <Link to="/ingresar">Inicia sesión</Link>
      </p>
    </Marco>
  )
}

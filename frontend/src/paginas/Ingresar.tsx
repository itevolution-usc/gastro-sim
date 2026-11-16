// Responsable: Cristian Cruz · W01 Inicio de sesión (RF-01.2)
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { useSesion } from '../estado/sesion'
import { iniciarSesion } from '../servicios/auth'

export function Ingresar() {
  const navegar = useNavigate()
  const errorSesion = useSesion((s) => s.error)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      await iniciarSesion(email.trim(), password)
      navegar(await useSesion.getState().actualizar(), { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo iniciar sesión')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Marco codigo="W01" titulo="Inicia sesión" subtitulo="Entrena tus decisiones clínicas junto a una IA.">
      <form onSubmit={enviar} className="formulario">
        <label>
          Correo
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {(error ?? errorSesion) && <Mensaje tipo="error">{error ?? errorSesion}</Mensaje>}
        <button className="primario" disabled={enviando}>
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
      <p className="enlaces">
        ¿No tienes cuenta? <Link to="/registro">Crear cuenta</Link>
      </p>
    </Marco>
  )
}

// Responsable: Cristian Cruz · W05 Código de recuperación (RF-01.6)
// Con la contraseña ya escrita (sesión aal1) y un código de recuperación,
// la API de Diego borra el 2FA perdido y el usuario lo vuelve a activar.
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { useSesion } from '../estado/sesion'
import { api } from '../servicios/api'
import { renovarSesion } from '../servicios/auth'

export function Recuperar() {
  const navegar = useNavigate()
  const [codigo, setCodigo] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      await api.recuperar(codigo.trim())
      // El token viejo aún dice que hay 2FA: se renueva antes de seguir.
      await renovarSesion()
      navegar(await useSesion.getState().actualizar(), { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo usar el código')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Marco
      codigo="W05"
      titulo="Usa un código de recuperación"
      subtitulo="Escribe uno de los 10 códigos que guardaste al activar el 2FA. Después deberás activarlo de nuevo."
    >
      <form onSubmit={enviar} className="formulario">
        <label>
          Código de recuperación
          <input
            className="codigo-grande"
            placeholder="XXXXX-XXXXX"
            autoComplete="off"
            required
            minLength={10}
            maxLength={20}
            value={codigo}
            onChange={(e) => setCodigo(e.target.value.toUpperCase())}
          />
        </label>
        {error && <Mensaje tipo="error">{error}</Mensaje>}
        <button className="primario" disabled={enviando}>
          {enviando ? 'Comprobando…' : 'Recuperar acceso'}
        </button>
      </form>
      <p className="enlaces">
        <Link to="/verificar">Volver a escribir el código de la app</Link>
      </p>
    </Marco>
  )
}

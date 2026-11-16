// Responsable: Cristian Cruz · W04 Verificación del segundo factor (RF-01.5)
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { useSesion } from '../estado/sesion'
import { cerrarSesion, verificarCodigo } from '../servicios/auth'

export function Verificar2FA() {
  const navegar = useNavigate()
  const [codigo, setCodigo] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      await verificarCodigo(codigo)
      navegar(await useSesion.getState().actualizar(), { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo verificar el código')
      setCodigo('')
    } finally {
      setEnviando(false)
    }
  }

  async function salir() {
    await cerrarSesion()
    navegar('/ingresar', { replace: true })
  }

  return (
    <Marco codigo="W04" titulo="Verificación en dos pasos" subtitulo="Escribe el código de 6 dígitos de tu app autenticadora.">
      <form onSubmit={enviar} className="formulario">
        <label>
          Código
          <input
            className="codigo-grande"
            inputMode="numeric"
            autoComplete="one-time-code"
            autoFocus
            pattern="[0-9]{6}"
            maxLength={6}
            required
            value={codigo}
            onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ''))}
          />
        </label>
        {error && <Mensaje tipo="error">{error}</Mensaje>}
        <button className="primario" disabled={enviando || codigo.length !== 6}>
          {enviando ? 'Verificando…' : 'Verificar'}
        </button>
      </form>
      <p className="enlaces">
        <Link to="/recuperar">¿Perdiste tu celular? Usa un código de recuperación</Link>
        <button className="enlace" onClick={salir}>
          Cerrar sesión
        </button>
      </p>
    </Marco>
  )
}

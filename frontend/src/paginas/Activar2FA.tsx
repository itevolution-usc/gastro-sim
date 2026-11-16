// Responsable: Cristian Cruz · W03 Aviso académico y activación del 2FA (RF-01.4, RF-01.5, RF-01.6)
// Tres pasos: 1) aceptar el aviso, 2) escanear el QR y confirmar un código,
// 3) guardar los 10 códigos de recuperación (se muestran una sola vez).
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { useSesion } from '../estado/sesion'
import { api } from '../servicios/api'
import { cerrarSesion, confirmarCodigo, iniciarActivacion } from '../servicios/auth'

function mensajeDe(err: unknown) {
  return err instanceof Error ? err.message : 'Ocurrió un error'
}

export function Activar2FA() {
  const navegar = useNavigate()
  const perfil = useSesion((s) => s.perfil)
  const [error, setError] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [acepta, setAcepta] = useState(false)
  const [factor, setFactor] = useState<{ factorId: string; qr: string; secreto: string } | null>(null)
  const [codigo, setCodigo] = useState('')
  const [codigos, setCodigos] = useState<string[] | null>(null)
  const [guardados, setGuardados] = useState(false)

  if (!perfil) return null

  async function accion(fn: () => Promise<void>) {
    setOcupado(true)
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(mensajeDe(err))
    } finally {
      setOcupado(false)
    }
  }

  const aceptarAviso = () =>
    accion(async () => {
      await api.aceptarAviso(perfil.version_aviso_vigente)
      await useSesion.getState().actualizar()
    })

  const generarQr = () => accion(async () => setFactor(await iniciarActivacion()))

  const confirmar = (e: FormEvent) => {
    e.preventDefault()
    return accion(async () => {
      await confirmarCodigo(factor!.factorId, codigo.trim())
      setCodigos((await api.generarCodigos()).codigos)
    })
  }

  // Cuenta con 2FA verificado en esta sesión pero sin códigos (cerró antes del paso 3).
  const soloCodigos = () => accion(async () => setCodigos((await api.generarCodigos()).codigos))

  function descargar() {
    const texto = `GASTRO-SIM · Códigos de recuperación de ${perfil!.email}\nCada código sirve UNA sola vez.\n\n${codigos!.join('\n')}\n`
    const enlace = document.createElement('a')
    enlace.href = URL.createObjectURL(new Blob([texto], { type: 'text/plain' }))
    enlace.download = 'gastro-sim-codigos-de-recuperacion.txt'
    enlace.click()
    URL.revokeObjectURL(enlace.href)
  }

  const terminar = () => accion(async () => navegar(await useSesion.getState().actualizar(), { replace: true }))
  const salir = () => accion(async () => {
    await cerrarSesion()
    navegar('/ingresar', { replace: true })
  })

  // ---------- Paso 1: aviso académico ----------
  if (!perfil.aviso_aceptado) {
    return (
      <Marco codigo="W03" titulo="Aviso académico" subtitulo="Paso 1 de 3">
        <div className="aviso">
          <p>GASTRO-SIM es un simulador de uso <strong>exclusivamente académico</strong>:</p>
          <ul>
            <li>No es un dispositivo médico y no realiza diagnósticos reales.</li>
            <li>Los casos son sintéticos y usan imágenes de un dataset público (HyperKvasir).</li>
            <li>La IA puede equivocarse, y a veces se altera a propósito para entrenar tu criterio.</li>
            <li>Tus decisiones se registran con un seudónimo para la investigación del curso.</li>
          </ul>
        </div>
        <label className="casilla">
          <input type="checkbox" checked={acepta} onChange={(e) => setAcepta(e.target.checked)} />
          Leí y acepto el aviso (versión {perfil.version_aviso_vigente})
        </label>
        {error && <Mensaje tipo="error">{error}</Mensaje>}
        <button className="primario" disabled={!acepta || ocupado} onClick={aceptarAviso}>
          Continuar
        </button>
      </Marco>
    )
  }

  // ---------- Paso 3: códigos de recuperación ----------
  if (codigos) {
    return (
      <Marco codigo="W03" titulo="Guarda tus códigos de recuperación" subtitulo="Paso 3 de 3">
        <Mensaje tipo="info">
          Si pierdes tu celular, cada código te permite entrar <strong>una sola vez</strong>. No se volverán a mostrar.
        </Mensaje>
        <ol className="codigos">
          {codigos.map((c) => (
            <li key={c}>
              <code>{c}</code>
            </li>
          ))}
        </ol>
        <button className="secundario" onClick={descargar}>
          Descargar como archivo .txt
        </button>
        <label className="casilla">
          <input type="checkbox" checked={guardados} onChange={(e) => setGuardados(e.target.checked)} />
          Guardé mis códigos en un lugar seguro
        </label>
        <button className="primario" disabled={!guardados || ocupado} onClick={terminar}>
          Ir al inicio
        </button>
      </Marco>
    )
  }

  // ---------- 2FA verificado, faltan los códigos ----------
  if (perfil.nivel_sesion === 'aal2') {
    return (
      <Marco codigo="W03" titulo="Genera tus códigos de recuperación" subtitulo="Paso 3 de 3">
        {error && <Mensaje tipo="error">{error}</Mensaje>}
        <button className="primario" disabled={ocupado} onClick={soloCodigos}>
          Generar códigos
        </button>
      </Marco>
    )
  }

  // ---------- Paso 2: escanear el QR ----------
  return (
    <Marco codigo="W03" titulo="Activa la verificación en dos pasos" subtitulo="Paso 2 de 3">
      <p>
        Instala en tu celular una app autenticadora (Google Authenticator, Microsoft Authenticator o Authy).
      </p>
      {!factor ? (
        <button className="primario" disabled={ocupado} onClick={generarQr}>
          {ocupado ? 'Generando…' : 'Mostrar mi código QR'}
        </button>
      ) : (
        <form onSubmit={confirmar} className="formulario">
          <img className="qr" src={factor.qr} alt="Código QR para la app autenticadora" />
          <details>
            <summary>¿No puedes escanear? Escribe esta clave</summary>
            <code className="secreto">{factor.secreto}</code>
          </details>
          <label>
            Código de 6 dígitos que muestra la app
            <input
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={codigo}
              onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ''))}
            />
          </label>
          <button className="primario" disabled={ocupado || codigo.length !== 6}>
            {ocupado ? 'Verificando…' : 'Activar'}
          </button>
        </form>
      )}
      {error && <Mensaje tipo="error">{error}</Mensaje>}
      <p className="enlaces">
        <button className="enlace" onClick={salir}>
          Cerrar sesión
        </button>
      </p>
    </Marco>
  )
}

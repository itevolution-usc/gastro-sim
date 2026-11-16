// Responsable: Cristian Cruz · W06 Inicio del estudiante (versión de la fase 2) y W17 cerrar sesión
// En la fase 3 aquí aparecerá el botón "Nuevo caso" del generador de casos (Emmanuel).
import { useNavigate } from 'react-router'

import { Marco, Mensaje } from '../componentes/Marco'
import { useSesion } from '../estado/sesion'
import { cerrarSesion } from '../servicios/auth'

export function Inicio() {
  const navegar = useNavigate()
  const perfil = useSesion((s) => s.perfil)
  if (!perfil) return null

  async function salir() {
    await cerrarSesion()
    navegar('/ingresar', { replace: true })
  }

  return (
    <Marco codigo="W06" titulo={`Hola, ${perfil.nombre_visible}`} subtitulo="Tu cuenta está lista.">
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
      <Mensaje tipo="info">El simulador de casos clínicos llega en la siguiente fase.</Mensaje>
      <button className="secundario" onClick={salir}>
        Cerrar sesión
      </button>
    </Marco>
  )
}

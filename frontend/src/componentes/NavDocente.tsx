// Responsable: Cristian Cruz · Menú y guardia de las pantallas del docente (W18 y W19)
import type { ReactNode } from 'react'
import { Navigate, NavLink } from 'react-router'

import { esDocente } from '../estado/docente'
import { useSesion } from '../estado/sesion'

/** Si la cuenta es de estudiante, vuelve al inicio. La API igual responde 403. */
export function SoloDocente({ children }: { children: ReactNode }) {
  const perfil = useSesion((s) => s.perfil)
  if (!esDocente(perfil)) return <Navigate to="/inicio" replace />
  return children
}

export function NavDocente() {
  const clase = ({ isActive }: { isActive: boolean }) => (isActive ? 'activo' : undefined)
  return (
    <nav className="nav-docente" aria-label="Menú del docente">
      <NavLink to="/docente/casos" className={clase}>
        Revisión de casos
      </NavLink>
      <NavLink to="/docente/configuracion" className={clase}>
        Configuración y exportación
      </NavLink>
      <NavLink to="/inicio" end>
        Volver al inicio
      </NavLink>
    </nav>
  )
}

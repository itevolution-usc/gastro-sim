// Responsable: Cristian Cruz · Guardia de rutas
// Antes de mostrar una pantalla, consulta el estado de la cuenta. Si al usuario
// le corresponde otra pantalla (por ejemplo, aún no verificó su 2FA), lo lleva allá.
// Así nadie llega al inicio sin aviso aceptado y sin segundo factor (RF-01.4, RF-01.5).
import { useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'

import type { Ruta } from '../estado/flujo'
import { useSesion } from '../estado/sesion'

interface Props {
  /** La pantalla se muestra solo si el flujo indica esta ruta. */
  permitir: Ruta
  children: ReactNode
}

export function Protegida({ permitir, children }: Props) {
  const navegar = useNavigate()
  const [lista, setLista] = useState(false)

  useEffect(() => {
    let vigente = true
    useSesion
      .getState()
      .actualizar()
      .then((destino) => {
        if (!vigente) return
        if (destino === permitir) setLista(true)
        else navegar(destino, { replace: true })
      })
    return () => {
      vigente = false
    }
  }, [permitir, navegar])

  if (!lista) return <p className="cargando">Cargando…</p>
  return children
}

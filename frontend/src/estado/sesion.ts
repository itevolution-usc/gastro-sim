// Responsable: Cristian Cruz · Estado global de la sesión (Zustand, ViewModel en MVVM)
// Guarda el perfil y calcula a qué pantalla debe ir el usuario.
import { create } from 'zustand'

import { api, ErrorApi, type Perfil } from '../servicios/api'
import { niveles } from '../servicios/auth'
import { supabase } from '../servicios/supabase'
import { siguientePantalla, type Ruta } from './flujo'

interface Sesion {
  perfil: Perfil | null
  cargando: boolean
  error: string | null
  /** Vuelve a consultar Supabase y la API, y devuelve la pantalla que corresponde. */
  actualizar: () => Promise<Ruta>
}

export const useSesion = create<Sesion>((set) => ({
  perfil: null,
  cargando: true,
  error: null,
  actualizar: async () => {
    set({ cargando: true, error: null })
    try {
      const { data } = await supabase.auth.getSession()
      if (!data.session) {
        set({ perfil: null, cargando: false })
        return '/ingresar'
      }
      const [{ actual, siguiente }, perfil] = await Promise.all([niveles(), api.miPerfil()])
      set({ perfil, cargando: false })
      return siguientePantalla({ haySesion: true, nivelActual: actual, nivelSiguiente: siguiente, perfil })
    } catch (e) {
      const mensaje = e instanceof ErrorApi || e instanceof Error ? e.message : 'Error inesperado'
      set({ perfil: null, cargando: false, error: mensaje })
      return '/ingresar'
    }
  },
}))

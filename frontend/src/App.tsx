// Responsable: Cristian Cruz · Rutas de la aplicación
// Cada pantalla de cuenta está protegida por el flujo: el usuario solo ve la
// que le corresponde según su sesión, su aviso y su 2FA.
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'

import { Marco } from './componentes/Marco'
import { Protegida } from './componentes/Protegida'
import { faltantes } from './config'
import { Activar2FA } from './paginas/Activar2FA'
import { Caso } from './paginas/Caso'
import { Ingresar } from './paginas/Ingresar'
import { Inicio } from './paginas/Inicio'
import { NuevoCaso } from './paginas/NuevoCaso'
import { Recuperar } from './paginas/Recuperar'
import { Registro } from './paginas/Registro'
import { Verificar2FA } from './paginas/Verificar2FA'

export default function App() {
  if (faltantes.length) {
    return (
      <Marco codigo="CONFIG" titulo="Falta configurar el frontend">
        <p>
          Crea el archivo <code>frontend/.env</code> a partir de <code>.env.example</code> y completa:
        </p>
        <ul>
          {faltantes.map((v) => (
            <li key={v}>
              <code>{v}</code>
            </li>
          ))}
        </ul>
        <p>
          Luego detén y vuelve a ejecutar <code>npm run dev</code>.
        </p>
      </Marco>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/ingresar" element={<Protegida permitir="/ingresar"><Ingresar /></Protegida>} />
        <Route path="/registro" element={<Protegida permitir="/ingresar"><Registro /></Protegida>} />
        <Route path="/activar" element={<Protegida permitir="/activar"><Activar2FA /></Protegida>} />
        <Route path="/verificar" element={<Protegida permitir="/verificar"><Verificar2FA /></Protegida>} />
        <Route path="/recuperar" element={<Protegida permitir="/verificar"><Recuperar /></Protegida>} />
        <Route path="/inicio" element={<Protegida permitir="/inicio"><Inicio /></Protegida>} />
        {/* Fase 3: casos clínicos. Exigen lo mismo que el inicio: aviso aceptado y 2FA verificado. */}
        <Route path="/caso/nuevo" element={<Protegida permitir="/inicio"><NuevoCaso /></Protegida>} />
        <Route path="/caso/:id" element={<Protegida permitir="/inicio"><Caso /></Protegida>} />
        <Route path="*" element={<Navigate to="/inicio" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

// Responsable: Cristian Cruz · Demo del simulador 3D SOLO para desarrollo (npm run dev → /demo-3d)
// Permite probar el modelo y los controles sin iniciar sesión ni tener la API corriendo.
// No existe en la versión compilada (npm run build): App.tsx solo la monta con import.meta.env.DEV.
import { useState } from 'react'

import { Escena3D } from '../componentes/Escena3D'
import { Marco, Mensaje } from '../componentes/Marco'
import type { EventoEscena } from '../escena/bus'

// Mismas ubicaciones que db/migraciones/002_catalogo_casos.sql
const UBICACIONES = {
  linea_z: { hito: 'linea_z', hito_nombre: 'Línea Z', x: 0.2, y: -19, z: 0, radio_visibilidad: 1.5 },
  cardias: { hito: 'cardias', hito_nombre: 'Cardias', x: 0, y: -22.5, z: 0.6, radio_visibilidad: 2 },
  piloro: { hito: 'piloro', hito_nombre: 'Píloro', x: 5, y: -28, z: 0, radio_visibilidad: 1.8, lesion_visible: false },
}

export function DemoEscena() {
  const params = new URLSearchParams(window.location.search)
  const zona = (params.get('zona') ?? 'linea_z') as keyof typeof UBICACIONES
  const hallazgo = UBICACIONES[zona] ?? UBICACIONES.linea_z
  // ?en=0.4,30,-10 → avance 0.4 de la ruta, giro 30°, inclinación −10° (para revisar vistas).
  const en = params.get('en')?.split(',').map(Number)
  const inicio = en && en.every((v) => Number.isFinite(v)) ? ([en[0], en[1] ?? 0, en[2] ?? 0] as [number, number, number]) : undefined
  const [eventos, setEventos] = useState<EventoEscena[]>([])
  const [fin, setFin] = useState<string | null>(null)

  return (
    <Marco codigo="W09 · DEMO" titulo="Simulador 3D (demo de desarrollo)" subtitulo={`Zona: ${hallazgo.hito_nombre}`} ancho>
      <Mensaje tipo="info">
        El píloro es un hallazgo normal: no muestra lesión (RF-03.4). Cambia la zona con <code>?zona=linea_z</code>, <code>?zona=cardias</code> o <code>?zona=piloro</code>. Para
        saltar a un punto: <code>&amp;en=0.4,30,-10</code> (avance 0–1, giro y inclinación en grados).
      </Mensaje>
      <Escena3D
        hallazgo={hallazgo}
        etiqueta="Demo · sin API"
        zona={hallazgo.hito_nombre}
        inicio={inicio}
        onBus={(bus) => bus.suscribir('*', (e) => setEventos((l) => [e, ...l].slice(0, 12)))}
        onCapturado={() => setFin('✓ Hallazgo capturado. En la app real aquí sigue la decisión inicial (W10).')}
        onOmitir={() => setFin('Omitido. En la app real aquí sigue la decisión con la imagen (W10).')}
      />
      {fin && <Mensaje tipo="info">{fin}</Mensaje>}
      <h2 className="titulo-eventos">Eventos que se enviarían a la API</h2>
      <ol className="eventos-demo" aria-live="polite">
        {eventos.map((e) => (
          <li key={e.ocurrido_en + e.tipo}>
            <code>{e.tipo}</code> {JSON.stringify(e.datos)}
          </li>
        ))}
      </ol>
    </Marco>
  )
}

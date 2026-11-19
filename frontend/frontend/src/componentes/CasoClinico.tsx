// Responsable: Cristian Cruz · Piezas del caso clínico reutilizadas en W10, W11 y W14
import type { Caso, Recomendacion } from '../servicios/api'
import { estiloRoi } from '../estado/intento'

/** Imagen endoscópica. Si llega un recuadro (ROI) de la IA, se dibuja encima (RF-06.2). */
export function ImagenCaso({ caso, roi }: { caso: Caso; roi?: Recomendacion['roi'] | null }) {
  return (
    <figure className="caso-imagen">
      <div className="lienzo">
        {caso.imagen_url ? (
          <img src={caso.imagen_url} alt="Imagen endoscópica del caso" />
        ) : (
          <div className="sin-imagen">La imagen se verá cuando el equipo cargue el dataset en Supabase.</div>
        )}
        {roi && <div className="roi" style={estiloRoi(roi)} aria-label="Zona señalada por la IA" />}
      </div>
      <figcaption>{caso.licencia_imagen}</figcaption>
    </figure>
  )
}

export function HistoriaCaso({ caso }: { caso: Caso }) {
  const h = caso.historia
  return (
    <section className="historia" aria-label="Historia clínica">
      <h2>Motivo de consulta</h2>
      <p>{h.motivo}</p>
      <h2>Historia clínica</h2>
      <p>{h.texto}</p>
      <h2>Síntomas</h2>
      <ul>
        {h.sintomas.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
      <h2>Antecedentes</h2>
      <ul>
        {h.antecedentes.map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ul>
    </section>
  )
}

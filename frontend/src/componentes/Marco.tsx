// Responsable: Cristian Cruz · Estructura común de las pantallas de cuenta (W01–W06)
import type { ReactNode } from 'react'

interface Props {
  codigo: string
  titulo: string
  subtitulo?: string
  children: ReactNode
}

export function Marco({ codigo, titulo, subtitulo, children }: Props) {
  return (
    <main className="pagina">
      <section className="tarjeta" aria-labelledby="titulo">
        <header className="marca">
          <span className="logo" aria-hidden="true">GS</span>
          <span>GASTRO-SIM</span>
          <small className="codigo">{codigo}</small>
        </header>
        <h1 id="titulo">{titulo}</h1>
        {subtitulo && <p className="subtitulo">{subtitulo}</p>}
        {children}
      </section>
      <p className="pie">Uso exclusivamente académico · No es un dispositivo médico</p>
    </main>
  )
}

export function Mensaje({ tipo, children }: { tipo: 'error' | 'info'; children: ReactNode }) {
  return (
    <p className={`mensaje ${tipo}`} role={tipo === 'error' ? 'alert' : 'status'}>
      {children}
    </p>
  )
}

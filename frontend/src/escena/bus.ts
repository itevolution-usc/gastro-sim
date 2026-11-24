// Responsable: Cristian Cruz · Bus de eventos de la escena 3D (patrón Observer, figura P5)
// El endoscopio y el hallazgo EMITEN eventos; la lista de hitos, el minimapa y la
// telemetría se SUSCRIBEN. Así ninguno conoce a los otros: se pueden agregar o quitar
// piezas sin tocar la escena.

/** Tipos que acepta la API en POST /intentos/{id}/eventos (RF-12). */
export type TipoEvento =
  | 'hito_visitado'
  | 'hallazgo_capturado'
  | 'hallazgo_omitido'
  | 'captura_invalida'
  | 'pausa'
  | 'reanudacion'

export interface EventoEscena {
  tipo: TipoEvento
  datos: Record<string, string | number | boolean>
  /** Momento del evento (ISO 8601), como lo pide la API. */
  ocurrido_en: string
}

type Suscriptor = (evento: EventoEscena) => void

export class BusEscena {
  private readonly suscriptores = new Map<TipoEvento | '*', Set<Suscriptor>>()

  /** Escucha un tipo de evento (o '*' para todos). Devuelve la función para dejar de escuchar. */
  suscribir(tipo: TipoEvento | '*', fn: Suscriptor): () => void {
    const lista = this.suscriptores.get(tipo) ?? new Set<Suscriptor>()
    lista.add(fn)
    this.suscriptores.set(tipo, lista)
    return () => {
      lista.delete(fn)
    }
  }

  /** Avisa a los suscriptores del tipo y a los de '*'. */
  emitir(tipo: TipoEvento, datos: EventoEscena['datos'] = {}, ahora: Date = new Date()): EventoEscena {
    const evento: EventoEscena = { tipo, datos, ocurrido_en: ahora.toISOString() }
    for (const fn of this.suscriptores.get(tipo) ?? []) fn(evento)
    for (const fn of this.suscriptores.get('*') ?? []) fn(evento)
    return evento
  }
}

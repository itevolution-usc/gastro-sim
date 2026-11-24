// Responsable: Cristian Cruz · TelemetriaBuffer (RF-12, figura P5)
// Junta los eventos de la escena y los envía a la API en lotes, no uno por uno:
// menos peticiones y la escena no se frena esperando a la red.
import type { EventoEscena } from './bus'

export type Enviar = (eventos: EventoEscena[]) => Promise<unknown>

/** Máximo que acepta la API por lote. */
export const MAX_LOTE = 200

export class TelemetriaBuffer {
  private pendientes: EventoEscena[] = []
  private enCurso: Promise<void> = Promise.resolve()

  private readonly enviar: Enviar

  constructor(enviar: Enviar) {
    this.enviar = enviar
  }

  get cantidad(): number {
    return this.pendientes.length
  }

  agregar(evento: EventoEscena): void {
    this.pendientes.push(evento)
  }

  /**
   * Envía lo pendiente en lotes de hasta MAX_LOTE, uno detrás de otro y en orden.
   * Si la red falla, los eventos vuelven a la cola para el siguiente intento.
   */
  enviarLote(): Promise<void> {
    this.enCurso = this.enCurso.then(async () => {
      while (this.pendientes.length > 0) {
        const lote = this.pendientes.splice(0, MAX_LOTE)
        try {
          await this.enviar(lote)
        } catch (e) {
          this.pendientes = [...lote, ...this.pendientes]
          throw e
        }
      }
    })
    // Un fallo no debe bloquear los envíos siguientes.
    const actual = this.enCurso
    this.enCurso = actual.catch(() => undefined)
    return actual
  }
}

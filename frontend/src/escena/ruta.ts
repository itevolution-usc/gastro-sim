// Responsable: Cristian Cruz · Reglas de la escena 3D (RF-03.2 a RF-03.6)
// Funciones puras, sin three.js ni React: se prueban en ruta.test.ts.
// Unidades: 1 = 1 cm. Ejes de la app: la boca está en (0, 0, 0) y el tubo baja por −Y.

export interface Punto {
  x: number
  y: number
  z: number
}

/** Recorrido del endoscopio: punto de inicio y los 7 hitos en orden (nombres exactos del .glb). */
export const RUTA = ['camara_inicio', 'linea_z', 'cardias', 'fondo', 'cuerpo', 'antro', 'piloro', 'bulbo'] as const
export const HITOS = RUTA.slice(1) as readonly Hito[]
export type Hito = Exclude<(typeof RUTA)[number], 'camara_inicio'>

export const NOMBRE_HITO: Record<Hito, string> = {
  linea_z: 'Línea Z',
  cardias: 'Cardias',
  fondo: 'Fondo gástrico',
  cuerpo: 'Cuerpo gástrico',
  antro: 'Antro',
  piloro: 'Píloro',
  bulbo: 'Bulbo duodenal',
}

/** Región de cada hito, para el minimapa. */
export const REGION_HITO: Record<Hito, 'esofago' | 'estomago' | 'duodeno'> = {
  linea_z: 'esofago',
  cardias: 'estomago',
  fondo: 'estomago',
  cuerpo: 'estomago',
  antro: 'estomago',
  piloro: 'estomago',
  bulbo: 'duodeno',
}

/** Distancia (cm) a la que un hito cuenta como visitado (RF-03.3). */
export const RADIO_HITO = 2.5
/** Distancia extra (cm) sobre el radio de visibilidad del caso para poder capturar. */
export const MARGEN_CAPTURA = 2
/** Ángulo máximo (grados) entre la mirada y el hallazgo para capturarlo: debe estar en el centro de la vista. */
export const ANGULO_CAPTURA = 30

export function distancia(a: Punto, b: Punto): number {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z)
}

/** Hitos que la cámara alcanza en esta posición y que aún no estaban visitados. */
export function hitosNuevos(
  camara: Punto,
  posiciones: Partial<Record<Hito, Punto>>,
  visitados: ReadonlySet<string>,
  radio = RADIO_HITO,
): Hito[] {
  return HITOS.filter((h) => {
    const p = posiciones[h]
    return p !== undefined && !visitados.has(h) && distancia(camara, p) <= radio
  })
}

/** Ángulo (grados) entre la dirección de la mirada y la dirección hacia el objetivo. */
export function anguloHacia(camara: Punto, mirada: Punto, objetivo: Punto): number {
  const hacia = { x: objetivo.x - camara.x, y: objetivo.y - camara.y, z: objetivo.z - camara.z }
  const n1 = Math.hypot(mirada.x, mirada.y, mirada.z)
  const n2 = Math.hypot(hacia.x, hacia.y, hacia.z)
  if (n1 === 0 || n2 === 0) return 0
  const coseno = (mirada.x * hacia.x + mirada.y * hacia.y + mirada.z * hacia.z) / (n1 * n2)
  return (Math.acos(Math.min(1, Math.max(-1, coseno))) * 180) / Math.PI
}

export interface Visibilidad {
  /** El hallazgo está cerca y en el centro de la vista: se puede capturar. */
  enVista: boolean
  distancia: number
  angulo: number
}

/**
 * ¿Se puede capturar el hallazgo? (RF-03.5)
 * Cerca: distancia ≤ radio_visibilidad del caso + MARGEN_CAPTURA. Centrado: ángulo ≤ ANGULO_CAPTURA.
 */
export function evaluarVisibilidad(camara: Punto, mirada: Punto, hallazgo: Punto, radioVisibilidad: number): Visibilidad {
  const d = distancia(camara, hallazgo)
  const a = anguloHacia(camara, mirada, hallazgo)
  return { enVista: d <= radioVisibilidad + MARGEN_CAPTURA && a <= ANGULO_CAPTURA, distancia: d, angulo: a }
}

/** Datos que se envían a la API al capturar (sin la clase: la escena nunca la conoce). */
export function datosCaptura(v: Visibilidad, hito: string, segundos: number) {
  return { hito, distancia: redondear(v.distancia), angulo: redondear(v.angulo), segundos: Math.round(segundos) }
}

/** Avance a lo largo de la ruta (0 = boca, 1 = final del duodeno), siempre dentro de los límites. */
export function moverAvance(actual: number, delta: number): number {
  return Math.min(1, Math.max(0, actual + delta))
}

/** RF-03.3: porcentaje de hitos visitados, por ejemplo 2 de 7 → 29. */
export function porcentajeHitos(visitados: number): number {
  return Math.round((Math.min(visitados, HITOS.length) / HITOS.length) * 100)
}

/** "125" → "02:05" para el cronómetro de la exploración. */
export function cronometro(segundos: number): string {
  const s = Math.max(0, Math.floor(segundos))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

/** Escala los puntos de la ruta (x, y) a un cuadro de `ancho` × `alto` píxeles para el minimapa (RF-03.6). */
export function proyectarMinimapa(puntos: Punto[], ancho: number, alto: number, margen = 10): Punto[] {
  if (puntos.length === 0) return []
  const xs = puntos.map((p) => p.x)
  const ys = puntos.map((p) => p.y)
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
  const escala = Math.min((ancho - 2 * margen) / (maxX - minX || 1), (alto - 2 * margen) / (maxY - minY || 1))
  const offX = (ancho - (maxX - minX) * escala) / 2
  const offY = (alto - (maxY - minY) * escala) / 2
  // En la app la boca está arriba (y = 0) y el tubo baja: en pantalla, y crece hacia abajo.
  return puntos.map((p) => ({ x: offX + (p.x - minX) * escala, y: offY + (maxY - p.y) * escala, z: 0 }))
}

function redondear(v: number): number {
  return Math.round(v * 100) / 100
}

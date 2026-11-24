// Responsable: Cristian Cruz · Motor 3D del endoscopio virtual (RF-03.1 a RF-03.5, RNF-01, RNF-02)
// three.js puro, sin React: carga el modelo de Blender, mueve la cámara por la ruta de
// los hitos y avisa por el bus (Observer) cuando pasa por un hito o captura el hallazgo.
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

import { BusEscena } from './bus'
import {
  datosCaptura,
  evaluarVisibilidad,
  hitosNuevos,
  moverAvance,
  RUTA,
  type Hito,
  type Punto,
  type Visibilidad,
} from './ruta'

export const URL_MODELO = '/modelos/tracto_superior.glb'

/** Velocidades del endoscopio. */
const AVANCE_CM_S = 4 // W / S
const GIRO_GRADOS_S = 70 // A / D y Q / E
const MOUSE_GRADOS_PX = 0.25 // arrastrar con el mouse
const INCLINACION_MAX = 80 // grados hacia arriba o abajo
const ARRIBA = new THREE.Vector3(0, 0, 1) // la ruta está en el plano XY: Z sirve de "arriba" estable

export interface ObjetivoHallazgo {
  hito: string
  x: number
  y: number
  z: number
  radio_visibilidad: number
  /** RF-03.4: un hallazgo normal no muestra lesión, pero la zona se puede capturar igual. */
  lesion_visible?: boolean
}

export interface EstadoEscena {
  avance: number
  posicion: Punto
  visibilidad: Visibilidad
  segundos: number
}

export class MotorEscena {
  readonly bus = new BusEscena()
  private readonly renderer: THREE.WebGLRenderer
  private readonly escena = new THREE.Scene()
  private readonly camara = new THREE.PerspectiveCamera(70, 1, 0.05, 80)
  private readonly reloj = new THREE.Clock()
  private ruta: THREE.CatmullRomCurve3 | null = null
  private largoRuta = 1
  private posiciones: Partial<Record<Hito, Punto>> = {}
  private readonly visitados = new Set<string>()
  private marcador: THREE.Mesh | null = null
  private puntoHallazgo = new THREE.Vector3()
  private teclas = new Set<string>()
  private avance = 0
  private giro = 0 // A / D y mouse (grados)
  private inclinacion = 0 // mouse (grados)
  private rotacion = 0 // Q / E (grados)
  private boton: -1 | 0 | 1 = 0 // botones en pantalla (táctil)
  private segundos = 0
  private pausado = false
  private cuadro = 0
  private sucio = true
  private visibilidad: Visibilidad = { enVista: false, distancia: Infinity, angulo: 180 }
  private observador: ResizeObserver | null = null
  private arrastre: { x: number; y: number } | null = null

  private readonly contenedor: HTMLElement
  private readonly hallazgo: ObjetivoHallazgo
  private readonly alCambiar: (estado: EstadoEscena) => void

  constructor(contenedor: HTMLElement, hallazgo: ObjetivoHallazgo, alCambiar: (estado: EstadoEscena) => void) {
    this.contenedor = contenedor
    this.hallazgo = hallazgo
    this.alCambiar = alCambiar
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
    // RNF-01: en pantallas de alta densidad no pasar de 2× (más píxeles = menos fluidez).
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.domElement.setAttribute('aria-hidden', 'true')
    contenedor.appendChild(this.renderer.domElement)

    this.escena.background = new THREE.Color(0x050202)
    this.escena.fog = new THREE.FogExp2(0x050202, 0.05) // la luz del endoscopio no llega lejos
    // Luz del endoscopio: sale de la punta (va pegada a la cámara).
    const luz = new THREE.PointLight(0xfff4e8, 6, 0, 1.5)
    this.camara.add(luz)
    this.escena.add(this.camara)
    this.escena.add(new THREE.HemisphereLight(0xffe0dc, 0x220808, 0.25))

    this.observador = new ResizeObserver(() => this.ajustarTamano())
    this.observador.observe(contenedor)
    this.ajustarTamano()
    this.conectarEntradas()
  }

  /** RNF-02: carga el .glb y avisa del progreso (0 a 1). */
  async cargar(url: string = URL_MODELO, progreso?: (fraccion: number) => void): Promise<void> {
    const gltf = await new GLTFLoader().loadAsync(url, (e) => {
      if (e.total > 0) progreso?.(e.loaded / e.total)
    })
    this.escena.add(gltf.scene)
    gltf.scene.updateMatrixWorld(true)

    // Los hitos son objetos vacíos con nombre dentro del modelo de Cristian.
    const puntos: THREE.Vector3[] = []
    for (const nombre of RUTA) {
      const objeto = gltf.scene.getObjectByName(nombre)
      if (!objeto) throw new Error(`El modelo 3D no tiene el hito "${nombre}"`)
      const p = objeto.getWorldPosition(new THREE.Vector3())
      puntos.push(p)
      if (nombre !== 'camara_inicio') this.posiciones[nombre] = { x: p.x, y: p.y, z: p.z }
    }
    this.ruta = new THREE.CatmullRomCurve3(puntos, false, 'centripetal')
    this.largoRuta = this.ruta.getLength()

    const malla = gltf.scene.getObjectByName('tracto_superior')
    if (!(malla instanceof THREE.Mesh)) throw new Error('El modelo 3D no tiene la malla "tracto_superior"')
    this.ponerMarcador(malla)
    this.reloj.start()
    this.animar()
  }

  /** Puntos de la ruta para dibujar el minimapa. */
  puntosRuta(cantidad = 80): Punto[] {
    if (!this.ruta) return []
    return this.ruta.getSpacedPoints(cantidad).map((p) => ({ x: p.x, y: p.y, z: p.z }))
  }

  posicionesHitos(): Partial<Record<Hito, Punto>> {
    return { ...this.posiciones }
  }

  /** Hitos ya visitados en un intento anterior (al recargar la página). */
  marcarVisitados(hitos: string[]): void {
    for (const h of hitos) this.visitados.add(h)
  }

  /** Botones en pantalla para celulares y tabletas: 1 avanza, −1 retrocede, 0 se detiene. */
  moverConBoton(sentido: -1 | 0 | 1): void {
    this.boton = sentido
  }

  /** RF-03.5: intenta capturar. Emite hallazgo_capturado o captura_invalida. */
  capturar(): boolean {
    if (this.visibilidad.enVista) {
      this.bus.emitir('hallazgo_capturado', datosCaptura(this.visibilidad, this.hallazgo.hito, this.segundos))
      return true
    }
    this.bus.emitir('captura_invalida', {
      distancia: Math.round(Math.min(this.visibilidad.distancia, 999) * 100) / 100,
      angulo: Math.round(this.visibilidad.angulo),
    })
    return false
  }

  omitir(): void {
    this.bus.emitir('hallazgo_omitido', { segundos: Math.round(this.segundos) })
  }

  /** La pestaña se ocultó o volvió (RF-12: pausa / reanudación). */
  pausar(pausa: boolean): void {
    if (pausa === this.pausado) return
    this.pausado = pausa
    this.teclas.clear()
    this.bus.emitir(pausa ? 'pausa' : 'reanudacion', {})
    this.reloj.getDelta() // no contar el tiempo en pausa
    this.sucio = true // al volver, redibujar aunque no se haya movido
  }

  /** Lleva el endoscopio a un punto de la ruta (0 = boca, 1 = duodeno) y orienta la punta. Útil en la demo. */
  irA(avance: number, giro = 0, inclinacion = 0): void {
    this.avance = moverAvance(0, avance)
    this.giro = giro
    this.inclinacion = THREE.MathUtils.clamp(inclinacion, -INCLINACION_MAX, INCLINACION_MAX)
    this.sucio = true
  }

  destruir(): void {
    cancelAnimationFrame(this.cuadro)
    this.observador?.disconnect()
    this.desconectarEntradas()
    this.escena.traverse((o) => {
      if (o instanceof THREE.Mesh) {
        o.geometry.dispose()
        for (const m of [o.material].flat()) {
          for (const valor of Object.values(m)) if (valor instanceof THREE.Texture) valor.dispose()
          m.dispose()
        }
      }
    })
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }

  // ---------- Interno ----------

  /** El hallazgo se pinta en la pared más cercana al punto del caso (misma apariencia para todas las clases). */
  private ponerMarcador(malla: THREE.Mesh): void {
    const centro = new THREE.Vector3(this.hallazgo.x, this.hallazgo.y, this.hallazgo.z)
    const rayo = new THREE.Raycaster()
    let mejor: THREE.Intersection | null = null
    // 26 direcciones alrededor del punto: se queda con la pared más cercana.
    for (const dx of [-1, 0, 1]) {
      for (const dy of [-1, 0, 1]) {
        for (const dz of [-1, 0, 1]) {
          if (dx === 0 && dy === 0 && dz === 0) continue
          rayo.set(centro, new THREE.Vector3(dx, dy, dz).normalize())
          const choque = rayo.intersectObject(malla, false)[0]
          if (choque && (!mejor || choque.distance < mejor.distance)) mejor = choque
        }
      }
    }
    const normal = mejor?.face ? mejor.face.normal.clone().transformDirection(malla.matrixWorld) : new THREE.Vector3(0, 0, 1)
    // La normal debe mirar hacia adentro del tubo (hacia el punto del caso).
    const punto = mejor ? mejor.point.clone() : centro.clone()
    if (normal.dot(centro.clone().sub(punto)) < 0) normal.negate()

    this.marcador = new THREE.Mesh(
      geometriaLesion(),
      new THREE.MeshStandardMaterial({
        color: 0xb8322c,
        emissive: 0x3a0806,
        roughness: 0.55,
        transparent: true,
        opacity: 0.92,
        polygonOffset: true,
        polygonOffsetFactor: -2,
        side: THREE.DoubleSide,
      }),
    )
    this.marcador.name = 'hallazgo'
    this.marcador.visible = this.hallazgo.lesion_visible !== false
    this.marcador.position.copy(punto).addScaledVector(normal, 0.03)
    this.marcador.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal)
    this.escena.add(this.marcador)
    this.puntoHallazgo = this.marcador.position.clone()
  }

  private animar = (): void => {
    this.cuadro = requestAnimationFrame(this.animar)
    const dt = Math.min(this.reloj.getDelta(), 0.1)
    if (this.pausado || !this.ruta) return
    this.segundos += dt

    const adelante = (this.teclas.has('w') || this.teclas.has('arrowup') ? 1 : 0) - (this.teclas.has('s') || this.teclas.has('arrowdown') ? 1 : 0) + this.boton
    const girar = (this.teclas.has('a') || this.teclas.has('arrowleft') ? 1 : 0) - (this.teclas.has('d') || this.teclas.has('arrowright') ? 1 : 0)
    const rotar = (this.teclas.has('q') ? 1 : 0) - (this.teclas.has('e') ? 1 : 0)
    if (adelante !== 0) this.avance = moverAvance(this.avance, (Math.sign(adelante) * AVANCE_CM_S * dt) / this.largoRuta)
    if (girar !== 0) this.giro += girar * GIRO_GRADOS_S * dt
    if (rotar !== 0) this.rotacion += rotar * GIRO_GRADOS_S * dt
    if (adelante !== 0 || girar !== 0 || rotar !== 0) this.sucio = true

    // RNF-01: si nada se movió, no se vuelve a dibujar (ahorra batería y GPU).
    if (!this.sucio) return
    this.sucio = false
    this.ubicarCamara()
    this.renderer.render(this.escena, this.camara)
    this.revisar()
  }

  private ubicarCamara(): void {
    const ruta = this.ruta!
    const pos = ruta.getPointAt(this.avance)
    const tangente = ruta.getTangentAt(this.avance)
    const base = new THREE.Matrix4().lookAt(pos, pos.clone().add(tangente), ARRIBA)
    const q = new THREE.Quaternion().setFromRotationMatrix(base)
    const euler = new THREE.Euler(
      THREE.MathUtils.degToRad(this.inclinacion),
      THREE.MathUtils.degToRad(this.giro),
      THREE.MathUtils.degToRad(this.rotacion),
      'YXZ',
    )
    this.camara.position.copy(pos)
    this.camara.quaternion.copy(q).multiply(new THREE.Quaternion().setFromEuler(euler))
  }

  private revisar(): void {
    const p = this.camara.position
    const posicion = { x: p.x, y: p.y, z: p.z }
    for (const hito of hitosNuevos(posicion, this.posiciones, this.visitados)) {
      this.visitados.add(hito)
      this.bus.emitir('hito_visitado', { hito })
    }
    const mirada = this.camara.getWorldDirection(new THREE.Vector3())
    this.visibilidad = evaluarVisibilidad(
      posicion,
      { x: mirada.x, y: mirada.y, z: mirada.z },
      { x: this.puntoHallazgo.x, y: this.puntoHallazgo.y, z: this.puntoHallazgo.z },
      this.hallazgo.radio_visibilidad,
    )
    this.alCambiar({ avance: this.avance, posicion, visibilidad: this.visibilidad, segundos: this.segundos })
  }

  private ajustarTamano(): void {
    const { clientWidth: ancho, clientHeight: alto } = this.contenedor
    if (ancho === 0 || alto === 0) return
    this.renderer.setSize(ancho, alto, false)
    this.camara.aspect = ancho / alto
    this.camara.updateProjectionMatrix()
    this.sucio = true
  }

  // ---------- Teclado y mouse (W/S avanzar · A/D girar · mouse orientar · Q/E rotar) ----------
  private readonly teclaAbajo = (e: KeyboardEvent): void => {
    const k = e.key.toLowerCase()
    if (['w', 's', 'a', 'd', 'q', 'e', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(k)) {
      e.preventDefault()
      this.teclas.add(k)
    }
  }
  private readonly teclaArriba = (e: KeyboardEvent): void => {
    this.teclas.delete(e.key.toLowerCase())
  }
  private readonly desenfoque = (): void => this.teclas.clear()
  private readonly punteroAbajo = (e: PointerEvent): void => {
    this.arrastre = { x: e.clientX, y: e.clientY }
    this.contenedor.setPointerCapture?.(e.pointerId)
    this.contenedor.focus()
  }
  private readonly punteroMovido = (e: PointerEvent): void => {
    if (!this.arrastre) return
    this.giro -= (e.clientX - this.arrastre.x) * MOUSE_GRADOS_PX
    this.inclinacion = THREE.MathUtils.clamp(
      this.inclinacion - (e.clientY - this.arrastre.y) * MOUSE_GRADOS_PX,
      -INCLINACION_MAX,
      INCLINACION_MAX,
    )
    this.arrastre = { x: e.clientX, y: e.clientY }
    this.sucio = true
  }
  private readonly punteroArriba = (): void => {
    this.arrastre = null
  }

  private conectarEntradas(): void {
    this.contenedor.addEventListener('keydown', this.teclaAbajo)
    this.contenedor.addEventListener('keyup', this.teclaArriba)
    this.contenedor.addEventListener('blur', this.desenfoque)
    this.contenedor.addEventListener('pointerdown', this.punteroAbajo)
    this.contenedor.addEventListener('pointermove', this.punteroMovido)
    this.contenedor.addEventListener('pointerup', this.punteroArriba)
    this.contenedor.addEventListener('pointercancel', this.punteroArriba)
  }

  private desconectarEntradas(): void {
    this.contenedor.removeEventListener('keydown', this.teclaAbajo)
    this.contenedor.removeEventListener('keyup', this.teclaArriba)
    this.contenedor.removeEventListener('blur', this.desenfoque)
    this.contenedor.removeEventListener('pointerdown', this.punteroAbajo)
    this.contenedor.removeEventListener('pointermove', this.punteroMovido)
    this.contenedor.removeEventListener('pointerup', this.punteroArriba)
    this.contenedor.removeEventListener('pointercancel', this.punteroArriba)
  }
}

/** Mancha irregular de ~0,9 cm: borde ondulado para que no parezca un círculo perfecto. */
function geometriaLesion(): THREE.ShapeGeometry {
  const forma = new THREE.Shape()
  const lados = 28
  for (let i = 0; i <= lados; i++) {
    const a = (i / lados) * Math.PI * 2
    const r = 0.45 * (1 + 0.18 * Math.sin(3 * a) + 0.1 * Math.cos(5 * a + 1))
    if (i === 0) forma.moveTo(r * Math.cos(a), r * Math.sin(a))
    else forma.lineTo(r * Math.cos(a), r * Math.sin(a))
  }
  return new THREE.ShapeGeometry(forma)
}


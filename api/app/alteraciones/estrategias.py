"""
Alteraciones de la recomendación de la IA: patrón Strategy (informe de diseño, figura P1).
Responsable: Emmanuel Ospina · Actividades 4404 y 4405 (RF-08.1, RF-08.2).

Para estudiar la sobre-dependencia en la IA, un porcentaje de las
recomendaciones se altera a propósito. Cada tipo de alteración es una
estrategia intercambiable; la fábrica la crea por su nombre y el servicio
decide, con la semilla del intento, si se altera y cómo (reproducible).

Python puro: sin SQL, sin HTTP. Se prueba sin base de datos.
"""
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace

TIPOS = ("clase_incorrecta", "confianza_alterada", "roi_desplazada")
# Si el docente aún no ha configurado nada: 1 de cada 4 recomendaciones, de cualquier tipo.
PORCENTAJE_POR_DEFECTO = 25.0
PORCENTAJE_MAXIMO = 50.0  # igual que el check de config_alteracion


@dataclass(frozen=True)
class Roi:
    """Región de interés en coordenadas normalizadas (0 a 1) sobre la imagen."""

    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class Clase:
    id: int
    codigo: str
    nombre: str
    region: str


@dataclass(frozen=True)
class Recomendacion:
    """Lo que la IA de visión le sugiere al estudiante (RF-06)."""

    clase_id: int
    clase: str
    nombre: str
    confianza: float  # 0 a 1
    roi: Roi
    modelo: str

    def como_json(self) -> dict:
        # clase_id lo usa la vista mv_desempeno para medir la sobre-dependencia.
        return {
            "clase_id": self.clase_id, "clase": self.clase, "nombre": self.nombre,
            "confianza": self.confianza, "modelo": self.modelo,
            "roi": {"x": self.roi.x, "y": self.roi.y, "w": self.roi.w, "h": self.roi.h},
        }


@dataclass(frozen=True)
class ConfigAlteracion:
    id: int | None  # None = valores por defecto (nadie ha configurado)
    porcentaje: float
    tipos: tuple[str, ...]


CONFIG_POR_DEFECTO = ConfigAlteracion(id=None, porcentaje=PORCENTAJE_POR_DEFECTO, tipos=TIPOS)


@dataclass(frozen=True)
class Decision:
    recomendacion: Recomendacion  # la que verá el estudiante
    alterada: bool
    tipo: str | None


# ---------- Strategy ----------

class EstrategiaAlteracion(ABC):
    tipo = "ninguna"

    @abstractmethod
    def aplicar(self, rec: Recomendacion, clases: list[Clase], azar: random.Random) -> Recomendacion: ...


class SinAlteracion(EstrategiaAlteracion):
    def aplicar(self, rec, clases, azar):
        return rec


class ClaseIncorrecta(EstrategiaAlteracion):
    """Sugiere otra clase de la misma región, con la misma seguridad: el error más peligroso."""

    tipo = "clase_incorrecta"

    def aplicar(self, rec, clases, azar):
        region = next((c.region for c in clases if c.id == rec.clase_id), None)
        otras = [c for c in clases if c.id != rec.clase_id and c.region == region]
        otras = otras or [c for c in clases if c.id != rec.clase_id]
        if not otras:
            return rec
        nueva = azar.choice(sorted(otras, key=lambda c: c.id))
        return replace(rec, clase_id=nueva.id, clase=nueva.codigo, nombre=nueva.nombre)


class ConfianzaAlterada(EstrategiaAlteracion):
    """Clase correcta, pero con una confianza engañosa: alta se vuelve baja y viceversa."""

    tipo = "confianza_alterada"

    def aplicar(self, rec, clases, azar):
        nueva = azar.uniform(0.30, 0.55) if rec.confianza >= 0.6 else azar.uniform(0.86, 0.97)
        return replace(rec, confianza=round(nueva, 2))


class RoiDesplazada(EstrategiaAlteracion):
    """Clase correcta, pero el recuadro señala otra zona de la imagen."""

    tipo = "roi_desplazada"

    def aplicar(self, rec, clases, azar):
        r = rec.roi
        cx, cy = r.x + r.w / 2, r.y + r.h / 2
        # Las 4 esquinas posibles; se elige una lejos del recuadro original.
        esquinas = [(0.05, 0.05), (0.95 - r.w, 0.05), (0.05, 0.95 - r.h), (0.95 - r.w, 0.95 - r.h)]
        lejanas = [(x, y) for x, y in esquinas if abs(x + r.w / 2 - cx) + abs(y + r.h / 2 - cy) >= 0.35]
        x, y = azar.choice(lejanas or esquinas)
        return replace(rec, roi=Roi(round(max(0.0, x), 3), round(max(0.0, y), 3), r.w, r.h))


class FabricaAlteraciones:
    """Crea la estrategia por su nombre. Agregar un tipo nuevo = registrar una clase aquí."""

    def __init__(self) -> None:
        self._registro: dict[str, type[EstrategiaAlteracion]] = {
            "ninguna": SinAlteracion,
            ClaseIncorrecta.tipo: ClaseIncorrecta,
            ConfianzaAlterada.tipo: ConfianzaAlterada,
            RoiDesplazada.tipo: RoiDesplazada,
        }

    def crear(self, tipo: str) -> EstrategiaAlteracion:
        if tipo not in self._registro:
            raise ValueError(f"Tipo de alteración desconocido: {tipo}")
        return self._registro[tipo]()


class ServicioAlteraciones:
    """Decide si la recomendación se altera y cómo (RF-08.2).

    forzar: solo para pruebas automáticas (obliga un tipo concreto).
    """

    def __init__(self, fabrica: FabricaAlteraciones | None = None, forzar: str | None = None):
        self._fabrica = fabrica or FabricaAlteraciones()
        self._forzar = forzar

    def decidir(self, original: Recomendacion, config: ConfigAlteracion, clases: list[Clase],
                semilla: int) -> Decision:
        azar = random.Random(semilla)  # misma semilla = misma decisión (reproducible)
        if self._forzar:
            tipo = self._forzar
        elif config.tipos and azar.random() * 100 < config.porcentaje:
            tipo = azar.choice(sorted(config.tipos))
        else:
            return Decision(original, alterada=False, tipo=None)
        if tipo == "ninguna":
            return Decision(original, alterada=False, tipo=None)
        nueva = self._fabrica.crear(tipo).aplicar(original, clases, azar)
        return Decision(nueva, alterada=nueva != original, tipo=tipo if nueva != original else None)

"""
Estados del intento: patrón State (informe de diseño, figuras P6 y SW6).
Responsable: Diego Agudelo · Actividades 4501 y 4502 (RF-05, RF-09).

Cada estado sabe qué acciones permite. Si el estudiante intenta algo fuera
de orden (pedir el tutor antes de decidir, decidir dos veces...), el estado
lanza TransicionInvalida y la API responde 409.

Fase 5: el estudiante recorre la escena 3D y captura el hallazgo (pasa a
"hallazgo_capturado"). Si no lo encuentra, puede decidir con la imagen desde
"explorando"; la telemetría guarda que lo omitió (hallazgo_omitido).
"""
from abc import ABC


# Los 7 hitos anatómicos, en el orden del recorrido (iguales a hito_anatomico y al modelo 3D).
HITOS = ("linea_z", "cardias", "fondo", "cuerpo", "antro", "piloro", "bulbo")


class TransicionInvalida(Exception):
    """Acción no permitida en el estado actual del intento."""


class EstadoIntento(ABC):
    nombre = ""
    abierto = True  # admite eventos de telemetría

    def registrar_evento(self, tipo: str) -> str:
        if not self.abierto:
            raise TransicionInvalida("El intento ya terminó")
        return self.nombre

    def registrar_decision_inicial(self) -> str:
        raise TransicionInvalida("La decisión inicial ya fue registrada")

    def consultar_tutor(self) -> None:
        raise TransicionInvalida("El tutor se habilita después de tu decisión inicial")

    def registrar_decision_final(self) -> str:
        raise TransicionInvalida("Primero registra tu decisión inicial")


class Explorando(EstadoIntento):
    nombre = "explorando"

    def registrar_evento(self, tipo: str) -> str:
        return "hallazgo_capturado" if tipo == "hallazgo_capturado" else self.nombre

    def registrar_decision_inicial(self) -> str:
        return "recomendacion"


class HallazgoCapturado(Explorando):
    nombre = "hallazgo_capturado"

    def registrar_evento(self, tipo: str) -> str:
        return self.nombre


class DecisionInicial(HallazgoCapturado):
    nombre = "decision_inicial"


class Recomendacion(EstadoIntento):
    """Solo aquí se ve la recomendación de la IA y se habla con el tutor (RF-07)."""

    nombre = "recomendacion"

    def consultar_tutor(self) -> None:
        return None

    def registrar_decision_final(self) -> str:
        return "finalizado"


class Finalizado(EstadoIntento):
    nombre = "finalizado"
    abierto = False

    def registrar_decision_inicial(self) -> str:
        raise TransicionInvalida("El intento ya terminó")

    def consultar_tutor(self) -> None:
        raise TransicionInvalida("El intento ya terminó")

    def registrar_decision_final(self) -> str:
        raise TransicionInvalida("El intento ya terminó")


class Abandonado(Finalizado):
    nombre = "abandonado"


ESTADOS: dict[str, EstadoIntento] = {
    e.nombre: e() for e in (Explorando, HallazgoCapturado, DecisionInicial, Recomendacion, Finalizado, Abandonado)
}


def estado(nombre: str) -> EstadoIntento:
    return ESTADOS[nombre]

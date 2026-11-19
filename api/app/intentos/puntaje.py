"""
Puntaje, niveles e insignias (RF-10 y RF-11).
Responsable: Jahan Michelle Chará · Actividades 4503 y 4504.

Python puro: sin SQL ni HTTP. Se prueba con números a mano.

Cómo se calcula el puntaje de un caso:
  - 100 puntos si la decisión final es correcta.
  -  50 puntos extra si la IA sugirió una clase equivocada a propósito
     y el estudiante NO la siguió (detectó el error de la IA).
  - Calibración: la confianza debe acompañar al acierto.
      acierto:  confianza × 5    (1 → 5 puntos ... 5 → 25 puntos)
      error:    (5 − confianza) × 5  (reconocer la duda vale: 1 → 20 ... 5 → 0)
Nunca es negativo. Cada 500 puntos acumulados se sube un nivel (máximo 10).
"""
from dataclasses import dataclass

PUNTOS_ACIERTO = 100
BONO_DETECCION = 50
PUNTOS_POR_CONFIANZA = 5
PUNTOS_POR_NIVEL = 500
NIVEL_MAXIMO = 10


@dataclass(frozen=True)
class Puntaje:
    acierto: int
    deteccion: int
    calibracion: int

    @property
    def total(self) -> int:
        return self.acierto + self.deteccion + self.calibracion

    def como_json(self) -> dict:
        return {"acierto": self.acierto, "deteccion": self.deteccion, "calibracion": self.calibracion,
                "total": self.total}


def _validar_confianza(confianza: int) -> None:
    if not 1 <= confianza <= 5:
        raise ValueError("La confianza va de 1 a 5")


def calcular_puntaje(acierto_usuario: bool, confianza_final: int, detecto_error_ia: bool) -> Puntaje:
    """RF-10: puntaje de un intento."""
    _validar_confianza(confianza_final)
    if acierto_usuario:
        calibracion = confianza_final * PUNTOS_POR_CONFIANZA
    else:
        calibracion = (5 - confianza_final) * PUNTOS_POR_CONFIANZA
    return Puntaje(
        acierto=PUNTOS_ACIERTO if acierto_usuario else 0,
        deteccion=BONO_DETECCION if (detecto_error_ia and acierto_usuario) else 0,
        calibracion=calibracion,
    )


def esta_calibrado(acierto_usuario: bool, confianza_final: int) -> bool:
    """Seguro y acertó (4–5), o dudoso y falló (1–2). La confianza 3 nunca cuenta."""
    _validar_confianza(confianza_final)
    return (acierto_usuario and confianza_final >= 4) or (not acierto_usuario and confianza_final <= 2)


def racha_final(calibraciones: list[bool]) -> int:
    """Cuántos intentos seguidos, contando desde el último, estuvieron calibrados."""
    racha = 0
    for calibrado in reversed(calibraciones):
        if not calibrado:
            break
        racha += 1
    return racha


def nivel_para(puntos: int) -> int:
    """RF-11: nivel 1 con 0–499 puntos, nivel 2 con 500–999, ... hasta 10."""
    return min(NIVEL_MAXIMO, 1 + max(0, puntos) // PUNTOS_POR_NIVEL)


def insignias_ganadas(estadisticas: dict[str, int], criterios: dict[str, dict],
                      ya_tiene: set[str]) -> list[str]:
    """RF-11: insignias nuevas.

    criterios viene de la tabla insignia, por ejemplo {"detector": {"errores_ia_detectados": 10}}.
    Se gana cuando TODAS las estadísticas pedidas alcanzan su umbral.
    """
    nuevas = []
    for codigo, criterio in sorted(criterios.items()):
        if codigo in ya_tiene or not criterio:
            continue
        if all(estadisticas.get(clave, 0) >= umbral for clave, umbral in criterio.items()):
            nuevas.append(codigo)
    return nuevas

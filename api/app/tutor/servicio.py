"""
Servicio del tutor: conversa con Gemini y responde con la guía local si falla.
Responsable: Emmanuel Ospina · Actividades 4401, 4403 y 4407 (RF-07.1, RF-07.3, RNF-03).

Flujo:
  1. Si hay modelo, se le pregunta (con reintentos y respaldo: Decorator de llm.py).
  2. La respuesta pasa por el guardián. Si no pasa, se pide una vez más.
  3. Si no hay modelo, no responde a tiempo o el guardián rechaza dos veces,
     se responde con la guía local (W13 "tutor no disponible"): el estudiante
     nunca se queda sin ayuda.
"""
import random
import time
from dataclasses import dataclass

from ..llm import LLMNoDisponible, ReintentoConRespaldo
from . import guardian
from .prompts import ESQUEMA_RESPUESTA, INSTRUCCIONES, ContextoTutor, construir_entrada

MODELO_LOCAL = "guia-local-v1"
MAX_INTENTOS_MODELO = 2


@dataclass(frozen=True)
class RespuestaTutor:
    texto: str
    modelo: str
    es_respaldo: bool
    latencia_ms: int


class GuiaLocal:
    """Pistas socráticas fijas. No dependen de internet y nunca revelan nada."""

    PISTAS = {
        "ia": (
            "¿Qué tan alta es la confianza que muestra la IA? ¿El recuadro señala la misma zona que tú "
            "observas? Una IA también se equivoca: contrasta su sugerencia con lo que ves y con la historia.",
            "Piensa qué te haría desconfiar de la recomendación: ¿coincide con los síntomas del paciente? "
            "¿El recuadro marca algo que de verdad te parezca anormal?",
        ),
        "sintomas": (
            "Relaciona cada síntoma con la región explorada. ¿Cuáles apuntan a un problema crónico y cuáles "
            "podrían aparecer también en una mucosa sin lesiones?",
            "¿Cuánto tiempo llevan los síntomas y qué antecedentes los agravan? Eso ayuda a estimar qué tan "
            "probable es una lesión.",
        ),
        "imagen": (
            "Observa el color, la textura y los bordes de la mucosa. ¿Hay zonas de distinto color, "
            "erosiones o un límite irregular? ¿O todo se ve uniforme?",
            "Compara la zona que señala el recuadro con el resto de la imagen. ¿Qué la hace diferente, "
            "si es que lo es?",
        ),
        "general": (
            "Repasa tus opciones una por una: ¿qué esperarías ver en la imagen y en la historia si cada una "
            "fuera cierta? Descarta las que no encajen.",
            "Antes de decidir, pregúntate qué evidencia te haría cambiar de opinión. ¿La tienes delante?",
        ),
    }
    _CLAVES = {
        "ia": ("ia", "inteligencia", "recomend", "confianza", "recuadro", "modelo"),
        "sintomas": ("síntoma", "sintoma", "dolor", "ardor", "historia", "antecedente", "paciente"),
        "imagen": ("imagen", "mucosa", "color", "veo", "lesión", "lesion", "zona", "foto"),
    }

    def responder(self, pregunta: str, turno: int) -> str:
        p = pregunta.lower()
        tema = next((t for t, claves in self._CLAVES.items() if any(c in p for c in claves)), "general")
        return random.Random(turno).choice(self.PISTAS[tema])


class ServicioTutor:
    def __init__(self, llm: ReintentoConRespaldo | None, guia: GuiaLocal | None = None):
        self._llm = llm
        self._guia = guia or GuiaLocal()

    async def responder(self, ctx: ContextoTutor, historial: list[dict], pregunta: str,
                        semilla: int) -> RespuestaTutor:
        inicio = time.monotonic()
        if self._llm is not None:
            entrada = construir_entrada(ctx, historial, pregunta)
            for n in range(MAX_INTENTOS_MODELO):
                try:
                    datos, modelo = await self._llm.generar_con_modelo(
                        INSTRUCCIONES, entrada, ESQUEMA_RESPUESTA, semilla + n
                    )
                except LLMNoDisponible:
                    break
                texto = datos.get("respuesta") if isinstance(datos, dict) else None
                if guardian.revisar(texto) is None:
                    return RespuestaTutor(texto.strip(), modelo, False, self._ms(inicio))
        # RF-07.3: respaldo. El estudiante ve que es la guía básica (W13).
        texto = self._guia.responder(pregunta, len(historial))
        return RespuestaTutor(texto, MODELO_LOCAL, True, self._ms(inicio))

    @staticmethod
    def _ms(inicio: float) -> int:
        return int((time.monotonic() - inicio) * 1000)

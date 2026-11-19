"""
Guardián de las respuestas del tutor (RF-07.2, RNF-13).
Responsable: Emmanuel Ospina · Actividad 4402.

Aunque el tutor no conoce la respuesta, podría "adivinar" y afirmarla con
seguridad. Toda respuesta pasa por aquí antes de llegar al estudiante; si
no pasa, se pide otra o se usa la guía local.
"""
import re

LARGO_MAXIMO = 1200

# Frases que afirman un diagnóstico o confirman una opción.
_AFIRMACIONES = re.compile(
    r"\b(la respuesta (correcta )?es|el diagn[oó]stico (correcto |final )?es|se trata de|"
    r"corresponde a (un|una)|es claramente|definitivamente es|tienes raz[oó]n|est[aá]s en lo correcto|"
    r"la ia (tiene raz[oó]n|acierta|est[aá] en lo cierto)|la opci[oó]n correcta)\b",
    re.IGNORECASE,
)
_DATO_PERSONAL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\b\d{7,}\b")


def revisar(respuesta: object) -> str | None:
    """Devuelve el motivo del rechazo, o None si la respuesta se puede mostrar."""
    if not isinstance(respuesta, str) or not respuesta.strip():
        return "respuesta vacía"
    if len(respuesta) > LARGO_MAXIMO:
        return "respuesta demasiado larga"
    if _AFIRMACIONES.search(respuesta):
        return "afirma o confirma un diagnóstico"
    if _DATO_PERSONAL.search(respuesta):
        return "contiene algo que parece un dato personal"
    return None

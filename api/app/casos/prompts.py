"""
Instrucciones que recibe el modelo de lenguaje para redactar la historia.
Responsable: Emmanuel Ospina · Actividad 4206 (RF-14.2).

Cada caso guarda VERSION_PROMPT, modelo y semilla (RF-14.5): si cambian estas
instrucciones, se sube la versión para poder comparar resultados.
Solo viajan datos sintéticos (clase típica, dificultad); nunca datos de
usuarios (RNF-08).
"""
import json

from .dominio import PERFILES

VERSION_PROMPT = "historia-v1"

INSTRUCCIONES = """Eres un docente de gastroenterología que redacta casos clínicos SINTÉTICOS
para entrenar estudiantes de medicina en endoscopia digestiva alta.
Reglas obligatorias:
1. Escribe en español neutro, en tercera persona, entre 3 y 6 oraciones.
2. El paciente es ficticio: no inventes nombres, documentos, teléfonos, correos ni direcciones.
3. NUNCA menciones el diagnóstico ni lo que se verá en la endoscopia. No uses ninguna de las
   palabras de la lista "prohibido_mencionar".
4. Usa los síntomas y antecedentes sugeridos como base; puedes reformularlos.
5. Dificultad "basico": síntomas típicos y claros. "intermedio": mezcla síntomas típicos con
   uno inespecífico. "avanzado": síntomas leves o inespecíficos que no orienten fácil.
6. Termina indicando que se solicita endoscopia digestiva alta.
7. Responde SOLO con el JSON pedido. "sexo" debe ser "femenino" o "masculino"."""

# Esquema de respuesta (formato OpenAPI que entiende Gemini): obliga a que la
# respuesta tenga exactamente estos campos.
ESQUEMA_HISTORIA = {
    "type": "OBJECT",
    "properties": {
        "edad": {"type": "INTEGER"},
        "sexo": {"type": "STRING", "enum": ["femenino", "masculino"]},
        "motivo": {"type": "STRING"},
        "antecedentes": {"type": "ARRAY", "items": {"type": "STRING"}},
        "sintomas": {"type": "ARRAY", "items": {"type": "STRING"}},
        "texto": {"type": "STRING"},
    },
    "required": ["edad", "sexo", "motivo", "antecedentes", "sintomas", "texto"],
}


def construir_entrada(clase: str, dificultad: str) -> str:
    """Datos del caso que se envían al modelo. La clase no se nombra: solo su perfil."""
    p = PERFILES[clase]
    datos = {
        "dificultad": dificultad,
        "rango_edad": list(p.rango_edad),
        "motivo_tipico": p.motivo,
        "sintomas_tipicos": list(p.sintomas),
        "antecedentes_tipicos": list(p.antecedentes),
        "prohibido_mencionar": list(p.revela),
    }
    return "Redacta la historia clínica del caso.\nDATOS:" + json.dumps(datos, ensure_ascii=False)

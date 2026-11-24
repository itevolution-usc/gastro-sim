"""
Exportación a CSV de los intentos para la investigación (W19, RF-15).
Responsable: Jahan Michelle Chará · Actividad 4507.

Función pura (sin base de datos): recibe las filas y devuelve el texto del CSV.
Privacidad (RNF-08): el participante va solo por su seudónimo; no hay columnas
de nombre, correo ni id de cuenta. Ningún campo es texto libre del usuario.
"""
import csv
import io
from datetime import date

COLUMNAS = (
    "participante", "caso_id", "dificultad", "referencia", "alterada", "tipo_alteracion",
    "decision_inicial", "confianza_inicial", "decision_final", "confianza_final", "cambio_decision",
    "acierto_usuario", "acierto_ia", "puntaje", "duracion_s", "hitos_visitados", "mensajes_tutor", "fecha",
)


def _valor(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"  # 1/0: se suma o promedia directo en Excel, R o Python
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def a_csv(filas: list[dict]) -> str:
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS)
    for fila in filas:
        escritor.writerow([_valor(fila.get(c)) for c in COLUMNAS])
    return salida.getvalue()


def nombre_archivo(hoy: date) -> str:
    return f"gastro-sim-intentos-{hoy.isoformat()}.csv"

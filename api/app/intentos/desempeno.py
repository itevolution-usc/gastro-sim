"""
Métricas del tablero de desempeño del estudiante (W16, RF-13).
Responsable: Jahan Michelle Chará · Actividad 4506.

Función pura (sin base de datos): recibe los intentos terminados y devuelve
las métricas. Solo cuenta intentos finalizados.

  precision          aciertos / intentos
  errores_ia         casos donde la recomendación mostrada NO era la respuesta
                     (alteración "clase incorrecta" o error real del modelo)
  deteccion          de esos casos, en cuántos la decisión final NO siguió a la IA
  sobredependencia   de esos casos en que el estudiante empezó con otra respuesta,
                     en cuántos se cambió a la de la IA equivocada
  calibracion        1 − Brier: qué tanto coincide la confianza (1 a 5 → 20 % a 100 %)
                     con acertar o no. 1 es perfecto; responder siempre con confianza 3
                     y acertar la mitad de las veces da 0,74
"""
from collections import defaultdict
from datetime import datetime, timedelta


def _razon(parte: int, total: int) -> float | None:
    return None if total == 0 else round(parte / total, 2)


def etiqueta_calibracion(valor: float | None) -> str | None:
    if valor is None:
        return None
    if valor >= 0.8:
        return "buena"
    if valor >= 0.65:
        return "regular"
    return "por mejorar"


def _lunes(fecha: datetime) -> str:
    return (fecha.date() - timedelta(days=fecha.weekday())).isoformat()


def _resumen(filas: list[dict]) -> dict:
    errores = [f for f in filas if f["recomendada"] != f["referencia"]]
    detectados = sum(1 for f in errores if f["final"] != f["recomendada"])
    discrepaban = [f for f in errores if f["inicial"] != f["recomendada"]]
    cambiaron = sum(1 for f in discrepaban if f["final"] == f["recomendada"])
    return {
        "intentos": len(filas),
        "aciertos": sum(1 for f in filas if f["acierto"]),
        "errores_ia": len(errores),
        "errores_ia_detectados": detectados,
        "siguio_ia_errada": cambiaron,
        "precision": _razon(sum(1 for f in filas if f["acierto"]), len(filas)),
        "deteccion": _razon(detectados, len(errores)),
        "sobredependencia": _razon(cambiaron, len(discrepaban)),
    }


def calcular(filas: list[dict]) -> dict:
    """filas: acierto, confianza (1-5), inicial, final, recomendada, referencia (ids de clase) y finalizado_en."""
    resumen = _resumen(filas)
    if filas:
        brier = sum((f["confianza"] / 5 - (1 if f["acierto"] else 0)) ** 2 for f in filas) / len(filas)
        resumen["calibracion"] = round(1 - brier, 2)
    else:
        resumen["calibracion"] = None
    resumen["calibracion_etiqueta"] = etiqueta_calibracion(resumen["calibracion"])
    semanas = defaultdict(list)
    for f in filas:
        semanas[_lunes(f["finalizado_en"])].append(f)
    resumen["por_semana"] = [
        {"semana": s, "intentos": len(fs), "precision": _resumen(fs)["precision"], "deteccion": _resumen(fs)["deteccion"]}
        for s, fs in sorted(semanas.items())
    ]
    return resumen

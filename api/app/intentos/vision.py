"""
Recomendación de la IA de visión (RF-06.1 y RF-06.2).
Responsable: Diego Agudelo · Actividades 4301, 4302 y 4304.

La tabla prediccion guarda las predicciones precalculadas del modelo de
visión (RF-06.3). Mientras el modelo se entrena (actividad 4304), se usa una
IA SIMULADA: sugiere la clase correcta con una confianza y un recuadro
verosímiles, calculados a partir de la huella sha256 de la imagen (siempre
los mismos para la misma imagen). Los errores de la IA vienen solo de las
alteraciones controladas (RF-08), que es lo que estudia la investigación.

Cuando exista el modelo real, basta con llenar la tabla prediccion: este
código la usará automáticamente.
"""
import random

from ..alteraciones.estrategias import Clase, Recomendacion, Roi

VERSION_SIMULADA = "simulada-v0"


def recomendacion_original(prediccion: dict | None, sha256: str, referencia: Clase,
                           clases: dict[int, Clase]) -> Recomendacion:
    if prediccion is not None:
        clase = clases[prediccion["clase_predicha_id"]]
        return Recomendacion(
            clase_id=clase.id, clase=clase.codigo, nombre=clase.nombre,
            confianza=round(float(prediccion["confianza"]), 2),
            roi=Roi(prediccion["roi_x"], prediccion["roi_y"], prediccion["roi_w"], prediccion["roi_h"]),
            modelo=prediccion["version_modelo"],
        )
    azar = random.Random(int(sha256[:16], 16))
    w, h = round(azar.uniform(0.25, 0.40), 3), round(azar.uniform(0.25, 0.40), 3)
    roi = Roi(round(azar.uniform(0.15, 0.85 - w), 3), round(azar.uniform(0.15, 0.85 - h), 3), w, h)
    return Recomendacion(
        clase_id=referencia.id, clase=referencia.codigo, nombre=referencia.nombre,
        confianza=round(azar.uniform(0.78, 0.96), 2), roi=roi, modelo=VERSION_SIMULADA,
    )

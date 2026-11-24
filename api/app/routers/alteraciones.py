"""
Configuración de las alteraciones de la IA y exportación (W19, RF-08.1, RF-08.2 y RF-15).
Responsable: Emmanuel Ospina · Actividad 4404 · Exportación (fase 6): Jahan Michelle Chará · 4507.

  GET /docente/alteraciones   configuración vigente (o la de por defecto)
  PUT /docente/alteraciones   guarda una nueva (queda el histórico)
  GET /docente/exportacion    fase 6: CSV seudonimizado con los intentos finalizados (RF-15)

Solo docentes y administradores, con sesión 2FA.
"""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, field_validator

from ..alteraciones import repositorio as repo
from ..alteraciones.estrategias import PORCENTAJE_MAXIMO, PORCENTAJE_POR_DEFECTO, TIPOS
from ..db import obtener_conexion
from ..intentos import exportacion
from ..intentos import repositorio as repo_intentos
from ..seguridad import Usuario
from .casos import docente_actual

router = APIRouter(tags=["alteraciones"])

TipoAlteracion = Literal["clase_incorrecta", "confianza_alterada", "roi_desplazada"]


class ConfigEntrada(BaseModel):
    porcentaje: float = Field(ge=0, le=PORCENTAJE_MAXIMO)
    tipos: list[TipoAlteracion] = Field(default_factory=list, max_length=3)

    @field_validator("tipos")
    @classmethod
    def _sin_repetidos(cls, tipos: list[str]) -> list[str]:
        return sorted(set(tipos))


def _vista(fila: dict | None) -> dict:
    if fila is None:
        return {"porcentaje": PORCENTAJE_POR_DEFECTO, "tipos": list(TIPOS), "vigente_desde": None,
                "por_defecto": True}
    return {"porcentaje": float(fila["porcentaje"]), "tipos": list(fila["tipos"]),
            "vigente_desde": fila["vigente_desde"].isoformat(), "por_defecto": False}


@router.get("/docente/alteraciones")
async def ver_config(_: Usuario = Depends(docente_actual), conexion=Depends(obtener_conexion)):
    return _vista(await repo.detalle_vigente(conexion))


@router.put("/docente/alteraciones")
async def guardar_config(entrada: ConfigEntrada, docente: Usuario = Depends(docente_actual),
                         conexion=Depends(obtener_conexion)):
    # Porcentaje mayor que 0 sin tipos no tendría efecto: se guarda como 0 para no confundir.
    porcentaje = entrada.porcentaje if entrada.tipos else 0.0
    return _vista(await repo.guardar_config(conexion, porcentaje, entrada.tipos, docente.id))


@router.get("/docente/exportacion")
async def exportar_intentos(_: Usuario = Depends(docente_actual), conexion=Depends(obtener_conexion)):
    contenido = exportacion.a_csv(await repo_intentos.filas_exportacion(conexion))
    return Response(
        content=contenido,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{exportacion.nombre_archivo(date.today())}"',
                 "Cache-Control": "no-store"},
    )

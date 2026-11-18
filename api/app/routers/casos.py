"""
Rutas de casos clínicos (capa de interfaz: solo traduce HTTP ↔ servicio).
Responsable: Emmanuel Ospina · RF-02.1, RF-04, RF-14.1 a RF-14.6.

  POST  /casos                 genera un caso nuevo (estudiante)
  GET   /casos/{id}            presenta un caso, sin la respuesta (estudiante)
  GET   /docente/casos         bandeja de revisión (docente o admin)
  PATCH /docente/casos/{id}    aprobar o descartar con motivo (docente o admin)

Todas exigen sesión con 2FA (aal2), igual que la fase 2.
"""
from functools import lru_cache
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from ..casos import repositorio as repo
from ..casos.servicio import CasoNoGenerado, ServicioCasos, SinImagenes
from ..config import obtener_configuracion
from ..db import obtener_conexion
from ..llm import ReintentoConRespaldo, crear_cliente_llm
from ..seguridad import Usuario, usuario_con_2fa
from ..storage import AdaptadorStorage, obtener_storage

router = APIRouter(tags=["casos"])

Dificultad = Literal["basico", "intermedio", "avanzado"]
Region = Literal["esofago", "estomago", "duodeno"]


@lru_cache
def _llm_compartido() -> ReintentoConRespaldo:
    return crear_cliente_llm(obtener_configuracion())


def obtener_llm() -> ReintentoConRespaldo:
    """Dependencia: las pruebas la reemplazan por un modelo falso."""
    return _llm_compartido()


def obtener_servicio(
    conexion=Depends(obtener_conexion),
    llm: ReintentoConRespaldo = Depends(obtener_llm),
    storage: AdaptadorStorage | None = Depends(obtener_storage),
) -> ServicioCasos:
    return ServicioCasos(conexion, llm, storage)


async def docente_actual(usuario: Usuario = Depends(usuario_con_2fa), conexion=Depends(obtener_conexion)) -> Usuario:
    """Solo docentes o administradores revisan casos (RF-14.6)."""
    if await repo.rol_de(conexion, usuario.id) not in ("docente", "admin"):
        raise HTTPException(403, "Esta función es solo para docentes")
    return usuario


class SolicitudCaso(BaseModel):
    dificultad: Dificultad = "basico"
    region: Region | None = None  # None = cualquier región (RF-02.2 es opcional)


class Revision(BaseModel):
    estado: Literal["aprobado", "descartado"]
    motivo: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _motivo_si_descarta(self):
        if self.estado == "descartado" and not (self.motivo and self.motivo.strip()):
            raise ValueError("Para descartar un caso escribe el motivo")
        return self


@router.post("/casos", status_code=201)
async def generar_caso(
    solicitud: SolicitudCaso,
    usuario: Usuario = Depends(usuario_con_2fa),
    servicio: ServicioCasos = Depends(obtener_servicio),
):
    try:
        return await servicio.generar(usuario.id, solicitud.dificultad, solicitud.region)
    except SinImagenes:
        raise HTTPException(503, "Aún no hay imágenes cargadas para generar casos. Avisa al equipo.")
    except CasoNoGenerado:
        # RF-14.4: el detalle técnico queda en generacion_fallida; al estudiante, un mensaje claro.
        raise HTTPException(422, "No se pudo generar un caso válido en este momento. Intenta de nuevo.")


@router.get("/casos/{caso_id}")
async def ver_caso(
    caso_id: UUID,
    _: Usuario = Depends(usuario_con_2fa),
    servicio: ServicioCasos = Depends(obtener_servicio),
):
    caso = await servicio.para_estudiante(caso_id)
    if caso is None:
        raise HTTPException(404, "El caso no existe o fue descartado")
    return caso


@router.get("/docente/casos")
async def bandeja_docente(
    estado: Literal["pendiente", "aprobado", "descartado", "todos"] = Query(default="pendiente"),
    limite: int = Query(default=50, ge=1, le=200),
    _: Usuario = Depends(docente_actual),
    servicio: ServicioCasos = Depends(obtener_servicio),
):
    return await servicio.para_docente(None if estado == "todos" else estado, limite)


@router.patch("/docente/casos/{caso_id}")
async def revisar_caso(
    caso_id: UUID,
    revision: Revision,
    docente: Usuario = Depends(docente_actual),
    servicio: ServicioCasos = Depends(obtener_servicio),
):
    if not await servicio.revisar(caso_id, revision.estado, revision.motivo, docente.id):
        raise HTTPException(404, "El caso no existe")
    return {"id": str(caso_id), "estado": revision.estado}

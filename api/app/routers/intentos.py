"""
Rutas para resolver un caso (capa de interfaz: solo traduce HTTP ↔ servicio).
Responsable: Diego Agudelo · RF-05, RF-07, RF-09 a RF-12.

  POST /intentos                        empieza a resolver un caso (o repite uno: RF-02.3)
  GET  /intentos                        fase 6: historial del estudiante (RF-02.3)
  GET  /mi-progreso                     fase 6: nivel, puntos e insignias (RF-11, W06)
  GET  /mi-desempeno                    fase 7: tablero de desempeño (RF-13, W16)
  GET  /intentos/{id}                   estado actual (lo que el estudiante puede ver)
  POST /intentos/{id}/eventos           telemetría de la escena 3D (lotes)
  POST /intentos/{id}/decision-inicial  decisión + confianza → recomendación de la IA
  POST /intentos/{id}/tutor             pregunta al tutor socrático
  POST /intentos/{id}/decision-final    cierra el intento → retroalimentación y puntaje

Todas exigen sesión con 2FA. Errores: 404 (no existe o no es tuyo),
409 (acción fuera de orden), 422 (opción inválida).
"""
from datetime import datetime
from functools import lru_cache
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator

from ..alteraciones.estrategias import ServicioAlteraciones
from ..config import obtener_configuracion
from ..db import obtener_conexion
from ..intentos.dominio import HITOS, TransicionInvalida
from ..intentos.servicio import NoEncontrado, OpcionInvalida, ServicioIntentos
from ..llm import crear_cliente_tutor
from ..seguridad import Usuario, usuario_con_2fa
from ..tutor.servicio import ServicioTutor

router = APIRouter(tags=["intentos"])


@lru_cache
def _tutor_compartido() -> ServicioTutor:
    return ServicioTutor(crear_cliente_tutor(obtener_configuracion()))


def obtener_tutor() -> ServicioTutor:
    """Dependencia: las pruebas la reemplazan por un tutor falso."""
    return _tutor_compartido()


def obtener_alteraciones() -> ServicioAlteraciones:
    """Dependencia: las pruebas la reemplazan para forzar un tipo de alteración."""
    return ServicioAlteraciones()


def obtener_servicio(conexion=Depends(obtener_conexion), tutor: ServicioTutor = Depends(obtener_tutor),
                     alteraciones: ServicioAlteraciones = Depends(obtener_alteraciones)) -> ServicioIntentos:
    return ServicioIntentos(conexion, tutor, alteraciones)


class NuevoIntento(BaseModel):
    caso_id: UUID


class Decision(BaseModel):
    clase: str = Field(min_length=1, max_length=40)
    confianza: int = Field(ge=1, le=5)  # escala de 1 (muy inseguro) a 5 (muy seguro)


class Pregunta(BaseModel):
    mensaje: str = Field(min_length=1, max_length=500)

    @field_validator("mensaje")
    @classmethod
    def _limpiar(cls, mensaje: str) -> str:
        mensaje = mensaje.strip()
        if not mensaje:
            raise ValueError("Escribe una pregunta")
        return mensaje


class Evento(BaseModel):
    tipo: Literal["hito_visitado", "hallazgo_capturado", "hallazgo_omitido", "captura_invalida", "pausa",
                  "reanudacion"]
    datos: dict = Field(default_factory=dict)
    ocurrido_en: datetime

    @field_validator("datos")
    @classmethod
    def _pequeno(cls, datos: dict) -> dict:
        if len(str(datos)) > 2000:
            raise ValueError("Datos del evento demasiado grandes")
        return datos

    @model_validator(mode="after")
    def _hito_conocido(self) -> "Evento":
        # Fase 5 (RF-03.3): un hito visitado debe ser uno de los 7 del catálogo; así la insignia
        # "Explorador" y el tablero no cuentan nombres inventados.
        if self.tipo == "hito_visitado" and self.datos.get("hito") not in HITOS:
            raise ValueError(f"Hito desconocido. Use uno de: {', '.join(HITOS)}")
        return self


class LoteEventos(BaseModel):
    eventos: list[Evento] = Field(min_length=1, max_length=200)


async def _ejecutar(corrutina):
    try:
        return await corrutina
    except NoEncontrado:
        raise HTTPException(404, "El intento no existe")
    except TransicionInvalida as e:
        raise HTTPException(409, str(e))
    except OpcionInvalida as e:
        raise HTTPException(422, str(e))


@router.post("/intentos", status_code=201)
async def iniciar(entrada: NuevoIntento, usuario: Usuario = Depends(usuario_con_2fa),
                  servicio: ServicioIntentos = Depends(obtener_servicio)):
    try:
        return await servicio.iniciar(usuario.id, entrada.caso_id)
    except NoEncontrado:
        raise HTTPException(404, "El caso no existe o fue descartado")


@router.get("/intentos")
async def historial(limite: int = Query(default=20, ge=1, le=100), usuario: Usuario = Depends(usuario_con_2fa),
                    servicio: ServicioIntentos = Depends(obtener_servicio)):
    return await _ejecutar(servicio.historial(usuario.id, limite))


@router.get("/mi-progreso")
async def mi_progreso(usuario: Usuario = Depends(usuario_con_2fa),
                      servicio: ServicioIntentos = Depends(obtener_servicio)):
    return await _ejecutar(servicio.progreso(usuario.id))


@router.get("/mi-desempeno")
async def mi_desempeno(usuario: Usuario = Depends(usuario_con_2fa),
                       servicio: ServicioIntentos = Depends(obtener_servicio)):
    return await _ejecutar(servicio.desempeno(usuario.id))


@router.get("/intentos/{intento_id}")
async def ver(intento_id: UUID, usuario: Usuario = Depends(usuario_con_2fa),
              servicio: ServicioIntentos = Depends(obtener_servicio)):
    return await _ejecutar(servicio.ver(usuario.id, intento_id))


@router.post("/intentos/{intento_id}/eventos")
async def eventos(intento_id: UUID, lote: LoteEventos, usuario: Usuario = Depends(usuario_con_2fa),
                  servicio: ServicioIntentos = Depends(obtener_servicio)):
    n = await _ejecutar(servicio.registrar_eventos(usuario.id, intento_id, [e.model_dump() for e in lote.eventos]))
    return {"registrados": n}


@router.post("/intentos/{intento_id}/decision-inicial")
async def decision_inicial(intento_id: UUID, d: Decision, usuario: Usuario = Depends(usuario_con_2fa),
                           servicio: ServicioIntentos = Depends(obtener_servicio)):
    return await _ejecutar(servicio.decision_inicial(usuario.id, intento_id, d.clase, d.confianza))


@router.post("/intentos/{intento_id}/tutor")
async def tutor(intento_id: UUID, p: Pregunta, usuario: Usuario = Depends(usuario_con_2fa),
                servicio: ServicioIntentos = Depends(obtener_servicio)):
    return await _ejecutar(servicio.preguntar(usuario.id, intento_id, p.mensaje))


@router.post("/intentos/{intento_id}/decision-final")
async def decision_final(intento_id: UUID, d: Decision, usuario: Usuario = Depends(usuario_con_2fa),
                         servicio: ServicioIntentos = Depends(obtener_servicio)):
    return await _ejecutar(servicio.decision_final(usuario.id, intento_id, d.clase, d.confianza))

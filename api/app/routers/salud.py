"""
Estado de la plataforma y catálogos públicos.
Responsable: Diego Agudelo · Paquete 4.6 Plataforma e integración.

/salud lo usan Docker, el monitoreo de disponibilidad (RNF-11, Cristian)
y el frontend para saber si el sistema está arriba.
Los catálogos los consumirán el simulador 3D (Cristian, hitos) y el
generador de casos (Emmanuel, clases de hallazgo). No exponen respuestas
de casos, por eso no requieren sesión.
"""
from fastapi import APIRouter, Depends, HTTPException

from ..config import Configuracion, obtener_configuracion
from ..db import obtener_conexion

router = APIRouter(tags=["plataforma"])

TABLAS_ESPERADAS = 18  # Diseño de Base de Datos v1.0


@router.get("/salud")
async def salud(config: Configuracion = Depends(obtener_configuracion)):
    try:
        async for conexion in obtener_conexion():
            fila = await (await conexion.execute(
                "select count(*) as tablas from information_schema.tables "
                "where table_schema in ('public', 'investigacion') and table_type = 'BASE TABLE'"
            )).fetchone()
    except Exception:
        # No se muestra el error interno: podría revelar datos de conexión.
        raise HTTPException(status_code=503, detail="La base de datos no responde")
    esquema_ok = fila["tablas"] == TABLAS_ESPERADAS
    return {
        "estado": "ok" if esquema_ok else "incompleto",
        "version": config.app_version,
        "entorno": config.entorno,
        "base_de_datos": {"conectada": True, "tablas": fila["tablas"], "esperadas": TABLAS_ESPERADAS},
    }


@router.get("/catalogos/hitos")
async def hitos(conexion=Depends(obtener_conexion)):
    """Los 7 hitos anatómicos en orden de recorrido (RF-03.3)."""
    cursor = await conexion.execute(
        "select codigo, nombre, region, orden from public.hito_anatomico order by orden"
    )
    return await cursor.fetchall()


@router.get("/catalogos/clases")
async def clases(conexion=Depends(obtener_conexion)):
    """Clases de hallazgo del tracto superior de HyperKvasir (RF-14.1)."""
    cursor = await conexion.execute(
        "select codigo, nombre_es, region, es_patologico from public.clase_hallazgo order by id"
    )
    return await cursor.fetchall()

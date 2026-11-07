"""
Punto de entrada de la API de GASTRO-SIM.
Responsable: Diego Agudelo · Development Manager.

Arquitectura: monolito modular en capas (ADR-01). En esta fase solo existe
la capa de interfaz (routers) y la infraestructura (db). Cada fase siguiente
agrega su router: cuentas (fase 2), casos (fase 3), intentos (fase 4)...
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import obtener_configuracion
from .db import abrir_pool, cerrar_pool
from .errores import registrar_manejadores
from .routers import salud


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    # Al arrancar: abrir conexiones. Al apagar: cerrarlas.
    await abrir_pool(obtener_configuracion().database_url)
    yield
    await cerrar_pool()


def crear_app() -> FastAPI:
    config = obtener_configuracion()
    app = FastAPI(
        title="GASTRO-SIM API",
        version=config.app_version,
        description="Simulador 3D de decisiones humano–IA en endoscopia digestiva alta. Uso académico.",
        lifespan=ciclo_de_vida,
    )
    # Solo el frontend autorizado puede llamar a la API desde el navegador.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origenes_permitidos,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    registrar_manejadores(app)
    app.include_router(salud.router)
    return app


app = crear_app()

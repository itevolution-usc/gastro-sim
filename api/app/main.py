"""
Punto de entrada de la API de GASTRO-SIM.
Responsable: Diego Agudelo · Development Manager.

Arquitectura: monolito modular en capas (ADR-01). Capa de interfaz (routers),
seguridad (seguridad.py), adaptadores externos (auth_admin.py) e
infraestructura (db). Cada fase agrega su router: salud (fase 1),
cuentas (fase 2), casos (fase 3), intentos (fase 4)...
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import obtener_configuracion
from .db import abrir_pool, cerrar_pool
from .errores import registrar_manejadores
from .routers import cuentas, salud


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
    app.include_router(cuentas.router)  # fase 2: perfil, aviso y 2FA
    return app


app = crear_app()

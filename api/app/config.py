"""
Configuración de la API leída de variables de entorno (.env).
Responsable: Diego Agudelo · Paquete 4.6 Plataforma e integración.

Ninguna clave se escribe en el código: todo llega del entorno (RNF-07).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    # Lee el archivo .env si existe; las variables del sistema tienen prioridad.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    entorno: str = "desarrollo"
    app_version: str = "0.1.0"
    # Lista separada por comas, por ejemplo "http://localhost:5173,https://gastro-sim.app"
    cors_origenes: str = "http://localhost:5173"

    @property
    def origenes_permitidos(self) -> list[str]:
        return [o.strip() for o in self.cors_origenes.split(",") if o.strip()]


@lru_cache
def obtener_configuracion() -> Configuracion:
    # Se crea una sola vez y se reutiliza en toda la API.
    return Configuracion()

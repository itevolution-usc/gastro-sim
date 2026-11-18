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

    # --- Supabase Auth (fase 2) ---
    # URL del proyecto: con ella la API descarga las claves públicas (JWKS)
    # para verificar los tokens de sesión.
    supabase_url: str = ""
    # Secreto JWT heredado (HS256). Solo si el proyecto aún firma con él.
    supabase_jwt_secret: str = ""
    # Clave service_role: permite borrar el factor 2FA al usar un código de
    # recuperación. Es secreta: solo vive en el .env del servidor.
    supabase_service_role_key: str = ""

    # Fase 3 · Generador de casos con IA (RF-14.2). Sin clave, la API usa el
    # generador local de respaldo: funciona sin internet y sin costo.
    gemini_api_key: str = ""
    # El primero es el principal; los demás son respaldos si está saturado.
    # flash-lite va primero: responde en ~1 s; los grandes suelen saturarse (RNF-14).
    gemini_modelos: str = "gemini-3.5-flash-lite,gemini-3.8-flash,gemini-3.6-flash"
    # Segundos máximos por llamada al modelo (RNF-14: caso listo en < 15 s).
    llm_tiempo_maximo: float = 12.0
    # Si todos los modelos fallan, usar el generador local en vez de fallar.
    llm_respaldo_local: bool = True

    @property
    def modelos_gemini(self) -> list[str]:
        return [m.strip() for m in self.gemini_modelos.split(",") if m.strip()]

    @property
    def origenes_permitidos(self) -> list[str]:
        return [o.strip() for o in self.cors_origenes.split(",") if o.strip()]


@lru_cache
def obtener_configuracion() -> Configuracion:
    # Se crea una sola vez y se reutiliza en toda la API.
    return Configuracion()

"""
Adaptador de la API de administración de Supabase Auth (patrón Adapter).
Responsable: Diego Agudelo · Actividad 4606 (RF-01.6).

El resto de la API no conoce las URL ni las cabeceras de Supabase: solo llama
a eliminar_factores_totp(). Si mañana cambiamos de proveedor de
autenticación, solo cambia este archivo.

Requiere la clave service_role, que salta toda la seguridad del proyecto:
por eso vive solo en el .env del servidor y nunca llega al navegador.
"""
from uuid import UUID

import httpx2
from fastapi import Depends, HTTPException

from .config import Configuracion, obtener_configuracion


class ErrorAuthAdmin(Exception):
    """Supabase Auth no respondió como se esperaba."""


class ClienteAuthAdmin:
    def __init__(self, url_supabase: str, clave_service_role: str):
        self._base = f"{url_supabase.rstrip('/')}/auth/v1"
        self._cabeceras = {"apikey": clave_service_role, "Authorization": f"Bearer {clave_service_role}"}

    async def eliminar_factores_totp(self, usuario_id: UUID) -> int:
        """Borra los factores TOTP del usuario para que vuelva a activar su 2FA.
        Devuelve cuántos factores se eliminaron."""
        try:
            async with httpx2.AsyncClient(base_url=self._base, headers=self._cabeceras, timeout=10) as http:
                respuesta = await http.get(f"/admin/users/{usuario_id}")
                respuesta.raise_for_status()
                factores = [
                    f for f in (respuesta.json().get("factors") or []) if f.get("factor_type") == "totp"
                ]
                for factor in factores:
                    borrado = await http.delete(f"/admin/users/{usuario_id}/factors/{factor['id']}")
                    borrado.raise_for_status()
                return len(factores)
        except httpx2.HTTPError as error:
            raise ErrorAuthAdmin(str(error)) from error


def obtener_admin(config: Configuracion = Depends(obtener_configuracion)) -> ClienteAuthAdmin:
    """Dependencia de FastAPI. En las pruebas se reemplaza por un cliente falso."""
    if not (config.supabase_url and config.supabase_service_role_key):
        raise HTTPException(status_code=503, detail="La recuperación de cuenta no está configurada en el servidor")
    return ClienteAuthAdmin(config.supabase_url, config.supabase_service_role_key)

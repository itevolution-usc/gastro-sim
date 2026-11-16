"""
Adaptador de Supabase Storage: imágenes del dataset (bucket privado "imagenes").
Responsable: Diego Agudelo · Actividad 4205 (RF-14.1) y RNF-08.

El bucket es privado: el navegador nunca lo lee directo. La API firma una URL
que vence en minutos, y solo para quien tiene sesión con 2FA.
Usa la clave service_role del .env; si falta (pruebas automáticas, Docker sin
Supabase), las URL salen vacías y la API sigue funcionando.
"""
from urllib.parse import quote

import httpx2
from fastapi import Depends

from .config import Configuracion, obtener_configuracion

BUCKET = "imagenes"


class ErrorStorage(Exception):
    pass


class AdaptadorStorage:
    def __init__(self, url_supabase: str, clave_servicio: str):
        self._base = url_supabase.rstrip("/") + "/storage/v1"
        self._cabeceras = {"apikey": clave_servicio, "Authorization": f"Bearer {clave_servicio}"}

    async def url_firmada(self, ruta: str, segundos: int = 900) -> str | None:
        """URL temporal para ver una imagen. None si Storage no responde (no rompe el caso)."""
        try:
            async with httpx2.AsyncClient(timeout=5) as http:
                r = await http.post(
                    f"{self._base}/object/sign/{BUCKET}/{quote(ruta)}",
                    headers=self._cabeceras,
                    json={"expiresIn": segundos},
                )
            if r.status_code != 200:
                return None
            return self._base + r.json()["signedURL"]
        except (httpx2.HTTPError, KeyError, ValueError):
            return None

    async def subir(self, ruta: str, contenido: bytes, tipo: str = "image/jpeg") -> None:
        """Sube (o reemplaza) un archivo. Lo usa el script cargar_imagenes.py."""
        async with httpx2.AsyncClient(timeout=60) as http:
            r = await http.post(
                f"{self._base}/object/{BUCKET}/{quote(ruta)}",
                headers={**self._cabeceras, "Content-Type": tipo, "x-upsert": "true"},
                content=contenido,
            )
        if r.status_code not in (200, 201):
            raise ErrorStorage(f"No se pudo subir {ruta}: HTTP {r.status_code} {r.text[:200]}")


def obtener_storage(config: Configuracion = Depends(obtener_configuracion)) -> AdaptadorStorage | None:
    """Dependencia de FastAPI. None = Storage no configurado (las pruebas lo reemplazan)."""
    if not (config.supabase_url and config.supabase_service_role_key):
        return None
    return AdaptadorStorage(config.supabase_url, config.supabase_service_role_key)

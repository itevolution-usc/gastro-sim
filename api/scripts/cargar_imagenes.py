"""
Carga un subconjunto de HyperKvasir en Supabase Storage y en la tabla imagen.
Responsable: Diego Agudelo · Actividad 4205 (RF-14.1) y RNF-08.

HyperKvasir (Borgli et al., 2020) es público, desidentificado y con licencia
CC BY 4.0. Su archivo de imágenes etiquetadas pesa 3,9 GB, pero este script
NO lo descarga completo: lee el zip por partes (peticiones HTTP con rango) y
solo baja las imágenes elegidas (unos 35 archivos de ~100 kB).

Uso (desde la raíz del repositorio, con Docker encendido):
    docker compose run --rm api python -m scripts.cargar_imagenes --solo-listar
    docker compose run --rm api python -m scripts.cargar_imagenes --por-clase 5

Se puede repetir sin duplicar: la imagen se reemplaza en Storage y la fila no
se inserta dos veces (archivo_origen es único).
"""
import argparse
import asyncio
import hashlib
import io
import random
import ssl
import sys
import zipfile
from pathlib import Path, PurePosixPath

import httpx2
import psycopg

from app.config import obtener_configuracion
from app.storage import AdaptadorStorage

URL_HYPERKVASIR = "https://datasets.simula.no/downloads/hyper-kvasir/hyper-kvasir-labeled-images.zip"

# El servidor de HyperKvasir no envía su certificado intermedio (Sectigo DV R36)
# y Python rechaza la conexión. Lo guardamos en el repositorio (es público) y lo
# sumamos a los certificados de confianza del sistema: la conexión sigue
# verificada hasta la raíz de Sectigo. Nunca se desactiva la verificación.
CERTIFICADO_INTERMEDIO = Path(__file__).parent / "certificados" / "sectigo_dv_r36.pem"


def contexto_tls() -> ssl.SSLContext:
    contexto = ssl.create_default_context()
    contexto.load_verify_locations(cafile=CERTIFICADO_INTERMEDIO)
    return contexto

# Clases del tracto superior (las 7 de clase_hallazgo) y su dificultad didáctica:
# lo normal es "basico"; lo sutil (grado A, segmento corto) es "avanzado".
DIFICULTAD = {
    "z-line": "basico",
    "pylorus": "basico",
    "retroflex-stomach": "basico",
    "esophagitis-b-d": "intermedio",
    "barretts": "intermedio",
    "esophagitis-a": "avanzado",
    "barretts-short-segment": "avanzado",
}


class ArchivoRemoto(io.RawIOBase):
    """Archivo de solo lectura sobre HTTP: cada read() pide solo los bytes necesarios."""

    def __init__(self, url: str):
        self._url = url
        self._http = httpx2.Client(timeout=60, follow_redirects=True, verify=contexto_tls())
        r = self._http.head(url)
        r.raise_for_status()
        if r.headers.get("accept-ranges") != "bytes":
            raise RuntimeError("El servidor no permite descargas parciales")
        self._tamano = int(r.headers["content-length"])
        self._pos = 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, desplazamiento: int, desde: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self._tamano}[desde]
        self._pos = max(0, min(self._tamano, base + desplazamiento))
        return self._pos

    def read(self, n: int = -1) -> bytes:
        if self._pos >= self._tamano:
            return b""
        fin = self._tamano - 1 if n is None or n < 0 else min(self._tamano - 1, self._pos + n - 1)
        r = self._http.get(self._url, headers={"Range": f"bytes={self._pos}-{fin}"})
        r.raise_for_status()
        self._pos += len(r.content)
        return r.content

    def readinto(self, destino) -> int:
        # io.BufferedReader llama a este método; así lee bloques de 1 MB y hace pocas peticiones.
        datos = self.read(len(destino))
        destino[: len(datos)] = datos
        return len(datos)

    def close(self) -> None:
        self._http.close()
        super().close()


def abrir_zip(origen: str) -> zipfile.ZipFile:
    """origen puede ser la URL del dataset o la ruta a un zip ya descargado."""
    if origen.startswith(("http://", "https://")):
        return zipfile.ZipFile(io.BufferedReader(ArchivoRemoto(origen), buffer_size=1 << 20))
    return zipfile.ZipFile(origen)


def elegir(nombres: list[str], por_clase: int, semilla: int) -> dict[str, list[str]]:
    """Agrupa las imágenes .jpg por carpeta de clase y elige N de cada una (siempre las mismas
    para la misma semilla, así todo el equipo carga el mismo subconjunto)."""
    grupos: dict[str, list[str]] = {clase: [] for clase in DIFICULTAD}
    for nombre in nombres:
        ruta = PurePosixPath(nombre)
        if ruta.suffix.lower() == ".jpg" and ruta.parent.name in grupos:
            grupos[ruta.parent.name].append(nombre)
    azar = random.Random(semilla)
    return {clase: azar.sample(sorted(lista), min(por_clase, len(lista))) for clase, lista in grupos.items()}


async def cargar(origen: str, por_clase: int, semilla: int, solo_listar: bool) -> int:
    config = obtener_configuracion()
    with abrir_zip(origen) as zf:
        elegidas = elegir(zf.namelist(), por_clase, semilla)
        for clase, lista in elegidas.items():
            print(f"{clase:24} {len(lista)} imágenes")
        if solo_listar:
            return 0
        if not (config.supabase_url and config.supabase_service_role_key):
            print("Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en el .env", file=sys.stderr)
            return 1
        storage = AdaptadorStorage(config.supabase_url, config.supabase_service_role_key)
        cargadas = 0
        with psycopg.connect(config.database_url) as conexion:
            clases = dict(conexion.execute("select codigo, id from public.clase_hallazgo").fetchall())
            for clase, lista in elegidas.items():
                for nombre in lista:
                    archivo = PurePosixPath(nombre).name
                    ruta = f"{clase}/{archivo}"
                    contenido = zf.read(nombre)
                    await storage.subir(ruta, contenido)
                    # La huella sha256 evita cargar la misma imagen dos veces con otro nombre.
                    conexion.execute(
                        """insert into public.imagen (archivo_origen, ruta_storage, clase_id, dificultad, sha256)
                           values (%s, %s, %s, %s, %s) on conflict do nothing""",
                        (archivo, ruta, clases[clase], DIFICULTAD[clase], hashlib.sha256(contenido).hexdigest()),
                    )
                    conexion.commit()
                    cargadas += 1
                    print(f"  ✔ {ruta}")
        print(f"Listo: {cargadas} imágenes en Storage y en la tabla imagen.")
        return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Carga imágenes de HyperKvasir (tracto superior)")
    p.add_argument("--origen", default=URL_HYPERKVASIR, help="URL del zip o ruta a un zip local")
    p.add_argument("--por-clase", type=int, default=5, help="Imágenes por clase (7 clases)")
    p.add_argument("--semilla", type=int, default=2026, help="Misma semilla = mismas imágenes")
    p.add_argument("--solo-listar", action="store_true", help="Solo muestra cuántas hay; no sube nada")
    a = p.parse_args()
    return asyncio.run(cargar(a.origen, a.por_clase, a.semilla, a.solo_listar))


if __name__ == "__main__":
    sys.exit(main())

"""
Conexión a PostgreSQL con un grupo (pool) de conexiones asíncronas.
Responsable: Diego Agudelo · Paquete 4.6 Plataforma e integración.

Se abre al arrancar la API y se cierra al apagarla. Los repositorios de las
fases siguientes (casos, intentos, cuentas) piden conexiones a este pool.
"""
from collections.abc import AsyncIterator

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

_pool: AsyncConnectionPool | None = None


async def abrir_pool(database_url: str) -> None:
    global _pool
    _pool = AsyncConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=10,
        # Cada fila llega como diccionario: {"codigo": "linea_z", ...}
        kwargs={"row_factory": dict_row},
        open=False,
    )
    # wait=False: la API arranca aunque la base de datos todavía no responda;
    # /salud lo informará con un 503 en lugar de tumbar el servidor.
    await _pool.open(wait=False)


async def cerrar_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def obtener_conexion() -> AsyncIterator:
    """Dependencia de FastAPI: entrega una conexión y la devuelve al terminar."""
    if _pool is None:
        raise RuntimeError("El pool de base de datos no está abierto")
    async with _pool.connection(timeout=5) as conexion:
        yield conexion

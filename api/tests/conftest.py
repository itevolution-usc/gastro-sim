"""
Configuración común de las pruebas.
Responsable: Nestor Velasco · Quality Manager (actividad 4611).

Las pruebas usan la base de datos real indicada en DATABASE_URL (prueba de
integración). El cliente se crea con "with" para que se ejecute el ciclo de
vida de la API (abrir y cerrar el pool).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def cliente():
    with TestClient(app) as c:
        yield c

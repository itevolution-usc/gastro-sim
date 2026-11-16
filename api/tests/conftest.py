"""
Configuración común de las pruebas.
Responsable: Nestor Velasco · Quality Manager (actividad 4611).

Las pruebas usan la base de datos real indicada en DATABASE_URL (prueba de
integración). El cliente se crea con "with" para que se ejecute el ciclo de
vida de la API (abrir y cerrar el pool).

Fase 2: las pruebas NO usan el Supabase real. Firman sus propios tokens con
un secreto de prueba, así corren sin internet, en cualquier computador y en
GitHub Actions. Estas variables se fijan ANTES de importar la API para que
ganen sobre lo que tenga el .env de cada uno.
"""
import os
import time
import uuid

os.environ["SUPABASE_JWT_SECRET"] = "secreto-solo-para-pruebas-automaticas-0123456789"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""

import jwt  # noqa: E402
import psycopg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import obtener_configuracion  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def cliente():
    with TestClient(app) as c:
        yield c


def crear_token(usuario_id: str, aal: str = "aal1", email: str = "prueba@gastro.test", **cambios) -> str:
    """Token igual al que emite Supabase Auth, firmado con el secreto de prueba."""
    ahora = int(time.time())
    datos = {"sub": usuario_id, "aud": "authenticated", "role": "authenticated", "email": email,
             "aal": aal, "iat": ahora, "exp": ahora + 3600}
    datos.update(cambios)
    return jwt.encode(datos, os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256")


@pytest.fixture
def usuario():
    """Crea un usuario de prueba en auth.users (el disparador crea su perfil) y lo borra al final."""
    usuario_id = str(uuid.uuid4())
    email = f"prueba-{usuario_id[:8]}@gastro.test"
    url = obtener_configuracion().database_url
    if "supabase" in url:
        # Protección: nunca crear usuarios de prueba en la base real del proyecto.
        pytest.skip("Las pruebas de cuentas solo corren contra la base de datos local (Docker o CI)")
    with psycopg.connect(url, autocommit=True) as conexion:
        conexion.execute("insert into auth.users (id, email) values (%s, %s)", (usuario_id, email))
    yield {"id": usuario_id, "email": email}
    with psycopg.connect(url, autocommit=True) as conexion:
        conexion.execute("delete from public.auditoria_cuenta where afectado_id = %s", (usuario_id,))
        conexion.execute("delete from auth.users where id = %s", (usuario_id,))

"""
Pruebas de la fase 2: sesión, aviso académico y 2FA.
Responsable: Diego Agudelo (desarrollo) · revisión: Nestor Velasco (calidad).
Requisitos: RF-01.1, RF-01.2, RF-01.4, RF-01.5, RF-01.6 y RNF-07.
Ejecutar dentro de la carpeta api/:   pytest -v
"""
import os
import time
import uuid

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app import seguridad
from app.auth_admin import ErrorAuthAdmin, obtener_admin
from app.config import Configuracion, obtener_configuracion
from app.main import app
from app.routers.cuentas import VERSION_AVISO, coincide, normalizar

from .conftest import crear_token


def cabecera(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def consultar(sql: str, parametros: tuple):
    with psycopg.connect(obtener_configuracion().database_url) as conexion:
        return conexion.execute(sql, parametros).fetchall()


class AdminFalso:
    """Reemplaza a Supabase Auth en las pruebas: anota a quién se le borró el 2FA."""

    def __init__(self, falla: bool = False):
        self.falla = falla
        self.llamadas = []

    async def eliminar_factores_totp(self, usuario_id):
        if self.falla:
            raise ErrorAuthAdmin("sin conexión")
        self.llamadas.append(str(usuario_id))
        return 1


@pytest.fixture
def admin_falso():
    falso = AdminFalso()
    app.dependency_overrides[obtener_admin] = lambda: falso
    yield falso
    app.dependency_overrides.pop(obtener_admin, None)


# ---------- RNF-07: el token se valida siempre ----------

def test_sin_token_responde_401(cliente):
    r = cliente.get("/cuentas/yo")
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/problem+json")


def test_token_firmado_con_otra_clave_responde_401(cliente, usuario):
    falso = jwt.encode({"sub": usuario["id"], "aud": "authenticated", "exp": int(time.time()) + 60},
                       "otra-clave-que-no-es-la-del-proyecto-0123456789", algorithm="HS256")
    assert cliente.get("/cuentas/yo", headers=cabecera(falso)).status_code == 401


def test_token_vencido_responde_401(cliente, usuario):
    vencido = crear_token(usuario["id"], exp=int(time.time()) - 10)
    assert cliente.get("/cuentas/yo", headers=cabecera(vencido)).status_code == 401


def test_token_sin_firma_alg_none_responde_401(cliente, usuario):
    sin_firma = jwt.encode({"sub": usuario["id"], "aud": "authenticated", "exp": int(time.time()) + 60},
                           None, algorithm="none")
    assert cliente.get("/cuentas/yo", headers=cabecera(sin_firma)).status_code == 401


def test_token_con_otra_audiencia_responde_401(cliente, usuario):
    otra = crear_token(usuario["id"], aud="anon")
    assert cliente.get("/cuentas/yo", headers=cabecera(otra)).status_code == 401


def test_token_asimetrico_es256_se_valida_con_jwks(monkeypatch):
    """Los proyectos nuevos de Supabase firman con ES256; la API usa su JWKS."""
    privada = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode({"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60,
                        "aal": "aal2"}, privada, algorithm="ES256", headers={"kid": "clave-1"})

    class JwksFalso:
        def get_signing_key_from_jwt(self, _token):
            return type("Clave", (), {"key": privada.public_key()})()

    monkeypatch.setattr(seguridad, "_cliente_jwks", lambda _url: JwksFalso())
    config = Configuracion(database_url="postgresql://x", supabase_url="https://demo.supabase.co")
    assert seguridad.decodificar_token(token, config)["aal"] == "aal2"


# ---------- RF-01.1: perfil creado al registrarse ----------

def test_perfil_se_crea_como_estudiante_sin_2fa(cliente, usuario):
    r = cliente.get("/cuentas/yo", headers=cabecera(crear_token(usuario["id"], email=usuario["email"])))
    assert r.status_code == 200
    datos = r.json()
    assert datos["rol"] == "estudiante"
    assert datos["nombre_visible"] == usuario["email"].split("@")[0]
    assert datos["mfa_activado"] is False
    assert datos["aviso_aceptado"] is False
    assert datos["nivel_sesion"] == "aal1"


def test_usuario_sin_perfil_responde_404(cliente):
    r = cliente.get("/cuentas/yo", headers=cabecera(crear_token(str(uuid.uuid4()))))
    assert r.status_code == 404


# ---------- RF-01.4: aviso académico ----------

def test_aviso_con_version_vieja_responde_409(cliente, usuario):
    r = cliente.post("/cuentas/aviso", json={"version": "2020-01"}, headers=cabecera(crear_token(usuario["id"])))
    assert r.status_code == 409


def test_aceptar_aviso_vigente(cliente, usuario):
    token = crear_token(usuario["id"])
    r = cliente.post("/cuentas/aviso", json={"version": VERSION_AVISO}, headers=cabecera(token))
    assert r.status_code == 200
    assert cliente.get("/cuentas/yo", headers=cabecera(token)).json()["aviso_aceptado"] is True


# ---------- RF-01.5 y RF-01.6: 2FA y códigos de recuperación ----------

def test_codigos_exigen_sesion_con_2fa(cliente, usuario):
    r = cliente.post("/cuentas/2fa/codigos", headers=cabecera(crear_token(usuario["id"], aal="aal1")))
    assert r.status_code == 403


def test_generar_10_codigos_unicos_guardados_cifrados(cliente, usuario):
    token = crear_token(usuario["id"], aal="aal2")
    r = cliente.post("/cuentas/2fa/codigos", headers=cabecera(token))
    assert r.status_code == 200
    codigos = r.json()["codigos"]
    assert len(codigos) == 10 and len(set(codigos)) == 10
    assert all(len(c) == 11 and c[5] == "-" for c in codigos)
    huellas = [f[0] for f in consultar(
        "select codigo_hash from public.codigo_recuperacion where perfil_id = %s", (usuario["id"],))]
    assert len(huellas) == 10
    assert not any(c in h or normalizar(c) in h for c in codigos for h in huellas)  # nunca en claro
    perfil = cliente.get("/cuentas/yo", headers=cabecera(token)).json()
    assert perfil["mfa_activado"] is True and perfil["codigos_disponibles"] == 10


def test_regenerar_invalida_los_codigos_anteriores(cliente, usuario):
    token = crear_token(usuario["id"], aal="aal2")
    viejos = cliente.post("/cuentas/2fa/codigos", headers=cabecera(token)).json()["codigos"]
    cliente.post("/cuentas/2fa/codigos", headers=cabecera(token))
    huellas = [f[0] for f in consultar(
        "select codigo_hash from public.codigo_recuperacion where perfil_id = %s", (usuario["id"],))]
    assert len(huellas) == 10
    assert not any(coincide(viejos[0], h) for h in huellas)


def test_recuperar_con_codigo_valido_borra_el_2fa(cliente, usuario, admin_falso):
    codigos = cliente.post("/cuentas/2fa/codigos",
                           headers=cabecera(crear_token(usuario["id"], aal="aal2"))).json()["codigos"]
    token_aal1 = crear_token(usuario["id"], aal="aal1")
    # Se acepta escrito en minúsculas y sin guion.
    r = cliente.post("/cuentas/2fa/recuperar", json={"codigo": codigos[3].lower().replace("-", "")},
                     headers=cabecera(token_aal1))
    assert r.status_code == 200
    assert r.json() == {"recuperado": True, "codigos_restantes": 9}
    assert admin_falso.llamadas == [usuario["id"]]
    perfil = cliente.get("/cuentas/yo", headers=cabecera(token_aal1)).json()
    assert perfil["mfa_activado"] is False and perfil["codigos_disponibles"] == 9
    auditoria = consultar("select accion from public.auditoria_cuenta where afectado_id = %s", (usuario["id"],))
    assert auditoria == [("restablecer_2fa",)]
    # Un código usado no sirve dos veces.
    otra_vez = cliente.post("/cuentas/2fa/recuperar", json={"codigo": codigos[3]}, headers=cabecera(token_aal1))
    assert otra_vez.status_code == 400


def test_recuperar_con_codigo_invalido_responde_400(cliente, usuario, admin_falso):
    cliente.post("/cuentas/2fa/codigos", headers=cabecera(crear_token(usuario["id"], aal="aal2")))
    r = cliente.post("/cuentas/2fa/recuperar", json={"codigo": "AAAAA-AAAAA"},
                     headers=cabecera(crear_token(usuario["id"])))
    assert r.status_code == 400
    assert admin_falso.llamadas == []


def test_si_supabase_falla_el_codigo_no_se_gasta(cliente, usuario):
    falso = AdminFalso(falla=True)
    app.dependency_overrides[obtener_admin] = lambda: falso
    try:
        codigos = cliente.post("/cuentas/2fa/codigos",
                               headers=cabecera(crear_token(usuario["id"], aal="aal2"))).json()["codigos"]
        r = cliente.post("/cuentas/2fa/recuperar", json={"codigo": codigos[0]},
                         headers=cabecera(crear_token(usuario["id"])))
        assert r.status_code == 503
        disponibles = consultar("select count(*) from public.codigo_recuperacion "
                                "where perfil_id = %s and usado_en is null", (usuario["id"],))
        assert disponibles == [(10,)]
    finally:
        app.dependency_overrides.pop(obtener_admin, None)


def test_recuperar_sin_clave_service_role_responde_503(cliente, usuario):
    assert os.environ["SUPABASE_SERVICE_ROLE_KEY"] == ""
    r = cliente.post("/cuentas/2fa/recuperar", json={"codigo": "AAAAA-AAAAA"},
                     headers=cabecera(crear_token(usuario["id"])))
    assert r.status_code == 503

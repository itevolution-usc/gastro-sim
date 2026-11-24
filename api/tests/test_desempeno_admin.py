"""
Pruebas de la fase 7: tablero de desempeño (W16) y administración de cuentas (W20 y W21).
Responsable: Nestor Velasco (calidad) · código bajo prueba: Michelle (desempeño) y Diego (administración).
Requisitos: RF-13, RF-01.3 y RF-01.7 (con registro en auditoria_cuenta).
Ejecutar dentro de la carpeta api/:   pytest -v

Ninguna prueba llama a Gemini ni a Supabase Auth: el restablecimiento del 2FA usa un cliente falso.
"""
import uuid
from datetime import datetime, timezone

import pytest

from app.auth_admin import ErrorAuthAdmin, obtener_admin
from app.intentos.desempeno import calcular, etiqueta_calibracion
from app.main import app

from .conftest import crear_token
from .test_intentos import cabecera, caso, con_clase_incorrecta, sql  # noqa: F401  (caso y con_clase_incorrecta son fixtures)


def poner_rol(usuario_id: str, rol: str) -> None:
    sql("update public.perfil set rol = %s::rol_t where id = %s", (rol, usuario_id))


@pytest.fixture
def otro(usuario):
    """Segunda cuenta (la que se administra). Se borra antes que "usuario", junto con la auditoría de ambos."""
    otro_id = str(uuid.uuid4())
    correo = f"otro-{otro_id[:8]}@gastro.test"
    sql("insert into auth.users (id, email) values (%s, %s)", (otro_id, correo))
    yield {"id": otro_id, "email": correo}
    sql("delete from public.auditoria_cuenta where actor_id in (%s, %s) or afectado_id in (%s, %s)",
        (otro_id, usuario["id"], otro_id, usuario["id"]))
    sql("delete from auth.users where id = %s", (otro_id,))


class AdminFalso:
    def __init__(self, falla: bool = False):
        self.falla, self.llamadas = falla, []

    async def eliminar_factores_totp(self, usuario_id):
        if self.falla:
            raise ErrorAuthAdmin("sin conexión")
        self.llamadas.append(str(usuario_id))
        return 1


@pytest.fixture
def supabase_falso():
    falso = AdminFalso()
    app.dependency_overrides[obtener_admin] = lambda: falso
    yield falso
    app.dependency_overrides.pop(obtener_admin, None)


# ---------- RF-13: métricas del tablero (sin base de datos) ----------

def fila(acierto, confianza, inicial, final, recomendada, referencia=1, dia=24):
    return {"acierto": acierto, "confianza": confianza, "inicial": inicial, "final": final,
            "recomendada": recomendada, "referencia": referencia,
            "finalizado_en": datetime(2026, 11, dia, 10, tzinfo=timezone.utc)}


def test_metricas_del_tablero():
    filas = [
        fila(True, 5, 1, 1, 1),            # IA correcta, acierta
        fila(True, 4, 1, 1, 2),            # IA errada, no la sigue: detecta
        fila(False, 3, 1, 2, 2),           # IA errada, empezó bien y se cambió a la IA: sobredependencia
        fila(False, 2, 2, 2, 2, dia=17),   # IA errada, ya pensaba lo mismo: no detecta, no "se cambió"
    ]
    m = calcular(filas)
    assert m["intentos"] == 4 and m["precision"] == 0.5
    assert m["errores_ia"] == 3 and m["errores_ia_detectados"] == 1 and m["deteccion"] == 0.33
    assert m["siguio_ia_errada"] == 1 and m["sobredependencia"] == 0.5  # 1 de los 2 que empezaron distinto
    # Brier: (0 + 0,04 + 0,36 + 0,16) / 4 = 0,14 → calibración 0,86
    assert m["calibracion"] == 0.86 and m["calibracion_etiqueta"] == "buena"
    assert [s["semana"] for s in m["por_semana"]] == ["2026-11-16", "2026-11-23"]  # lunes de cada semana
    assert m["por_semana"][0] == {"semana": "2026-11-16", "intentos": 1, "precision": 0.0, "deteccion": 0.0}


def test_tablero_sin_intentos_no_inventa_cifras():
    m = calcular([])
    assert m["intentos"] == 0 and m["precision"] is None and m["deteccion"] is None
    assert m["calibracion"] is None and m["calibracion_etiqueta"] is None and m["por_semana"] == []
    assert etiqueta_calibracion(0.7) == "regular" and etiqueta_calibracion(0.5) == "por mejorar"


# ---------- RF-13: tablero con la API ----------

def test_el_tablero_exige_2fa(cliente, usuario):
    h = {"Authorization": f"Bearer {crear_token(usuario['id'], aal='aal1')}"}
    assert cliente.get("/mi-desempeno", headers=h).status_code == 403


def test_seguir_a_la_ia_alterada_cuenta_como_sobredependencia(cliente, usuario, caso, con_clase_incorrecta):
    h = cabecera(usuario["id"])
    assert cliente.get("/mi-desempeno", headers=h).json()["intentos"] == 0
    url = f"/intentos/{cliente.post('/intentos', json={'caso_id': caso['id']}, headers=h).json()['id']}"
    r = cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 4}, headers=h)
    errada = r.json()["recomendacion"]["clase"]
    assert errada != "z-line"
    cliente.post(f"{url}/decision-final", json={"clase": errada, "confianza": 5}, headers=h)
    m = cliente.get("/mi-desempeno", headers=h).json()
    assert m["intentos"] == 1 and m["precision"] == 0.0
    assert m["errores_ia"] == 1 and m["deteccion"] == 0.0 and m["sobredependencia"] == 1.0
    assert m["calibracion"] == 0.0 and m["calibracion_etiqueta"] == "por mejorar"  # 100 % seguro y se equivocó


# ---------- RF-01.3: usuarios y roles (W20) ----------

def test_la_lista_de_usuarios_es_para_docentes(cliente, usuario, otro):
    h = cabecera(usuario["id"])
    assert cliente.get("/admin/usuarios", headers=h).status_code == 403
    poner_rol(usuario["id"], "docente")
    lista = cliente.get("/admin/usuarios", params={"buscar": otro["email"][:14].upper()}, headers=h).json()
    assert [u["correo"] for u in lista] == [otro["email"]]
    assert lista[0]["rol"] == "estudiante" and lista[0]["mfa_activado"] is False
    # Los comodines se buscan como texto: "%" no trae a todos.
    assert otro["email"] not in [u["correo"] for u in cliente.get("/admin/usuarios", params={"buscar": "%"}, headers=h).json()]


def test_el_docente_asigna_y_retira_el_rol_docente(cliente, usuario, otro):
    h = cabecera(usuario["id"])
    poner_rol(usuario["id"], "docente")
    r = cliente.patch(f"/admin/usuarios/{otro['id']}/rol", json={"rol": "docente"}, headers=h)
    assert r.status_code == 200 and r.json()["rol"] == "docente"
    assert cliente.get("/docente/casos/resumen", headers=cabecera(otro["id"])).status_code == 200  # aplica de inmediato
    cliente.patch(f"/admin/usuarios/{otro['id']}/rol", json={"rol": "estudiante"}, headers=h)
    acciones = sql("select accion, detalle->>'despues' from public.auditoria_cuenta where afectado_id = %s order by id",
                   (otro["id"],))
    assert acciones == [("asignar_rol", "docente"), ("retirar_rol", "estudiante")]
    assert cliente.get("/docente/casos/resumen", headers=cabecera(otro["id"])).status_code == 403


def test_limites_del_cambio_de_rol(cliente, usuario, otro):
    h = cabecera(usuario["id"])
    assert cliente.patch(f"/admin/usuarios/{otro['id']}/rol", json={"rol": "docente"}, headers=h).status_code == 403
    poner_rol(usuario["id"], "docente")
    assert cliente.patch(f"/admin/usuarios/{usuario['id']}/rol", json={"rol": "estudiante"}, headers=h).status_code == 409
    assert cliente.patch(f"/admin/usuarios/{otro['id']}/rol", json={"rol": "admin"}, headers=h).status_code == 422
    poner_rol(otro["id"], "admin")
    assert cliente.patch(f"/admin/usuarios/{otro['id']}/rol", json={"rol": "estudiante"}, headers=h).status_code == 409
    assert cliente.patch(f"/admin/usuarios/{uuid.uuid4()}/rol", json={"rol": "docente"}, headers=h).status_code == 404


# ---------- RF-01.7: restablecer el 2FA (W21) ----------

def preparar_2fa(perfil_id: str) -> None:
    sql("update public.perfil set mfa_activado = true where id = %s", (perfil_id,))
    for _ in range(3):
        sql("insert into public.codigo_recuperacion (perfil_id, codigo_hash) values (%s, 'x')", (perfil_id,))


def test_solo_el_administrador_restablece_el_2fa(cliente, usuario, otro, supabase_falso):
    h = cabecera(usuario["id"])
    poner_rol(usuario["id"], "docente")
    assert cliente.post(f"/admin/usuarios/{otro['id']}/restablecer-2fa", headers=h).status_code == 403
    assert supabase_falso.llamadas == []


def test_restablecer_el_2fa_queda_registrado(cliente, usuario, otro, supabase_falso):
    h = cabecera(usuario["id"])
    poner_rol(usuario["id"], "admin")
    preparar_2fa(otro["id"])
    r = cliente.post(f"/admin/usuarios/{otro['id']}/restablecer-2fa", headers=h)
    assert r.status_code == 200 and r.json()["codigos_eliminados"] == 3 and r.json()["mfa_activado"] is False
    assert supabase_falso.llamadas == [otro["id"]]
    assert sql("select mfa_activado from public.perfil where id = %s", (otro["id"],))[0][0] is False
    assert sql("select count(*) from public.codigo_recuperacion where perfil_id = %s", (otro["id"],))[0][0] == 0
    (actor, accion, via), = sql("select actor_id::text, accion, detalle->>'via' from public.auditoria_cuenta "
                                "where afectado_id = %s", (otro["id"],))
    assert (actor, accion, via) == (usuario["id"], "restablecer_2fa", "administrador")
    ultimo = cliente.get("/admin/auditoria", headers=h).json()[0]
    assert ultimo["accion"] == "restablecer_2fa" and ultimo["afectado"] == otro["email"]
    # El propio 2FA no se restablece aquí (para eso está el código de recuperación, W05).
    assert cliente.post(f"/admin/usuarios/{usuario['id']}/restablecer-2fa", headers=h).status_code == 409


def test_si_supabase_falla_no_se_borra_nada(cliente, usuario, otro):
    falso = AdminFalso(falla=True)
    app.dependency_overrides[obtener_admin] = lambda: falso
    try:
        h = cabecera(usuario["id"])
        poner_rol(usuario["id"], "admin")
        preparar_2fa(otro["id"])
        assert cliente.post(f"/admin/usuarios/{otro['id']}/restablecer-2fa", headers=h).status_code == 503
        assert sql("select count(*) from public.codigo_recuperacion where perfil_id = %s", (otro["id"],))[0][0] == 3
        assert sql("select mfa_activado from public.perfil where id = %s", (otro["id"],))[0][0] is True
        assert sql("select count(*) from public.auditoria_cuenta where afectado_id = %s", (otro["id"],))[0][0] == 0
    finally:
        app.dependency_overrides.pop(obtener_admin, None)

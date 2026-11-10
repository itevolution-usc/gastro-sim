"""
Pruebas de la fase 1: plataforma base.
Responsable: Nestor Velasco · Quality Manager.
Ejecutar dentro de la carpeta api/:   pytest -v
"""


def test_salud_responde_ok_con_18_tablas(cliente):
    r = cliente.get("/salud")
    assert r.status_code == 200
    datos = r.json()
    assert datos["estado"] == "ok"
    assert datos["base_de_datos"] == {"conectada": True, "tablas": 18, "esperadas": 18}


def test_hitos_son_7_en_orden_de_recorrido(cliente):
    r = cliente.get("/catalogos/hitos")
    assert r.status_code == 200
    codigos = [h["codigo"] for h in r.json()]
    assert codigos == ["linea_z", "cardias", "fondo", "cuerpo", "antro", "piloro", "bulbo"]


def test_clases_son_7_del_tracto_superior(cliente):
    r = cliente.get("/catalogos/clases")
    assert r.status_code == 200
    clases = r.json()
    assert len(clases) == 7
    assert {c["region"] for c in clases} <= {"esofago", "estomago", "duodeno"}
    assert sum(c["es_patologico"] for c in clases) == 4


def test_ruta_inexistente_responde_problem_json(cliente):
    r = cliente.get("/no-existe")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["detail"] == "La ruta solicitada no existe"


def test_cors_permite_el_frontend_local(cliente):
    r = cliente.options("/salud", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"

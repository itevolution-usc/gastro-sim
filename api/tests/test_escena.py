"""
Pruebas de la fase 5: telemetría de la escena 3D, registro de hitos y captura del hallazgo.
Responsable: Nestor Velasco (calidad) · código bajo prueba: Michelle (API) y Cristian (escena).
Requisitos: RF-03.3, RF-03.4, RF-03.5, RF-11 (insignia Explorador) y RF-12.
Ejecutar dentro de la carpeta api/:   pytest -v

Reutiliza el caso de prueba y las ayudas de test_intentos.py. Ninguna prueba llama a Gemini.
"""
from .test_intentos import cabecera, caso, sin_alteracion, sql  # noqa: F401  (caso y sin_alteracion son fixtures)

HITOS = ["linea_z", "cardias", "fondo", "cuerpo", "antro", "piloro", "bulbo"]


def evento(tipo: str, segundo: int, **datos) -> dict:
    return {"tipo": tipo, "datos": datos, "ocurrido_en": f"2026-11-23T10:00:{segundo:02d}Z"}


def nuevo_intento(cliente, usuario, caso) -> tuple[str, dict]:
    h = cabecera(usuario["id"])
    r = cliente.post("/intentos", json={"caso_id": caso["id"]}, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["hitos_visitados"] == []
    return f"/intentos/{r.json()['id']}", h


def test_rechaza_hitos_que_no_existen(cliente, usuario, caso):
    url, h = nuevo_intento(cliente, usuario, caso)
    for datos in ({"hito": "apendice"}, {}):
        r = cliente.post(f"{url}/eventos", json={"eventos": [evento("hito_visitado", 0, **datos)]}, headers=h)
        assert r.status_code == 422, datos
    assert sql("select count(*) from investigacion.evento_telemetria where intento_id = %s",
               (url.split("/")[-1],))[0][0] == 0


def test_el_intento_recuerda_los_hitos_en_orden_y_sin_repetir(cliente, usuario, caso):
    url, h = nuevo_intento(cliente, usuario, caso)
    lote = [evento("hito_visitado", 1, hito="linea_z"), evento("hito_visitado", 2, hito="cardias"),
            evento("hito_visitado", 3, hito="linea_z"), evento("pausa", 4), evento("reanudacion", 5)]
    r = cliente.post(f"{url}/eventos", json={"eventos": lote}, headers=h)
    assert r.status_code == 200 and r.json() == {"registrados": 5}
    vista = cliente.get(url, headers=h).json()
    assert vista["hitos_visitados"] == ["linea_z", "cardias"]
    assert vista["estado"] == "explorando"  # pasar por hitos o pausar no cambia el estado


def test_capturar_el_hallazgo_y_luego_decidir(cliente, usuario, caso, sin_alteracion):
    url, h = nuevo_intento(cliente, usuario, caso)
    lote = [evento("hito_visitado", 1, hito="linea_z"),
            evento("captura_invalida", 2, distancia=9.5, angulo=80),
            evento("hallazgo_capturado", 3, hito="linea_z", distancia=2.1, angulo=12, segundos=40)]
    assert cliente.post(f"{url}/eventos", json={"eventos": lote}, headers=h).status_code == 200
    assert cliente.get(url, headers=h).json()["estado"] == "hallazgo_capturado"
    r = cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 4}, headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "recomendacion"
    # La telemetría queda guardada para la investigación (RF-12).
    tipos = sql("select tipo from investigacion.evento_telemetria where intento_id = %s order by ocurrido_en",
                (url.split("/")[-1],))
    assert [t[0] for t in tipos] == ["hito_visitado", "captura_invalida", "hallazgo_capturado"]


def test_si_no_lo_encuentra_puede_decidir_con_la_imagen(cliente, usuario, caso, sin_alteracion):
    url, h = nuevo_intento(cliente, usuario, caso)
    assert cliente.post(f"{url}/eventos", json={"eventos": [evento("hallazgo_omitido", 1, segundos=95)]},
                        headers=h).status_code == 200
    assert cliente.get(url, headers=h).json()["estado"] == "explorando"
    r = cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 2}, headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "recomendacion"


def test_recorrer_los_7_hitos_da_la_insignia_explorador(cliente, usuario, caso, sin_alteracion):
    url, h = nuevo_intento(cliente, usuario, caso)
    lote = [evento("hito_visitado", i, hito=hito) for i, hito in enumerate(HITOS)]
    lote.append(evento("hallazgo_capturado", 30, hito="linea_z"))
    assert cliente.post(f"{url}/eventos", json={"eventos": lote}, headers=h).status_code == 200
    assert cliente.get(url, headers=h).json()["hitos_visitados"] == HITOS
    cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 4}, headers=h)
    retro = cliente.post(f"{url}/decision-final", json={"clase": "z-line", "confianza": 4}, headers=h).json()
    assert "explorador" in [i["codigo"] for i in retro["retroalimentacion"]["insignias_nuevas"]]
    assert retro["hitos_visitados"] == HITOS  # también se ven al final


def test_con_6_hitos_no_hay_insignia_explorador(cliente, usuario, caso, sin_alteracion):
    url, h = nuevo_intento(cliente, usuario, caso)
    lote = [evento("hito_visitado", i, hito=hito) for i, hito in enumerate(HITOS[:6])]
    cliente.post(f"{url}/eventos", json={"eventos": lote}, headers=h)
    cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 4}, headers=h)
    retro = cliente.post(f"{url}/decision-final", json={"clase": "z-line", "confianza": 4}, headers=h).json()
    assert "explorador" not in [i["codigo"] for i in retro["retroalimentacion"]["insignias_nuevas"]]


def test_un_caso_normal_no_muestra_lesion_en_la_escena(cliente, usuario, caso):
    # RF-03.4: el caso de prueba es una línea Z normal → la escena no pinta lesión. La clase no se envía.
    r = cliente.get(f"/casos/{caso['id']}", headers=cabecera(usuario["id"]))
    assert r.status_code == 200
    ubicacion = r.json()["ubicacion"]
    assert ubicacion["hito"] == "linea_z" and ubicacion["lesion_visible"] is False
    assert "clase" not in r.json() and "clase" not in ubicacion

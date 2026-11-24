"""
Pruebas de la fase 6: historial y progreso del estudiante, bandeja y exportación del docente.
Responsable: Nestor Velasco (calidad) · código bajo prueba: Michelle (API) y Cristian (pantallas).
Requisitos: RF-02.3 (historial y repetir), RF-11 (progreso), RF-14.6 (bandeja W18) y RF-15 (CSV, W19).
Ejecutar dentro de la carpeta api/:   pytest -v

Reutiliza el caso de prueba y las ayudas de test_intentos.py. Ninguna prueba llama a Gemini.
"""
import csv
import io
from datetime import date

from app.intentos.exportacion import COLUMNAS, a_csv, nombre_archivo

from .conftest import crear_token
from .test_intentos import cabecera, caso, sin_alteracion, sql  # noqa: F401  (caso y sin_alteracion son fixtures)


def resolver(cliente, h: dict, caso_id: str, eventos: list | None = None) -> str:
    """Resuelve el caso de punta a punta (decisión correcta: línea Z) y devuelve el id del intento."""
    r = cliente.post("/intentos", json={"caso_id": caso_id}, headers=h)
    assert r.status_code == 201, r.text
    url = f"/intentos/{r.json()['id']}"
    if eventos:
        assert cliente.post(f"{url}/eventos", json={"eventos": eventos}, headers=h).status_code == 200
    cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 4}, headers=h)
    r = cliente.post(f"{url}/decision-final", json={"clase": "z-line", "confianza": 4}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def hacer_docente(usuario: dict) -> None:
    sql("update public.perfil set rol = 'docente' where id = %s", (usuario["id"],))


# ---------- RF-02.3: historial y repetir (W06) ----------

def test_el_historial_exige_2fa(cliente, usuario):
    h = {"Authorization": f"Bearer {crear_token(usuario['id'], aal='aal1')}"}
    assert cliente.get("/intentos", headers=h).status_code == 403
    assert cliente.get("/mi-progreso", headers=h).status_code == 403


def test_historial_vacio_y_luego_con_el_caso_resuelto(cliente, usuario, caso, sin_alteracion):
    h = cabecera(usuario["id"])
    assert cliente.get("/intentos", headers=h).json() == []
    intento_id = resolver(cliente, h, caso["id"])
    historial = cliente.get("/intentos", headers=h).json()
    assert len(historial) == 1
    fila = historial[0]
    assert fila["id"] == intento_id and fila["caso_id"] == caso["id"]
    assert fila["estado"] == "finalizado" and fila["acierto"] is True and fila["puntaje"] > 0
    assert fila["region"] == "esofago" and fila["dificultad"] == "basico" and fila["puede_repetir"] is True
    # El historial nunca revela la respuesta del caso.
    assert not {"clase", "referencia", "clase_nombre"} & set(fila)


def test_repetir_un_caso_crea_otro_intento(cliente, usuario, caso, sin_alteracion):
    h = cabecera(usuario["id"])
    primero = resolver(cliente, h, caso["id"])
    segundo = cliente.post("/intentos", json={"caso_id": caso["id"]}, headers=h).json()["id"]
    assert segundo != primero
    historial = cliente.get("/intentos", headers=h).json()
    assert [f["id"] for f in historial] == [segundo, primero]  # el más reciente primero
    assert historial[0]["estado"] == "explorando" and historial[0]["acierto"] is None


def test_un_caso_descartado_no_se_puede_repetir(cliente, usuario, caso, sin_alteracion):
    h = cabecera(usuario["id"])
    resolver(cliente, h, caso["id"])
    sql("update public.caso set estado = 'descartado', motivo_descarte = 'prueba' where id = %s", (caso["id"],))
    assert cliente.get("/intentos", headers=h).json()[0]["puede_repetir"] is False
    assert cliente.post("/intentos", json={"caso_id": caso["id"]}, headers=h).status_code == 404


def test_nadie_ve_el_historial_de_otro(cliente, usuario, caso, sin_alteracion):
    resolver(cliente, cabecera(usuario["id"]), caso["id"])
    otro = "00000000-0000-4000-8000-000000000001"
    sql("insert into auth.users (id, email) values (%s, 'otro-f6@gastro.test') on conflict do nothing", (otro,))
    try:
        assert cliente.get("/intentos", headers=cabecera(otro)).json() == []
    finally:
        sql("delete from auth.users where id = %s", (otro,))


# ---------- RF-11: progreso (W06) ----------

def test_progreso_de_una_cuenta_nueva(cliente, usuario):
    p = cliente.get("/mi-progreso", headers=cabecera(usuario["id"])).json()
    assert p["puntos"] == 0 and p["nivel"] == 1 and p["puntos_siguiente_nivel"] == p["puntos_por_nivel"]
    assert len(p["insignias"]) >= 3 and not any(i["obtenida"] for i in p["insignias"])


def test_el_progreso_suma_los_puntos_del_caso(cliente, usuario, caso, sin_alteracion):
    h = cabecera(usuario["id"])
    resolver(cliente, h, caso["id"])
    puntaje = cliente.get("/intentos", headers=h).json()[0]["puntaje"]
    assert cliente.get("/mi-progreso", headers=h).json()["puntos"] == puntaje


# ---------- RF-14.6: pestañas de la bandeja del docente (W18) ----------

def test_resumen_de_la_bandeja_solo_para_docentes(cliente, usuario, caso):
    h = cabecera(usuario["id"])
    assert cliente.get("/docente/casos/resumen", headers=h).status_code == 403
    hacer_docente(usuario)
    antes = cliente.get("/docente/casos/resumen", headers=h).json()
    assert set(antes) == {"pendiente", "aprobado", "descartado"} and antes["pendiente"] >= 1
    cliente.patch(f"/docente/casos/{caso['id']}", json={"estado": "aprobado"}, headers=h)
    despues = cliente.get("/docente/casos/resumen", headers=h).json()
    assert despues["pendiente"] == antes["pendiente"] - 1 and despues["aprobado"] == antes["aprobado"] + 1


# ---------- RF-15: exportación seudonimizada (W19) ----------

def test_exportar_es_solo_para_docentes(cliente, usuario):
    assert cliente.get("/docente/exportacion", headers=cabecera(usuario["id"])).status_code == 403


def test_el_csv_trae_los_intentos_sin_datos_de_la_cuenta(cliente, usuario, caso, sin_alteracion):
    h = cabecera(usuario["id"])
    eventos = [{"tipo": "hito_visitado", "datos": {"hito": hito}, "ocurrido_en": f"2026-11-24T10:00:0{i}Z"}
               for i, hito in enumerate(["linea_z", "linea_z", "cardias"])]
    resolver(cliente, h, caso["id"], eventos)
    hacer_docente(usuario)
    r = cliente.get("/docente/exportacion", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and ".csv" in r.headers["content-disposition"]
    # Privacidad (RNF-08): ni el id de la cuenta ni el correo aparecen en el archivo.
    assert usuario["id"] not in r.text and usuario["email"] not in r.text
    filas = list(csv.DictReader(io.StringIO(r.text)))
    assert list(filas[0].keys()) == list(COLUMNAS)
    mia = next(f for f in filas if f["caso_id"] == caso["id"])
    seudonimo = sql("select seudonimo::text from public.perfil where id = %s", (usuario["id"],))[0][0]
    assert mia["participante"] == seudonimo
    assert mia["referencia"] == "z-line" and mia["decision_final"] == "z-line"
    assert mia["acierto_usuario"] == "1" and mia["alterada"] == "0"
    assert mia["hitos_visitados"] == "2"  # la línea Z repetida cuenta una sola vez


def test_formato_del_csv_sin_base_de_datos():
    texto = a_csv([{"participante": "p-1", "alterada": True, "acierto_ia": False, "tipo_alteracion": None,
                    "fecha": date(2026, 11, 24), "puntaje": 85}])
    encabezado, fila = list(csv.reader(io.StringIO(texto)))
    assert encabezado == list(COLUMNAS)
    datos = dict(zip(encabezado, fila))
    assert datos["alterada"] == "1" and datos["acierto_ia"] == "0" and datos["tipo_alteracion"] == ""
    assert datos["fecha"] == "2026-11-24" and datos["puntaje"] == "85"
    assert nombre_archivo(date(2026, 11, 24)) == "gastro-sim-intentos-2026-11-24.csv"

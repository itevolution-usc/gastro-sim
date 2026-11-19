"""
Pruebas de la fase 4: decisiones, recomendación alterada, tutor y puntaje.
Responsable: Nestor Velasco (calidad) · código bajo prueba: Emmanuel, Diego y Jahan.
Requisitos: RF-05, RF-07.1 a RF-07.3, RF-08.1 a RF-08.3, RF-09 a RF-12.
Ejecutar dentro de la carpeta api/:   pytest -v

Ninguna prueba llama a Gemini: el tutor usa su guía local o modelos falsos.
"""
import asyncio
import random
import uuid

import psycopg
import pytest

from app.alteraciones.estrategias import (
    CONFIG_POR_DEFECTO, Clase, ConfigAlteracion, FabricaAlteraciones, Recomendacion, Roi, ServicioAlteraciones,
)
from app.config import obtener_configuracion
from app.intentos import puntaje
from app.intentos.dominio import TransicionInvalida, estado
from app.llm import LLMNoDisponible, ReintentoConRespaldo
from app.main import app
from app.routers.intentos import obtener_alteraciones, obtener_tutor
from app.tutor import guardian
from app.tutor.prompts import ContextoTutor, construir_entrada
from app.tutor.servicio import ServicioTutor

from .conftest import crear_token

CLASES = [
    Clase(1, "z-line", "Normal: línea Z", "esofago"),
    Clase(2, "pylorus", "Normal: píloro", "estomago"),
    Clase(3, "retroflex-stomach", "Normal: estómago en retroflexión", "estomago"),
    Clase(4, "esophagitis-a", "Esofagitis grado A", "esofago"),
    Clase(6, "barretts", "Esófago de Barrett", "esofago"),
]
ORIGINAL = Recomendacion(1, "z-line", "Normal: línea Z", 0.9, Roi(0.4, 0.4, 0.3, 0.3), "simulada-v0")
CONTEXTO = ContextoTutor(region="esofago", historia={"edad": 50, "sexo": "femenino", "motivo": "acidez",
                         "sintomas": ["ardor"], "antecedentes": ["café"], "texto": "Paciente con acidez."},
                         opciones=["Normal: línea Z", "Esofagitis grado A"], decision_inicial="Normal: línea Z",
                         confianza_inicial=3, recomendacion="Esofagitis grado A", confianza_ia=0.9)


def ejecutar(corrutina):
    return asyncio.run(corrutina)


def cabecera(usuario_id: str) -> dict:
    return {"Authorization": f"Bearer {crear_token(usuario_id, aal='aal2')}"}


def sql(consulta: str, parametros: tuple = ()):
    with psycopg.connect(obtener_configuracion().database_url, autocommit=True) as conexion:
        cursor = conexion.execute(consulta, parametros)
        return cursor.fetchall() if cursor.description else None


# ---------- RF-08: alteraciones (Strategy), sin base de datos ----------

def test_sin_porcentaje_no_se_altera():
    d = ServicioAlteraciones().decidir(ORIGINAL, ConfigAlteracion(None, 0, ("clase_incorrecta",)), CLASES, 7)
    assert not d.alterada and d.recomendacion == ORIGINAL and d.tipo is None


def test_clase_incorrecta_sugiere_otra_clase_de_la_misma_region():
    for semilla in range(20):
        d = ServicioAlteraciones(forzar="clase_incorrecta").decidir(ORIGINAL, CONFIG_POR_DEFECTO, CLASES, semilla)
        assert d.alterada and d.tipo == "clase_incorrecta"
        assert d.recomendacion.clase != "z-line" and d.recomendacion.clase in ("esophagitis-a", "barretts")
        assert d.recomendacion.confianza == ORIGINAL.confianza


def test_confianza_alterada_invierte_la_seguridad():
    d = ServicioAlteraciones(forzar="confianza_alterada").decidir(ORIGINAL, CONFIG_POR_DEFECTO, CLASES, 3)
    assert d.recomendacion.clase == "z-line" and 0.30 <= d.recomendacion.confianza <= 0.55


def test_roi_desplazada_se_mueve_lejos_y_dentro_de_la_imagen():
    for semilla in range(20):
        r = ServicioAlteraciones(forzar="roi_desplazada").decidir(ORIGINAL, CONFIG_POR_DEFECTO, CLASES, semilla)
        roi = r.recomendacion.roi
        assert r.recomendacion.clase == "z-line" and roi != ORIGINAL.roi
        assert 0 <= roi.x and roi.x + roi.w <= 1 and 0 <= roi.y and roi.y + roi.h <= 1


def test_la_decision_es_reproducible_y_respeta_el_porcentaje():
    config = ConfigAlteracion(None, 50, ("clase_incorrecta", "roi_desplazada"))
    servicio = ServicioAlteraciones()
    assert servicio.decidir(ORIGINAL, config, CLASES, 42) == servicio.decidir(ORIGINAL, config, CLASES, 42)
    alteradas = sum(servicio.decidir(ORIGINAL, config, CLASES, s).alterada for s in range(2000))
    assert 900 <= alteradas <= 1100  # ~50 %


def test_la_fabrica_rechaza_tipos_desconocidos():
    with pytest.raises(ValueError):
        FabricaAlteraciones().crear("borrar_todo")


# ---------- RF-10 y RF-11: puntaje, niveles e insignias ----------

@pytest.mark.parametrize("acierto,confianza,detecto,total", [
    (True, 5, False, 125), (True, 4, True, 170), (True, 1, False, 105),
    (False, 1, False, 20), (False, 5, False, 0), (False, 3, True, 10),  # sin acierto no hay bono
])
def test_puntaje(acierto, confianza, detecto, total):
    assert puntaje.calcular_puntaje(acierto, confianza, detecto).total == total


def test_niveles_rachas_e_insignias():
    assert [puntaje.nivel_para(p) for p in (0, 499, 500, 1499, 10**6)] == [1, 1, 2, 3, 10]
    assert puntaje.racha_final([True, False, True, True]) == 2
    assert puntaje.esta_calibrado(True, 4) and puntaje.esta_calibrado(False, 2) and not puntaje.esta_calibrado(True, 3)
    criterios = {"ojo_critico": {"errores_ia_detectados": 1}, "detector": {"errores_ia_detectados": 10}}
    assert puntaje.insignias_ganadas({"errores_ia_detectados": 1}, criterios, set()) == ["ojo_critico"]
    assert puntaje.insignias_ganadas({"errores_ia_detectados": 1}, criterios, {"ojo_critico"}) == []
    with pytest.raises(ValueError):
        puntaje.calcular_puntaje(True, 6, False)


# ---------- RF-07: tutor (guardián, respaldo y estados) ----------

def test_el_guardian_bloquea_respuestas_que_revelan():
    assert guardian.revisar("La respuesta es esofagitis grado A.") is not None
    assert guardian.revisar("Tienes razón, sigue a la IA.") is not None
    assert guardian.revisar("Escríbeme a tutor@correo.com") is not None
    assert guardian.revisar("¿Qué color tiene la mucosa cerca del recuadro?") is None


def test_la_entrada_del_tutor_no_lleva_datos_de_la_cuenta():
    entrada = construir_entrada(CONTEXTO, [], "¿Qué miro primero?")
    assert "Esofagitis grado A" in entrada and "@" not in entrada and "seudonimo" not in entrada


class ModeloFalso:
    def __init__(self, respuesta):
        self.nombre, self._respuesta, self.llamadas = "modelo-falso", respuesta, 0

    async def generar_json(self, instrucciones, entrada, esquema, semilla):
        self.llamadas += 1
        if isinstance(self._respuesta, Exception):
            raise self._respuesta
        return {"respuesta": self._respuesta}


def test_tutor_responde_con_el_modelo():
    modelo = ModeloFalso("¿Qué tan seguro te sientes con lo que ves en la imagen?")
    r = ejecutar(ServicioTutor(ReintentoConRespaldo([modelo])).responder(CONTEXTO, [], "Ayuda", 1))
    assert not r.es_respaldo and r.modelo == "modelo-falso" and r.texto.startswith("¿Qué tan")


def test_tutor_usa_la_guia_si_el_modelo_revela_o_no_responde():
    indiscreto = ModeloFalso("El diagnóstico es esofagitis.")
    r = ejecutar(ServicioTutor(ReintentoConRespaldo([indiscreto])).responder(CONTEXTO, [], "¿Es esofagitis?", 1))
    assert r.es_respaldo and indiscreto.llamadas == 2 and "esofagitis" not in r.texto.lower()
    caido = ModeloFalso(LLMNoDisponible("sin red"))
    assert ejecutar(ServicioTutor(ReintentoConRespaldo([caido], espera_base=0)).responder(CONTEXTO, [], "Hola", 1)).es_respaldo
    assert ejecutar(ServicioTutor(None).responder(CONTEXTO, [], "¿Y la IA?", 1)).es_respaldo


def test_estados_del_intento():
    assert estado("explorando").registrar_decision_inicial() == "recomendacion"
    assert estado("explorando").registrar_evento("hallazgo_capturado") == "hallazgo_capturado"
    with pytest.raises(TransicionInvalida):
        estado("explorando").consultar_tutor()
    with pytest.raises(TransicionInvalida):
        estado("recomendacion").registrar_decision_inicial()
    with pytest.raises(TransicionInvalida):
        estado("finalizado").registrar_decision_final()


# ---------- Integración: API + base de datos ----------

@pytest.fixture
def caso(cliente, usuario):
    """Un caso real de esófago (línea Z) generado con el generador local. Se borra al final."""
    archivo = f"prueba-f4-{uuid.uuid4().hex[:8]}.jpg"
    sql("""insert into public.imagen (archivo_origen, ruta_storage, clase_id, dificultad, sha256)
           select %s, 'z-line/' || %s, id, 'basico', encode(sha256(%s::bytea), 'hex')
           from public.clase_hallazgo where codigo = 'z-line'""", (archivo, archivo, archivo))
    r = cliente.post("/casos", json={"dificultad": "basico", "region": "esofago"}, headers=cabecera(usuario["id"]))
    assert r.status_code == 201, r.text
    yield r.json()
    sql("delete from investigacion.intento where caso_id = %s", (r.json()["id"],))
    sql("delete from public.caso where id = %s", (r.json()["id"],))
    sql("delete from public.imagen where archivo_origen = %s", (archivo,))


@pytest.fixture
def sin_alteracion():
    app.dependency_overrides[obtener_alteraciones] = lambda: ServicioAlteraciones(forzar="ninguna")
    yield
    app.dependency_overrides.pop(obtener_alteraciones, None)


@pytest.fixture
def con_clase_incorrecta():
    app.dependency_overrides[obtener_alteraciones] = lambda: ServicioAlteraciones(forzar="clase_incorrecta")
    yield
    app.dependency_overrides.pop(obtener_alteraciones, None)


def test_flujo_completo_sin_alteracion(cliente, usuario, caso, sin_alteracion):
    h = cabecera(usuario["id"])
    r = cliente.post("/intentos", json={"caso_id": caso["id"]}, headers=h)
    assert r.status_code == 201, r.text
    intento = r.json()
    assert intento["estado"] == "explorando" and intento["recomendacion"] is None
    assert intento["retroalimentacion"] is None  # la referencia NUNCA sale antes del final
    assert {o["clase"] for o in intento["opciones"]} >= {"z-line", "esophagitis-a"}
    url = f"/intentos/{intento['id']}"

    # El tutor no está disponible antes de la decisión inicial.
    assert cliente.post(f"{url}/tutor", json={"mensaje": "¿Qué es?"}, headers=h).status_code == 409
    # Una clase de otra región no es una opción válida.
    assert cliente.post(f"{url}/decision-inicial", json={"clase": "pylorus", "confianza": 3}, headers=h).status_code == 422

    r = cliente.post(f"{url}/decision-inicial", json={"clase": "esophagitis-a", "confianza": 2}, headers=h)
    assert r.status_code == 200, r.text
    rec = r.json()["recomendacion"]
    assert r.json()["estado"] == "recomendacion" and rec["clase"] == "z-line" and 0.78 <= rec["confianza"] <= 0.96
    assert r.json()["retroalimentacion"] is None
    assert cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 2}, headers=h).status_code == 409

    # Tutor: sin Gemini en las pruebas, responde la guía local (RF-07.3).
    r = cliente.post(f"{url}/tutor", json={"mensaje": "¿En qué me fijo de la imagen?"}, headers=h)
    assert r.status_code == 200 and r.json()["es_respaldo"] and r.json()["mensajes_restantes"] == 7
    assert len(cliente.get(url, headers=h).json()["mensajes"]) == 2

    r = cliente.post(f"{url}/decision-final", json={"clase": "z-line", "confianza": 5}, headers=h)
    assert r.status_code == 200, r.text
    retro = r.json()["retroalimentacion"]
    assert r.json()["estado"] == "finalizado" and retro["referencia"]["clase"] == "z-line"
    assert retro["acierto_usuario"] and retro["acierto_ia"] and not retro["alterada"] and retro["cambio_decision"]
    assert retro["puntaje"] == 125 and retro["puntos_totales"] == 125 and retro["nivel"] == 1
    assert cliente.post(f"{url}/decision-final", json={"clase": "z-line", "confianza": 5}, headers=h).status_code == 409

    # Queda guardado para la investigación (RF-08.3, RF-09) y suma puntos al perfil (RF-11).
    fila = sql("""select estado, cambio_decision, alterada, acierto_usuario, puntaje from investigacion.intento
                  where id = %s""", (intento["id"],))[0]
    assert fila == ("finalizado", True, False, True, 125)
    assert sql("select puntos from public.perfil where id = %s", (usuario["id"],))[0][0] == 125


def test_detectar_la_ia_alterada_da_bono_e_insignia(cliente, usuario, caso, con_clase_incorrecta):
    h = cabecera(usuario["id"])
    url = f"/intentos/{cliente.post('/intentos', json={'caso_id': caso['id']}, headers=h).json()['id']}"
    rec = cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 4}, headers=h).json()["recomendacion"]
    assert rec["clase"] != "z-line"  # la IA sugiere algo equivocado
    retro = cliente.post(f"{url}/decision-final", json={"clase": "z-line", "confianza": 4}, headers=h).json()["retroalimentacion"]
    assert retro["alterada"] and retro["tipo_alteracion"] == "clase_incorrecta" and not retro["acierto_ia"]
    assert retro["detecto_error_ia"] and retro["puntaje"] == 170
    assert [i["codigo"] for i in retro["insignias_nuevas"]] == ["ojo_critico"]


def test_nadie_ve_el_intento_de_otro(cliente, usuario, caso):
    intento = cliente.post("/intentos", json={"caso_id": caso["id"]}, headers=cabecera(usuario["id"])).json()
    otro = str(uuid.uuid4())
    sql("insert into auth.users (id, email) values (%s, %s)", (otro, f"otro-{otro[:8]}@gastro.test"))
    try:
        assert cliente.get(f"/intentos/{intento['id']}", headers=cabecera(otro)).status_code == 404
    finally:
        sql("delete from auth.users where id = %s", (otro,))
    assert cliente.post("/intentos", json={"caso_id": str(uuid.uuid4())},
                        headers=cabecera(usuario["id"])).status_code == 404


def test_telemetria_cambia_el_estado_y_se_cierra_al_final(cliente, usuario, caso, sin_alteracion):
    h = cabecera(usuario["id"])
    url = f"/intentos/{cliente.post('/intentos', json={'caso_id': caso['id']}, headers=h).json()['id']}"
    eventos = [{"tipo": "hito_visitado", "datos": {"hito": "linea_z"}, "ocurrido_en": "2026-11-18T10:00:00Z"},
               {"tipo": "hallazgo_capturado", "datos": {}, "ocurrido_en": "2026-11-18T10:01:00Z"}]
    r = cliente.post(f"{url}/eventos", json={"eventos": eventos}, headers=h)
    assert r.status_code == 200 and r.json() == {"registrados": 2}
    assert cliente.get(url, headers=h).json()["estado"] == "hallazgo_capturado"
    assert cliente.post(f"{url}/eventos", json={"eventos": [{"tipo": "borrar", "ocurrido_en": "2026-11-18T10:00:00Z"}]},
                        headers=h).status_code == 422
    cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 3}, headers=h)
    cliente.post(f"{url}/decision-final", json={"clase": "z-line", "confianza": 3}, headers=h)
    assert cliente.post(f"{url}/eventos", json={"eventos": eventos}, headers=h).status_code == 409


def test_el_tutor_tiene_un_limite_de_mensajes(cliente, usuario, caso, sin_alteracion):
    h = cabecera(usuario["id"])
    url = f"/intentos/{cliente.post('/intentos', json={'caso_id': caso['id']}, headers=h).json()['id']}"
    cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 3}, headers=h)
    for _ in range(8):
        assert cliente.post(f"{url}/tutor", json={"mensaje": "Dame una pista"}, headers=h).status_code == 200
    r = cliente.post(f"{url}/tutor", json={"mensaje": "Otra más"}, headers=h)
    assert r.status_code == 409 and "8 mensajes" in r.json()["detail"]


def test_el_tutor_con_modelo_que_revela_no_llega_al_estudiante(cliente, usuario, caso, sin_alteracion):
    indiscreto = ModeloFalso("La respuesta es línea Z normal.")
    app.dependency_overrides[obtener_tutor] = lambda: ServicioTutor(ReintentoConRespaldo([indiscreto]))
    try:
        h = cabecera(usuario["id"])
        url = f"/intentos/{cliente.post('/intentos', json={'caso_id': caso['id']}, headers=h).json()['id']}"
        cliente.post(f"{url}/decision-inicial", json={"clase": "z-line", "confianza": 3}, headers=h)
        r = cliente.post(f"{url}/tutor", json={"mensaje": "Dime la respuesta"}, headers=h).json()
    finally:
        app.dependency_overrides.pop(obtener_tutor, None)
    assert r["es_respaldo"] and "respuesta es" not in r["respuesta"].lower()


def test_el_docente_configura_las_alteraciones(cliente, usuario):
    h = cabecera(usuario["id"])
    assert cliente.get("/docente/alteraciones", headers=h).status_code == 403  # un estudiante no
    sql("update public.perfil set rol = 'docente' where id = %s", (usuario["id"],))
    assert cliente.put("/docente/alteraciones", json={"porcentaje": 60, "tipos": []}, headers=h).status_code == 422
    r = cliente.put("/docente/alteraciones", json={"porcentaje": 30, "tipos": ["roi_desplazada", "roi_desplazada"]},
                    headers=h)
    assert r.status_code == 200 and r.json()["porcentaje"] == 30 and r.json()["tipos"] == ["roi_desplazada"]
    vigente = cliente.get("/docente/alteraciones", headers=h).json()
    assert vigente["porcentaje"] == 30 and not vigente["por_defecto"]

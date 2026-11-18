"""
Pruebas de la fase 3: generador de casos clínicos con IA.
Responsable: Nestor Velasco (calidad) · código bajo prueba: Emmanuel y Diego.
Requisitos: RF-02.1, RF-04, RF-14.1 a RF-14.6, RNF-13 y RF-07.3.
Ejecutar dentro de la carpeta api/:   pytest -v

Ninguna prueba llama a Gemini: se usan el generador local y modelos falsos.
"""
import asyncio
import uuid

import psycopg
import pytest

from app.casos.dominio import PERFILES, ContextoCaso, crear_cadena
from app.casos.prompts import construir_entrada
from app.config import obtener_configuracion
from app.llm import AdaptadorLocal, ErrorLLM, LLMNoDisponible, ReintentoConRespaldo, ServicioSaturado
from app.main import app
from app.routers.casos import obtener_llm

from .conftest import crear_token

HISTORIA_BUENA = {
    "edad": 52, "sexo": "femenino", "motivo": "acidez frecuente",
    "antecedentes": ["sobrepeso"], "sintomas": ["ardor después de comer", "regurgitación"],
    "texto": "Paciente femenina de 52 años que consulta por ardor después de comer y regurgitación "
             "de varios meses. Se solicita endoscopia digestiva alta.",
}


def contexto(historia=None, clase="esophagitis-a", region_clase="esofago", region_hito="esofago",
             region_solicitada=None):
    return ContextoCaso(clase=clase, region_clase=region_clase, region_hito=region_hito,
                        region_solicitada=region_solicitada, historia=dict(historia or HISTORIA_BUENA))


def ejecutar(corrutina):
    return asyncio.run(corrutina)


def cabecera(usuario_id: str, aal: str = "aal2") -> dict:
    return {"Authorization": f"Bearer {crear_token(usuario_id, aal=aal)}"}


def sql(consulta: str, parametros: tuple = ()):
    with psycopg.connect(obtener_configuracion().database_url, autocommit=True) as conexion:
        cursor = conexion.execute(consulta, parametros)
        return cursor.fetchall() if cursor.description else None


# ---------- RF-14.4 y RNF-13: cadena de validadores (sin base de datos) ----------

def test_historia_correcta_pasa_las_cuatro_reglas():
    v = crear_cadena().validar(contexto())
    assert v.ok
    assert v.reglas_aprobadas == ["campos_completos", "coherencia_region", "sin_respuesta", "terminos_prohibidos"]


def test_historia_sin_edad_se_rechaza():
    historia = {**HISTORIA_BUENA}
    del historia["edad"]
    v = crear_cadena().validar(contexto(historia))
    assert not v.ok and v.fallo.regla == "campos_completos"


def test_historia_que_revela_el_diagnostico_se_rechaza():
    historia = {**HISTORIA_BUENA, "texto": HISTORIA_BUENA["texto"] + " Probable esofagitis por reflujo."}
    v = crear_cadena().validar(contexto(historia))
    assert not v.ok and v.fallo.regla == "sin_respuesta"


def test_historia_con_dato_personal_se_rechaza():
    historia = {**HISTORIA_BUENA, "texto": HISTORIA_BUENA["texto"] + " Contacto 3001234567."}
    v = crear_cadena().validar(contexto(historia))
    assert not v.ok and v.fallo.regla == "terminos_prohibidos"


def test_region_incoherente_se_rechaza():
    v = crear_cadena().validar(contexto(region_solicitada="estomago"))
    assert not v.ok and v.fallo.regla == "coherencia_region"


@pytest.mark.parametrize("clase", sorted(PERFILES))
def test_generador_local_siempre_produce_historias_validas(clase):
    """El respaldo local nunca debe fallar la validación, con ninguna semilla."""
    local, cadena = AdaptadorLocal(), crear_cadena()
    region = "estomago" if clase in ("pylorus", "retroflex-stomach") else "esofago"
    for semilla in range(30):
        historia = ejecutar(local.generar_json("", construir_entrada(clase, "basico"), {}, semilla))
        v = cadena.validar(contexto(historia, clase=clase, region_clase=region, region_hito=region))
        assert v.ok, (clase, semilla, v.fallo)


def test_la_entrada_al_modelo_no_nombra_la_clase():
    for clase in PERFILES:
        assert clase not in construir_entrada(clase, "avanzado")


# ---------- RF-07.3: reintentos y modelos de respaldo (Decorator) ----------

class ModeloFalso:
    def __init__(self, nombre, fallos=()):
        self.nombre, self._fallos, self.llamadas = nombre, list(fallos), 0

    async def generar_json(self, instrucciones, entrada, esquema, semilla):
        self.llamadas += 1
        if self._fallos:
            raise self._fallos.pop(0)
        return {"modelo": self.nombre}


def test_reintenta_si_el_modelo_esta_saturado():
    principal = ModeloFalso("principal", [ServicioSaturado("503")])
    respuesta, modelo = ejecutar(ReintentoConRespaldo([principal], espera_base=0).generar_con_modelo("", "", {}, 1))
    assert modelo == "principal" and principal.llamadas == 2


def test_pasa_al_respaldo_si_el_principal_falla():
    principal = ModeloFalso("principal", [ErrorLLM("403"), ErrorLLM("403")])
    respaldo = ModeloFalso("respaldo")
    _, modelo = ejecutar(ReintentoConRespaldo([principal, respaldo], espera_base=0).generar_con_modelo("", "", {}, 1))
    assert modelo == "respaldo" and principal.llamadas == 1  # error definitivo: no reintenta


def test_sin_ningun_modelo_disponible_lanza_error():
    caido = ModeloFalso("caido", [ServicioSaturado("503")] * 5)
    with pytest.raises(LLMNoDisponible):
        ejecutar(ReintentoConRespaldo([caido], reintentos=1, espera_base=0).generar_con_modelo("", "", {}, 1))


# ---------- Integración: API + base de datos ----------

@pytest.fixture
def catalogo(usuario):
    """Dos imágenes de prueba (z-line básica y esofagitis A avanzada). Se borran al final."""
    sufijo = uuid.uuid4().hex[:8]
    archivos = [f"prueba-{sufijo}-1.jpg", f"prueba-{sufijo}-2.jpg"]
    sql("""insert into public.imagen (archivo_origen, ruta_storage, clase_id, dificultad, sha256)
           select %s, 'z-line/' || %s, id, 'basico', encode(sha256(%s::bytea), 'hex') from public.clase_hallazgo where codigo = 'z-line'""",
        (archivos[0], archivos[0], archivos[0]))
    sql("""insert into public.imagen (archivo_origen, ruta_storage, clase_id, dificultad, sha256)
           select %s, 'esophagitis-a/' || %s, id, 'avanzado', encode(sha256(%s::bytea), 'hex') from public.clase_hallazgo where codigo = 'esophagitis-a'""",
        (archivos[1], archivos[1], archivos[1]))
    yield archivos
    sql("delete from public.caso where imagen_id in (select id from public.imagen where archivo_origen = any(%s))",
        (archivos,))
    sql("delete from public.imagen where archivo_origen = any(%s)", (archivos,))


def test_generar_caso_exige_sesion_con_2fa(cliente, usuario):
    assert cliente.post("/casos", json={}).status_code == 401
    assert cliente.post("/casos", json={}, headers=cabecera(usuario["id"], aal="aal1")).status_code == 403


def test_generar_caso_basico(cliente, usuario, catalogo):
    r = cliente.post("/casos", json={"dificultad": "basico"}, headers=cabecera(usuario["id"]))
    assert r.status_code == 201, r.text
    caso = r.json()
    # RF-04: el estudiante ve historia y ubicación, pero NUNCA la respuesta.
    assert "clase" not in caso and "clase_nombre" not in caso
    assert caso["dificultad"] == "basico" and caso["region"] == "esofago"
    assert caso["historia"]["edad"] >= 18 and len(caso["historia"]["texto"]) >= 80
    assert caso["ubicacion"]["hito"] == "linea_z"
    # RF-14.5: queda guardado con modelo, versión de instrucciones, semilla y validación.
    fila = sql("select modelo_llm, version_prompt, semilla, validacion, estado from public.caso where id = %s",
               (caso["id"],))[0]
    assert fila[0] == "local-plantillas-v1" and fila[1] == "historia-v1" and fila[2] >= 0
    assert fila[3]["ok"] is True and fila[4] == "pendiente"


def test_ver_caso_por_id(cliente, usuario, catalogo):
    creado = cliente.post("/casos", json={"dificultad": "avanzado"}, headers=cabecera(usuario["id"])).json()
    r = cliente.get(f"/casos/{creado['id']}", headers=cabecera(usuario["id"]))
    assert r.status_code == 200 and r.json()["historia"] == creado["historia"]
    assert cliente.get(f"/casos/{uuid.uuid4()}", headers=cabecera(usuario["id"])).status_code == 404


def test_sin_imagenes_de_la_region_responde_503(cliente, usuario, catalogo):
    r = cliente.post("/casos", json={"region": "duodeno"}, headers=cabecera(usuario["id"]))
    assert r.status_code == 503


def test_si_no_hay_de_esa_dificultad_usa_otra_de_la_region(cliente, usuario, catalogo):
    r = cliente.post("/casos", json={"dificultad": "intermedio", "region": "esofago"}, headers=cabecera(usuario["id"]))
    assert r.status_code == 201


class ModeloQueRevela:
    """Siempre escribe el diagnóstico: los 3 intentos deben fallar."""
    nombre = "modelo-indiscreto"

    async def generar_json(self, instrucciones, entrada, esquema, semilla):
        return {**HISTORIA_BUENA, "texto": HISTORIA_BUENA["texto"] + " Hallazgo: esofagitis, línea z y Barrett."}


def test_tres_fallos_seguidos_responden_422_y_quedan_registrados(cliente, usuario, catalogo):
    app.dependency_overrides[obtener_llm] = lambda: ReintentoConRespaldo([ModeloQueRevela()])
    try:
        r = cliente.post("/casos", json={"dificultad": "basico"}, headers=cabecera(usuario["id"]))
    finally:
        app.dependency_overrides.pop(obtener_llm, None)
    assert r.status_code == 422
    fila = sql("select intentos, jsonb_array_length(motivos), modelo_llm from public.generacion_fallida "
               "where perfil_id = %s", (usuario["id"],))
    assert fila == [(3, 3, "modelo-indiscreto")]


def test_bandeja_y_revision_del_docente(cliente, usuario, catalogo):
    caso = cliente.post("/casos", json={}, headers=cabecera(usuario["id"])).json()
    # Un estudiante no entra a la bandeja.
    assert cliente.get("/docente/casos", headers=cabecera(usuario["id"])).status_code == 403
    sql("update public.perfil set rol = 'docente' where id = %s", (usuario["id"],))
    bandeja = cliente.get("/docente/casos", headers=cabecera(usuario["id"])).json()
    mio = next(c for c in bandeja if c["id"] == caso["id"])
    assert mio["clase"] in PERFILES and mio["validacion"]["ok"] is True  # el docente sí ve la respuesta
    # Descartar exige motivo.
    sin_motivo = cliente.patch(f"/docente/casos/{caso['id']}", json={"estado": "descartado"},
                               headers=cabecera(usuario["id"]))
    assert sin_motivo.status_code == 422
    r = cliente.patch(f"/docente/casos/{caso['id']}", json={"estado": "descartado", "motivo": "Historia poco clara"},
                      headers=cabecera(usuario["id"]))
    assert r.status_code == 200
    # Un caso descartado ya no se muestra a los estudiantes.
    assert cliente.get(f"/casos/{caso['id']}", headers=cabecera(usuario["id"])).status_code == 404

"""
Fachada ServicioIntentos: el estudiante resuelve un caso (figura SW5).
Responsable: Diego Agudelo · Actividades 4501–4505 (RF-05, RF-08.3, RF-09 a RF-12).

  1. iniciar            crea el intento (estado explorando)
  2. registrar_eventos  telemetría de la escena 3D (RF-12)
  3. decision_inicial   guarda decisión + confianza y entrega la recomendación
                        de la IA, alterada o no (RF-05, RF-08)
  4. preguntar          tutor socrático (RF-07), máximo MAX_MENSAJES_TUTOR
  5. decision_final     cierra, calcula puntaje e insignias y revela la verdad
                        (referencia y si la IA fue alterada) (RF-09 a RF-11)
  Fase 6: historial (RF-02.3) y progreso (nivel, puntos e insignias, RF-11) para el W06.
  Fase 7: tablero de desempeño (RF-13) para el W16.

La respuesta correcta (referencia) NUNCA sale antes de "finalizado".
"""
from uuid import UUID

from ..alteraciones import repositorio as repo_alteraciones
from ..alteraciones.estrategias import Clase, Recomendacion, Roi, ServicioAlteraciones
from ..tutor.prompts import ContextoTutor
from ..tutor.servicio import ServicioTutor
from . import desempeno as metricas
from . import puntaje as reglas
from . import repositorio as repo
from .dominio import TransicionInvalida, estado
from .vision import recomendacion_original

MAX_MENSAJES_TUTOR = 8
NOMBRES_ALTERACION = {
    "clase_incorrecta": "sugirió una clase equivocada",
    "confianza_alterada": "mostró una confianza engañosa",
    "roi_desplazada": "señaló una zona equivocada de la imagen",
}


class NoEncontrado(Exception):
    pass


class OpcionInvalida(Exception):
    pass


class ServicioIntentos:
    def __init__(self, conexion, tutor: ServicioTutor, alteraciones: ServicioAlteraciones):
        self._db = conexion
        self._tutor = tutor
        self._alteraciones = alteraciones

    # ---------- 1. Iniciar ----------
    async def iniciar(self, perfil_id: UUID, caso_id: UUID) -> dict:
        perfil = await self._perfil(perfil_id)
        if not await repo.caso_disponible(self._db, caso_id):
            raise NoEncontrado("El caso no existe o fue descartado")
        intento_id = await repo.crear_intento(self._db, perfil["seudonimo"], caso_id)
        return await self.ver(perfil_id, intento_id)

    async def ver(self, perfil_id: UUID, intento_id: UUID) -> dict:
        perfil = await self._perfil(perfil_id)
        it = await self._intento(perfil, intento_id)
        return await self._vista(it, perfil)

    # ---------- 2. Telemetría (RF-12) ----------
    async def registrar_eventos(self, perfil_id: UUID, intento_id: UUID, eventos: list[dict]) -> int:
        perfil = await self._perfil(perfil_id)
        it = await self._intento(perfil, intento_id)
        nuevo = it["estado"]
        for e in eventos:
            nuevo = estado(nuevo).registrar_evento(e["tipo"])
        await repo.registrar_eventos(self._db, intento_id, eventos)
        if nuevo != it["estado"]:
            await repo.actualizar_estado(self._db, intento_id, it["estado"], nuevo)
        return len(eventos)

    # ---------- 3. Decisión inicial + recomendación (RF-05, RF-08) ----------
    async def decision_inicial(self, perfil_id: UUID, intento_id: UUID, clase: str, confianza: int) -> dict:
        perfil = await self._perfil(perfil_id)
        it = await self._intento(perfil, intento_id)
        estado(it["estado"]).registrar_decision_inicial()
        clases = await self._clases()
        elegida = self._opcion(clases, clase, it["region"])

        original = recomendacion_original(
            await repo.prediccion(self._db, it["imagen_id"]), it["sha256"], clases[it["referencia_id"]], clases
        )
        config = await repo_alteraciones.config_vigente(self._db, perfil["grupo_id"])
        decision = self._alteraciones.decidir(original, config, list(clases.values()), semilla=intento_id.int % 2**31)
        guardado = await repo.guardar_decision_inicial(
            self._db, intento_id, clase_id=elegida.id, confianza=confianza, config_id=config.id,
            alterada=decision.alterada, tipo=decision.tipo, recomendacion=decision.recomendacion.como_json(),
        )
        if not guardado:
            raise TransicionInvalida("La decisión inicial ya fue registrada")
        return await self.ver(perfil_id, intento_id)

    # ---------- 4. Tutor (RF-07) ----------
    async def preguntar(self, perfil_id: UUID, intento_id: UUID, mensaje: str) -> dict:
        perfil = await self._perfil(perfil_id)
        it = await self._intento(perfil, intento_id)
        estado(it["estado"]).consultar_tutor()
        historial = await repo.mensajes(self._db, intento_id)
        usados = sum(1 for m in historial if m["emisor"] == "estudiante")
        if usados >= MAX_MENSAJES_TUTOR:
            raise TransicionInvalida(f"Ya usaste los {MAX_MENSAJES_TUTOR} mensajes del tutor en este caso")

        clases = await self._clases()
        rec = it["recomendacion_mostrada"]
        ctx = ContextoTutor(
            region=it["region"], historia=it["historia"],
            opciones=[c.nombre for c in clases.values() if c.region == it["region"]],
            decision_inicial=clases[it["decision_inicial_id"]].nombre, confianza_inicial=it["confianza_inicial"],
            recomendacion=rec["nombre"], confianza_ia=rec["confianza"],
        )
        respuesta = await self._tutor.responder(ctx, historial, mensaje, semilla=intento_id.int % 2**31 + usados)
        await repo.guardar_mensaje(self._db, intento_id, "estudiante", mensaje)
        await repo.guardar_mensaje(self._db, intento_id, "tutor", respuesta.texto, modelo=respuesta.modelo,
                                   latencia_ms=respuesta.latencia_ms, es_respaldo=respuesta.es_respaldo)
        return {"respuesta": respuesta.texto, "es_respaldo": respuesta.es_respaldo,
                "mensajes_restantes": MAX_MENSAJES_TUTOR - usados - 1}

    # ---------- 5. Decisión final, puntaje e insignias (RF-09 a RF-11) ----------
    async def decision_final(self, perfil_id: UUID, intento_id: UUID, clase: str, confianza: int) -> dict:
        perfil = await self._perfil(perfil_id)
        it = await self._intento(perfil, intento_id)
        estado(it["estado"]).registrar_decision_final()
        clases = await self._clases()
        elegida = self._opcion(clases, clase, it["region"])

        rec = it["recomendacion_mostrada"]
        acierto_usuario = elegida.id == it["referencia_id"]
        acierto_ia = rec["clase_id"] == it["referencia_id"]
        detecto = bool(it["alterada"]) and it["tipo_alteracion"] == "clase_incorrecta" and elegida.id != rec["clase_id"]
        p = reglas.calcular_puntaje(acierto_usuario, confianza, detecto)

        if not await repo.guardar_decision_final(self._db, intento_id, clase_id=elegida.id, confianza=confianza,
                                                 acierto_usuario=acierto_usuario, acierto_ia=acierto_ia,
                                                 puntaje=p.total):
            raise TransicionInvalida("El intento ya terminó")

        puntos = await repo.sumar_puntos(self._db, perfil_id, p.total)
        nivel = reglas.nivel_para(puntos)
        await repo.fijar_nivel(self._db, perfil_id, nivel)
        nuevas = await self._insignias(perfil_id, perfil["seudonimo"], intento_id)
        vista = await self.ver(perfil_id, intento_id)
        vista["retroalimentacion"].update({
            "puntos_totales": puntos, "nivel": nivel,
            "subio_de_nivel": nivel > perfil["nivel"], "insignias_nuevas": nuevas,
        })
        return vista

    # ---------- Fase 6: historial y progreso (W06) ----------
    async def historial(self, perfil_id: UUID, limite: int) -> list[dict]:
        """RF-02.3: casos resueltos (y en curso) del estudiante. Sin la respuesta correcta."""
        perfil = await self._perfil(perfil_id)
        filas = await repo.mis_intentos(self._db, perfil["seudonimo"], limite)
        return [
            {
                "id": str(f["id"]),
                "caso_id": str(f["caso_id"]),
                "estado": f["estado"],
                "fecha": f["iniciado_en"].isoformat(),
                "region": f["region"],
                "dificultad": f["dificultad"],
                "acierto": f["acierto_usuario"] if f["estado"] == "finalizado" else None,
                "puntaje": f["puntaje"],
                # Un caso que el docente descartó ya no se puede repetir (RF-14.6).
                "puede_repetir": f["estado_caso"] != "descartado",
            }
            for f in filas
        ]

    async def progreso(self, perfil_id: UUID) -> dict:
        """RF-11: nivel, puntos y las insignias (ganadas y por ganar) del estudiante."""
        perfil = await self._perfil(perfil_id)
        ganadas = await repo.insignias_de(self._db, perfil_id)
        nivel = perfil["nivel"]
        siguiente = None if nivel >= reglas.NIVEL_MAXIMO else nivel * reglas.PUNTOS_POR_NIVEL
        return {
            "puntos": perfil["puntos"],
            "nivel": nivel,
            "nivel_maximo": reglas.NIVEL_MAXIMO,
            "puntos_por_nivel": reglas.PUNTOS_POR_NIVEL,
            "puntos_siguiente_nivel": siguiente,
            "insignias": [
                {"codigo": i["codigo"], "nombre": i["nombre"], "descripcion": i["descripcion"],
                 "obtenida": i["codigo"] in ganadas}
                for i in await repo.insignias(self._db)
            ],
        }

    async def desempeno(self, perfil_id: UUID) -> dict:
        """RF-13: precisión, detección de errores de la IA, sobredependencia y calibración (W16)."""
        perfil = await self._perfil(perfil_id)
        return metricas.calcular(await repo.filas_desempeno(self._db, perfil["seudonimo"]))

    # ---------- Ayudantes ----------
    async def _perfil(self, perfil_id: UUID) -> dict:
        perfil = await repo.perfil_de(self._db, perfil_id)
        if perfil is None:
            raise NoEncontrado("Perfil no encontrado")
        return perfil

    async def _intento(self, perfil: dict, intento_id: UUID) -> dict:
        it = await repo.obtener_intento(self._db, intento_id, perfil["seudonimo"])
        if it is None:
            raise NoEncontrado("El intento no existe")
        return it

    async def _clases(self) -> dict[int, Clase]:
        return {f["id"]: Clase(f["id"], f["codigo"], f["nombre_es"], f["region"]) for f in await repo.clases(self._db)}

    @staticmethod
    def _opcion(clases: dict[int, Clase], codigo: str, region: str) -> Clase:
        elegida = next((c for c in clases.values() if c.codigo == codigo), None)
        if elegida is None or elegida.region != region:
            raise OpcionInvalida("Elige una de las opciones de la región del caso")
        return elegida

    async def _insignias(self, perfil_id: UUID, participante: UUID, intento_id: UUID) -> list[dict]:
        filas = await repo.historial(self._db, participante)
        estadisticas = {
            "intentos_finalizados": len(filas),
            "errores_ia_detectados": sum(
                1 for f in filas
                if f["alterada"] and f["tipo_alteracion"] == "clase_incorrecta" and f["acierto_usuario"]
                and f["decision_final_id"] != f["clase_recomendada"]
            ),
            "racha_calibrada": reglas.racha_final(
                [reglas.esta_calibrado(f["acierto_usuario"], f["confianza_final"]) for f in filas]
            ),
            "hitos_visitados": await repo.hitos_visitados(self._db, intento_id),
        }
        catalogo = await repo.insignias(self._db)
        nuevas = reglas.insignias_ganadas(
            estadisticas, {i["codigo"]: i["criterio"] for i in catalogo}, await repo.insignias_de(self._db, perfil_id)
        )
        await repo.otorgar(self._db, perfil_id, nuevas)
        return [{"codigo": i["codigo"], "nombre": i["nombre"], "descripcion": i["descripcion"]}
                for i in catalogo if i["codigo"] in nuevas]

    async def _vista(self, it: dict, perfil: dict) -> dict:
        """Lo que ve el estudiante según el estado. La referencia solo al final."""
        clases = await self._clases()

        def decision(clase_id, confianza):
            if clase_id is None:
                return None
            return {"clase": clases[clase_id].codigo, "nombre": clases[clase_id].nombre, "confianza": confianza}

        rec = it["recomendacion_mostrada"]
        vista = {
            "id": str(it["id"]),
            "caso_id": str(it["caso_id"]),
            "estado": it["estado"],
            "region": it["region"],
            "opciones": [{"clase": c.codigo, "nombre": c.nombre} for c in clases.values() if c.region == it["region"]],
            "decision_inicial": decision(it["decision_inicial_id"], it["confianza_inicial"]),
            "recomendacion": None if rec is None else {
                "clase": rec["clase"], "nombre": rec["nombre"], "confianza": rec["confianza"], "roi": rec["roi"],
            },
            "mensajes": [],
            "mensajes_restantes": 0,
            "decision_final": decision(it["decision_final_id"], it["confianza_final"]),
            "retroalimentacion": None,
            # Fase 5: para que la escena 3D marque los hitos ya visitados si el estudiante recarga.
            "hitos_visitados": await repo.lista_hitos_visitados(self._db, it["id"]),
        }
        if it["estado"] in ("recomendacion", "finalizado"):
            historial = await repo.mensajes(self._db, it["id"])
            vista["mensajes"] = [
                {"emisor": m["emisor"], "contenido": m["contenido"], "es_respaldo": m["es_respaldo"],
                 "creado_en": m["creado_en"].isoformat()} for m in historial
            ]
            if it["estado"] == "recomendacion":
                usados = sum(1 for m in historial if m["emisor"] == "estudiante")
                vista["mensajes_restantes"] = max(0, MAX_MENSAJES_TUTOR - usados)
        if it["estado"] == "finalizado":
            vista["retroalimentacion"] = self._retroalimentacion(it, perfil)
        return vista

    @staticmethod
    def _retroalimentacion(it: dict, perfil: dict) -> dict:
        rec = it["recomendacion_mostrada"]
        detecto = bool(it["alterada"]) and it["tipo_alteracion"] == "clase_incorrecta" \
            and it["decision_final_id"] != rec["clase_id"]
        desglose = reglas.calcular_puntaje(it["acierto_usuario"], it["confianza_final"], detecto).como_json()
        lineas = [f"La imagen correspondía a: {it['referencia_nombre']}."]
        lineas.append("Tu decisión final fue correcta." if it["acierto_usuario"] else "Tu decisión final no fue correcta.")
        if it["alterada"]:
            lineas.append(f"Atención: en este caso la IA fue alterada a propósito y {NOMBRES_ALTERACION[it['tipo_alteracion']]}.")
        elif not it["acierto_ia"]:
            lineas.append("La IA se equivocó en este caso.")
        else:
            lineas.append("La recomendación de la IA era correcta.")
        if it["decision_inicial_id"] != it["decision_final_id"]:
            lineas.append("Cambiaste tu decisión después de ver la recomendación.")
        return {
            "referencia": {"clase": it["referencia"], "nombre": it["referencia_nombre"]},
            "acierto_usuario": it["acierto_usuario"],
            "acierto_ia": it["acierto_ia"],
            "alterada": bool(it["alterada"]),
            "tipo_alteracion": it["tipo_alteracion"],
            "cambio_decision": it["decision_inicial_id"] != it["decision_final_id"],
            "puntaje": it["puntaje"],
            "desglose": desglose,
            "detecto_error_ia": detecto,
            "explicacion": lineas,
            "insignias_nuevas": [],
            "subio_de_nivel": False,
            "puntos_totales": perfil["puntos"],
            "nivel": perfil["nivel"],
        }

"""
Fachada ServicioCasos: genera, presenta y revisa casos clínicos.
Responsable: Emmanuel Ospina · Actividades 4201, 4204–4210 y 4214
(RF-02.1, RF-04, RF-14.1 a RF-14.6, RNF-14).

Flujo de generación (Figura 4 de la arquitectura del software):
  1. Elegir imagen (RF-14.1) y su ubicación en la ruta 3D (RF-14.3).
  2. Pedir al modelo de lenguaje la historia clínica (RF-14.2).
  3. Validarla con la cadena de validadores (RF-14.4).
  4. Si pasa, guardarla (RF-14.5). Si no, repetir: máximo 3 intentos.
  5. Tras 3 fallos: registrar en generacion_fallida y avisar al estudiante.
"""
import random
import secrets
import time
from uuid import UUID

from ..llm import LLMNoDisponible, ReintentoConRespaldo
from ..storage import AdaptadorStorage
from . import repositorio as repo
from .dominio import ContextoCaso, crear_cadena
from .prompts import ESQUEMA_HISTORIA, INSTRUCCIONES, VERSION_PROMPT, construir_entrada

MAX_INTENTOS = 3
CAMPOS_HISTORIA = ("edad", "sexo", "motivo", "antecedentes", "sintomas", "texto")


class SinImagenes(Exception):
    """Aún no se han cargado imágenes del dataset (ver api/scripts/cargar_imagenes.py)."""


class CasoNoGenerado(Exception):
    """Tres intentos seguidos fallaron la validación o el modelo no respondió."""

    def __init__(self, motivos: list[str]):
        super().__init__("; ".join(motivos))
        self.motivos = motivos


class ServicioCasos:
    def __init__(self, conexion, llm: ReintentoConRespaldo, storage: AdaptadorStorage | None):
        self._db = conexion
        self._llm = llm
        self._storage = storage
        self._cadena = crear_cadena()

    async def generar(self, perfil_id: UUID, dificultad: str, region: str | None) -> dict:
        inicio = time.monotonic()
        motivos: list[str] = []
        modelo = None
        for _ in range(MAX_INTENTOS):
            semilla = secrets.randbelow(2**31)  # se guarda para reproducir el caso
            azar = random.Random(semilla)
            imagen = await repo.elegir_imagen(self._db, dificultad, region, azar)
            if imagen is None:
                raise SinImagenes()
            ubicacion = await repo.elegir_ubicacion(self._db, imagen["clase_id"], azar)
            if ubicacion is None:
                motivos.append(f"La clase {imagen['clase']} no tiene ubicación 3D")
                continue
            try:
                respuesta, modelo = await self._llm.generar_con_modelo(
                    INSTRUCCIONES, construir_entrada(imagen["clase"], dificultad), ESQUEMA_HISTORIA, semilla
                )
            except LLMNoDisponible as e:
                motivos.append(f"Modelo no disponible: {e}")
                continue
            historia = {k: respuesta.get(k) for k in CAMPOS_HISTORIA} if isinstance(respuesta, dict) else respuesta
            validacion = self._cadena.validar(ContextoCaso(
                clase=imagen["clase"], region_clase=imagen["region"], region_hito=ubicacion["region_hito"],
                region_solicitada=region, historia=historia,
            ))
            if not validacion.ok:
                motivos.append(f"{validacion.fallo.regla}: {validacion.fallo.motivo}")
                continue
            caso_id = await repo.guardar_caso(
                self._db, imagen_id=imagen["id"], ubicacion_id=ubicacion["id"], dificultad=dificultad,
                historia=historia, referencia_id=imagen["clase_id"], modelo_llm=modelo,
                version_prompt=VERSION_PROMPT, semilla=semilla, validacion=validacion.como_json(),
                tiempo_ms=int((time.monotonic() - inicio) * 1000),
            )
            return await self.para_estudiante(caso_id)

        await repo.registrar_fallo(self._db, perfil_id=perfil_id, dificultad=dificultad, region=region,
                                   intentos=MAX_INTENTOS, motivos=motivos, modelo_llm=modelo)
        # Se confirma antes de lanzar el error: si no, el registro se perdería al deshacer la transacción.
        await self._db.commit()
        raise CasoNoGenerado(motivos)

    async def para_estudiante(self, caso_id: UUID) -> dict | None:
        """RF-04: lo que ve el estudiante. NUNCA incluye la clase (la respuesta)."""
        fila = await repo.obtener_caso(self._db, caso_id)
        if fila is None or fila["estado"] == "descartado":
            return None
        return {
            "id": str(fila["id"]),
            "dificultad": fila["dificultad"],
            "region": fila["region"],
            "historia": fila["historia"],
            "imagen_url": await self._url(fila["ruta_storage"]),
            "ubicacion": self._ubicacion(fila),
            "licencia_imagen": f"HyperKvasir · {fila['licencia']}",
            "creado_en": fila["creado_en"].isoformat(),
        }

    async def para_docente(self, estado: str | None, limite: int) -> list[dict]:
        """RF-14.6: el docente sí ve la respuesta y cómo se generó el caso."""
        filas = await repo.listar_casos(self._db, estado, limite)
        return [
            {
                "id": str(f["id"]),
                "estado": f["estado"],
                "dificultad": f["dificultad"],
                "region": f["region"],
                "clase": f["clase"],
                "clase_nombre": f["clase_nombre"],
                "historia": f["historia"],
                "imagen_url": await self._url(f["ruta_storage"]),
                "licencia_imagen": f"HyperKvasir · {f['licencia']}",  # fase 6: la muestra el W18
                "ubicacion": self._ubicacion(f),
                "modelo_llm": f["modelo_llm"],
                "version_prompt": f["version_prompt"],
                "semilla": f["semilla"],
                "validacion": f["validacion"],
                "tiempo_generacion_ms": f["tiempo_generacion_ms"],
                "motivo_descarte": f["motivo_descarte"],
                "creado_en": f["creado_en"].isoformat(),
                "revisado_en": f["revisado_en"].isoformat() if f["revisado_en"] else None,
            }
            for f in filas
        ]

    async def revisar(self, caso_id: UUID, estado: str, motivo: str | None, revisor: UUID) -> bool:
        return await repo.revisar_caso(self._db, caso_id, estado, motivo, revisor)

    async def _url(self, ruta: str) -> str | None:
        return None if self._storage is None else await self._storage.url_firmada(ruta)

    @staticmethod
    def _ubicacion(fila: dict) -> dict:
        # Fase 5 (RF-03.4): la escena 3D pinta una lesión solo si el hallazgo es patológico; un caso
        # normal (línea Z, píloro o retroflexión) no muestra lesión. La clase sigue sin enviarse.
        return {"hito": fila["hito"], "hito_nombre": fila["hito_nombre"], "x": fila["x"], "y": fila["y"],
                "z": fila["z"], "radio_visibilidad": fila["radio_visibilidad"],
                "lesion_visible": fila["es_patologico"]}

"""
Cliente del modelo de lenguaje (LLM) para redactar historias clínicas.
Responsable: Emmanuel Ospina · Actividad 4206 (RF-14.2) y RF-07.3.

Patrones del informe de diseño:
  - Adapter: AdaptadorGemini traduce nuestra interfaz a la API REST de Gemini.
    El resto del sistema no sabe que existe Gemini (ClienteLLM).
  - Adapter de prueba: AdaptadorLocal redacta con plantillas, sin internet y
    sin costo. Sirve para las pruebas automáticas y como último respaldo.
  - Decorator: ReintentoConRespaldo envuelve varios clientes y agrega
    reintentos con espera creciente y cambio de modelo cuando uno falla.

La clave GEMINI_API_KEY solo se lee aquí, desde el .env (RNF-07).
Solo se envían a Gemini datos sintéticos: clase, región y dificultad.
Nunca datos de usuarios (RNF-08).
"""
import asyncio
import json
import random
import time
from typing import Protocol

import httpx2

from .config import Configuracion

URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"


class ErrorLLM(Exception):
    """El modelo respondió mal (clave inválida, respuesta vacía, JSON roto...)."""


class ServicioSaturado(ErrorLLM):
    """Error pasajero (429, 500, 503 o tiempo agotado): vale la pena reintentar."""


class LLMNoDisponible(Exception):
    """Ningún modelo respondió: el servicio debe avisar con un mensaje de respaldo."""


class ClienteLLM(Protocol):
    """Interfaz común. Cualquier modelo (Gemini, local, otro) la cumple."""

    nombre: str

    async def generar_json(self, instrucciones: str, entrada: str, esquema: dict, semilla: int) -> dict: ...


# ---------- Adapter: Gemini por REST ----------

class AdaptadorGemini:
    def __init__(self, modelo: str, api_key: str, tiempo_maximo: float = 12.0, temperatura: float = 0.8):
        self.nombre = modelo
        self._api_key = api_key
        self._tiempo = tiempo_maximo
        self._temperatura = temperatura

    async def generar_json(self, instrucciones: str, entrada: str, esquema: dict, semilla: int) -> dict:
        cuerpo = {
            "systemInstruction": {"parts": [{"text": instrucciones}]},
            "contents": [{"role": "user", "parts": [{"text": entrada}]}],
            "generationConfig": {
                "temperature": self._temperatura,
                "maxOutputTokens": 4096,
                "seed": semilla,  # reproducibilidad (RF-14.5)
                "responseMimeType": "application/json",
                "responseSchema": esquema,  # Gemini responde exactamente con estos campos
            },
        }
        try:
            async with httpx2.AsyncClient(timeout=self._tiempo) as http:
                r = await http.post(
                    URL_GEMINI.format(modelo=self.nombre),
                    headers={"x-goog-api-key": self._api_key},  # nunca en la URL
                    json=cuerpo,
                )
        except httpx2.TimeoutException as e:
            raise ServicioSaturado(f"{self.nombre}: tiempo agotado") from e
        except httpx2.HTTPError as e:
            raise ServicioSaturado(f"{self.nombre}: sin conexión") from e

        if r.status_code in (429, 500, 502, 503, 504):
            raise ServicioSaturado(f"{self.nombre}: HTTP {r.status_code}")
        if r.status_code != 200:
            # 400 (petición inválida), 403 (clave inválida), 404 (modelo no existe).
            raise ErrorLLM(f"{self.nombre}: HTTP {r.status_code}")
        try:
            partes = r.json()["candidates"][0]["content"]["parts"]
            texto = "".join(p.get("text", "") for p in partes if not p.get("thought"))
            return json.loads(texto)
        except (KeyError, IndexError, ValueError, TypeError) as e:
            raise ErrorLLM(f"{self.nombre}: respuesta sin JSON válido") from e


# ---------- Adapter local: plantillas (pruebas y último respaldo) ----------

class AdaptadorLocal:
    """Redacta una historia verosímil con plantillas y la semilla del caso.

    No conoce el diagnóstico por nombre: recibe los síntomas típicos dentro de la
    entrada (ver prompts.py), igual que Gemini. Así ambos pasan por los mismos
    validadores.
    """

    nombre = "local-plantillas-v1"

    async def generar_json(self, instrucciones: str, entrada: str, esquema: dict, semilla: int) -> dict:
        datos = json.loads(entrada.split("DATOS:", 1)[1])
        azar = random.Random(semilla)
        edad = azar.randint(*datos["rango_edad"])
        sexo = azar.choice(["femenino", "masculino"])
        sintomas = azar.sample(datos["sintomas_tipicos"], k=min(2, len(datos["sintomas_tipicos"])))
        antecedentes = azar.sample(datos["antecedentes_tipicos"], k=min(2, len(datos["antecedentes_tipicos"])))
        motivo = datos["motivo_tipico"]
        meses = azar.randint(2, 18)
        texto = (
            f"Paciente {sexo} de {edad} años que consulta por {motivo}. "
            f"Refiere {sintomas[0]}" + (f" y {sintomas[1]}" if len(sintomas) > 1 else "")
            + f" desde hace aproximadamente {meses} meses. "
            f"Antecedentes: {', '.join(antecedentes)}. "
            "Se programa endoscopia digestiva alta para estudio."
        )
        return {
            "edad": edad,
            "sexo": sexo,
            "motivo": motivo,
            "antecedentes": antecedentes,
            "sintomas": sintomas,
            "texto": texto,
        }


# ---------- Decorator: reintentos y modelos de respaldo ----------

class ReintentoConRespaldo:
    """Prueba cada cliente en orden. Si uno está saturado, reintenta con espera
    creciente; si falla de forma definitiva, pasa al siguiente (RF-07.3).
    No guarda estado entre llamadas: es seguro con varias peticiones a la vez.
    """

    def __init__(self, clientes: list[ClienteLLM], reintentos: int = 1, espera_base: float = 1.0,
                 plazo_total: float = 25.0):
        if not clientes:
            raise ValueError("Se necesita al menos un cliente")
        self._clientes = clientes
        self._reintentos = reintentos
        self._espera = espera_base
        self._plazo = plazo_total
        self.nombre = clientes[0].nombre

    async def generar_con_modelo(self, instrucciones: str, entrada: str, esquema: dict,
                                 semilla: int) -> tuple[dict, str]:
        """Devuelve (respuesta, nombre del modelo que respondió) para guardarlo en el caso."""
        inicio = time.monotonic()
        errores: list[str] = []
        for i, cliente in enumerate(self._clientes):
            es_ultimo = i == len(self._clientes) - 1
            for n in range(self._reintentos + 1):
                # El último cliente (el local) siempre se intenta, aunque el plazo se acabe.
                if not es_ultimo and time.monotonic() - inicio > self._plazo:
                    break
                try:
                    return await cliente.generar_json(instrucciones, entrada, esquema, semilla), cliente.nombre
                except ServicioSaturado as e:
                    errores.append(str(e))
                    if n < self._reintentos:
                        await asyncio.sleep(self._espera * 2**n)  # 1 s, 2 s, 4 s...
                except ErrorLLM as e:
                    errores.append(str(e))
                    break  # error definitivo: no reintentar este modelo
        raise LLMNoDisponible("; ".join(errores))

    async def generar_json(self, instrucciones: str, entrada: str, esquema: dict, semilla: int) -> dict:
        respuesta, _ = await self.generar_con_modelo(instrucciones, entrada, esquema, semilla)
        return respuesta


def crear_cliente_llm(config: Configuracion) -> ReintentoConRespaldo:
    """Fábrica: arma la cadena de modelos según el .env."""
    clientes: list[ClienteLLM] = []
    if config.gemini_api_key:
        clientes += [AdaptadorGemini(m, config.gemini_api_key, config.llm_tiempo_maximo)
                     for m in config.modelos_gemini]
    if config.llm_respaldo_local or not clientes:
        clientes.append(AdaptadorLocal())
    return ReintentoConRespaldo(clientes)


def crear_cliente_tutor(config: Configuracion) -> ReintentoConRespaldo | None:
    """Fábrica del tutor (fase 4, RF-07.1): solo modelos Gemini, sin plantillas.

    El generador local de historias no sabe conversar, así que aquí no se usa.
    Sin clave devuelve None y el tutor responde con su guía local (RF-07.3).
    Temperatura baja: respuestas más prudentes. Plazo corto (RNF-03).
    """
    if not config.gemini_api_key:
        return None
    clientes: list[ClienteLLM] = [
        AdaptadorGemini(m, config.gemini_api_key, config.llm_tiempo_maximo, temperatura=0.4)
        for m in config.modelos_gemini
    ]
    return ReintentoConRespaldo(clientes, plazo_total=config.llm_tiempo_maximo)

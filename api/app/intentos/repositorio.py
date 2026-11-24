"""
Consultas SQL de intentos, telemetría, tutor y gamificación (patrón Repository).
Responsable: Diego Agudelo · Actividades 4501–4505 (RF-05, RF-09 a RF-12).

Privacidad (RNF-08): en el esquema investigacion el estudiante solo aparece
por su seudónimo, nunca por su id de cuenta, nombre o correo.
Concurrencia: las actualizaciones de estado llevan "where estado = ..."; si
dos peticiones llegan a la vez, solo una gana (no se suman puntos dos veces).
"""
from uuid import UUID

from psycopg.types.json import Jsonb

_INTENTO = """
  select it.*, c.referencia_id, c.imagen_id, c.historia, c.estado as estado_caso,
         img.sha256, ch.codigo as referencia, ch.nombre_es as referencia_nombre, ch.region
  from investigacion.intento it
  join public.caso c on c.id = it.caso_id
  join public.imagen img on img.id = c.imagen_id
  join public.clase_hallazgo ch on ch.id = c.referencia_id
"""


async def perfil_de(conexion, perfil_id: UUID) -> dict | None:
    return await (await conexion.execute(
        "select seudonimo, grupo_id, puntos, nivel from public.perfil where id = %s", (perfil_id,)
    )).fetchone()


async def caso_disponible(conexion, caso_id: UUID) -> bool:
    fila = await (await conexion.execute(
        "select 1 from public.caso where id = %s and estado <> 'descartado'", (caso_id,)
    )).fetchone()
    return fila is not None


async def crear_intento(conexion, participante: UUID, caso_id: UUID) -> UUID:
    fila = await (await conexion.execute(
        "insert into investigacion.intento (participante, caso_id) values (%s, %s) returning id",
        (participante, caso_id),
    )).fetchone()
    return fila["id"]


async def obtener_intento(conexion, intento_id: UUID, participante: UUID) -> dict | None:
    """Solo el dueño ve su intento: de lo contrario, None (la API responde 404)."""
    return await (await conexion.execute(
        f"{_INTENTO} where it.id = %s and it.participante = %s", (intento_id, participante)
    )).fetchone()


async def clases(conexion) -> list[dict]:
    return await (await conexion.execute(
        "select id, codigo, nombre_es, region from public.clase_hallazgo order by id"
    )).fetchall()


async def prediccion(conexion, imagen_id: int) -> dict | None:
    return await (await conexion.execute(
        """select clase_predicha_id, confianza, roi_x, roi_y, roi_w, roi_h, version_modelo
           from public.prediccion where imagen_id = %s order by creado_en desc limit 1""",
        (imagen_id,),
    )).fetchone()


async def actualizar_estado(conexion, intento_id: UUID, actual: str, nuevo: str) -> None:
    await conexion.execute(
        "update investigacion.intento set estado = %s where id = %s and estado = %s", (nuevo, intento_id, actual)
    )


async def registrar_eventos(conexion, intento_id: UUID, eventos: list[dict]) -> None:
    async with conexion.cursor() as cursor:
        await cursor.executemany(
            """insert into investigacion.evento_telemetria (intento_id, tipo, datos, ocurrido_en)
               values (%s, %s, %s, %s)""",
            [(intento_id, e["tipo"], Jsonb(e["datos"]), e["ocurrido_en"]) for e in eventos],
        )


async def guardar_decision_inicial(conexion, intento_id: UUID, *, clase_id: int, confianza: int,
                                   config_id: int | None, alterada: bool, tipo: str | None,
                                   recomendacion: dict) -> bool:
    cursor = await conexion.execute(
        """update investigacion.intento
           set decision_inicial_id = %s, confianza_inicial = %s, decision_inicial_en = now(), config_id = %s,
               alterada = %s, tipo_alteracion = %s, recomendacion_mostrada = %s, estado = 'recomendacion'
           where id = %s and estado in ('explorando', 'hallazgo_capturado', 'decision_inicial')""",
        (clase_id, confianza, config_id, alterada, tipo, Jsonb(recomendacion), intento_id),
    )
    return cursor.rowcount == 1


async def mensajes(conexion, intento_id: UUID) -> list[dict]:
    return await (await conexion.execute(
        """select emisor, contenido, es_respaldo, creado_en from investigacion.mensaje_tutor
           where intento_id = %s order by creado_en, id""",
        (intento_id,),
    )).fetchall()


async def guardar_mensaje(conexion, intento_id: UUID, emisor: str, contenido: str, *,
                          modelo: str | None = None, latencia_ms: int | None = None,
                          es_respaldo: bool = False) -> None:
    await conexion.execute(
        """insert into investigacion.mensaje_tutor (intento_id, emisor, contenido, modelo_llm, latencia_ms, es_respaldo)
           values (%s, %s, %s, %s, %s, %s)""",
        (intento_id, emisor, contenido, modelo, latencia_ms, es_respaldo),
    )


async def guardar_decision_final(conexion, intento_id: UUID, *, clase_id: int, confianza: int,
                                 acierto_usuario: bool, acierto_ia: bool, puntaje: int) -> bool:
    cursor = await conexion.execute(
        """update investigacion.intento
           set decision_final_id = %s, confianza_final = %s, acierto_usuario = %s, acierto_ia = %s,
               puntaje = %s, estado = 'finalizado', finalizado_en = now()
           where id = %s and estado = 'recomendacion'""",
        (clase_id, confianza, acierto_usuario, acierto_ia, puntaje, intento_id),
    )
    return cursor.rowcount == 1


async def historial(conexion, participante: UUID) -> list[dict]:
    """Intentos finalizados del estudiante, del más antiguo al más reciente (para rachas e insignias)."""
    return await (await conexion.execute(
        """select acierto_usuario, confianza_final, alterada, tipo_alteracion, decision_final_id,
                  (recomendacion_mostrada->>'clase_id')::smallint as clase_recomendada
           from investigacion.intento where participante = %s and estado = 'finalizado'
           order by finalizado_en, id""",
        (participante,),
    )).fetchall()


async def hitos_visitados(conexion, intento_id: UUID) -> int:
    fila = await (await conexion.execute(
        """select count(distinct datos->>'hito') as n from investigacion.evento_telemetria
           where intento_id = %s and tipo = 'hito_visitado'""",
        (intento_id,),
    )).fetchone()
    return fila["n"]


async def lista_hitos_visitados(conexion, intento_id: UUID) -> list[str]:
    """Fase 5: hitos ya visitados, en el orden en que se visitaron (la escena los marca al recargar)."""
    filas = await (await conexion.execute(
        """select datos->>'hito' as hito from investigacion.evento_telemetria
           where intento_id = %s and tipo = 'hito_visitado'
           group by datos->>'hito' order by min(ocurrido_en)""",
        (intento_id,),
    )).fetchall()
    return [f["hito"] for f in filas]


async def sumar_puntos(conexion, perfil_id: UUID, puntos: int) -> int:
    fila = await (await conexion.execute(
        "update public.perfil set puntos = puntos + %s where id = %s returning puntos", (puntos, perfil_id)
    )).fetchone()
    return fila["puntos"]


async def fijar_nivel(conexion, perfil_id: UUID, nivel: int) -> None:
    await conexion.execute("update public.perfil set nivel = %s where id = %s", (nivel, perfil_id))


async def insignias(conexion) -> list[dict]:
    return await (await conexion.execute(
        "select id, codigo, nombre, descripcion, criterio from public.insignia order by id"
    )).fetchall()


async def insignias_de(conexion, perfil_id: UUID) -> set[str]:
    filas = await (await conexion.execute(
        """select i.codigo from public.perfil_insignia pi join public.insignia i on i.id = pi.insignia_id
           where pi.perfil_id = %s""",
        (perfil_id,),
    )).fetchall()
    return {f["codigo"] for f in filas}


async def otorgar(conexion, perfil_id: UUID, codigos: list[str]) -> None:
    for codigo in codigos:
        await conexion.execute(
            """insert into public.perfil_insignia (perfil_id, insignia_id)
               select %s, id from public.insignia where codigo = %s on conflict do nothing""",
            (perfil_id, codigo),
        )


# ---------- Fase 6: historial (RF-02.3) y exportación (RF-15) ----------

async def mis_intentos(conexion, participante: UUID, limite: int) -> list[dict]:
    """Intentos del estudiante, del más reciente al más antiguo. No incluye la respuesta del caso."""
    return await (await conexion.execute(
        """select it.id, it.caso_id, it.estado, it.acierto_usuario, it.puntaje, it.iniciado_en,
                  c.dificultad, c.estado as estado_caso, ch.region
           from investigacion.intento it
           join public.caso c on c.id = it.caso_id
           join public.clase_hallazgo ch on ch.id = c.referencia_id
           where it.participante = %s
           order by it.iniciado_en desc, it.id
           limit %s""",
        (participante, limite),
    )).fetchall()


async def filas_exportacion(conexion) -> list[dict]:
    """RF-15: intentos finalizados, solo con el seudónimo (sin id de cuenta, nombre ni correo)."""
    return await (await conexion.execute(
        """select it.participante, it.caso_id, c.dificultad, ref.codigo as referencia,
                  it.alterada, it.tipo_alteracion,
                  di.codigo as decision_inicial, it.confianza_inicial,
                  df.codigo as decision_final, it.confianza_final, it.cambio_decision,
                  it.acierto_usuario, it.acierto_ia, it.puntaje,
                  extract(epoch from (it.finalizado_en - it.iniciado_en))::int as duracion_s,
                  (select count(distinct e.datos->>'hito') from investigacion.evento_telemetria e
                    where e.intento_id = it.id and e.tipo = 'hito_visitado') as hitos_visitados,
                  (select count(*) from investigacion.mensaje_tutor m
                    where m.intento_id = it.id and m.emisor = 'estudiante') as mensajes_tutor,
                  it.iniciado_en::date as fecha
           from investigacion.intento it
           join public.caso c on c.id = it.caso_id
           join public.clase_hallazgo ref on ref.id = c.referencia_id
           left join public.clase_hallazgo di on di.id = it.decision_inicial_id
           left join public.clase_hallazgo df on df.id = it.decision_final_id
           where it.estado = 'finalizado'
           order by it.finalizado_en, it.id""",
    )).fetchall()

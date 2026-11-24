"""
Consultas SQL de casos (patrón Repository).
Responsable: Emmanuel Ospina · Actividades 4205, 4207, 4209 y 4210.

El servicio nunca escribe SQL: pide datos aquí. Así se prueba y se cambia la
base de datos sin tocar las reglas del negocio. Todas las consultas usan
parámetros (%s), nunca texto pegado: no hay inyección SQL (RNF-07).
"""
import random
from uuid import UUID

from psycopg.types.json import Jsonb

_COLUMNAS_CASO = """
  c.id, c.dificultad, c.historia, c.estado, c.creado_en, c.modelo_llm, c.version_prompt,
  c.semilla, c.validacion, c.tiempo_generacion_ms, c.motivo_descarte, c.revisado_en,
  i.ruta_storage, i.archivo_origen, i.licencia,
  ch.codigo as clase, ch.nombre_es as clase_nombre, ch.region, ch.es_patologico,
  u.x, u.y, u.z, u.radio_visibilidad, h.codigo as hito, h.nombre as hito_nombre
"""
_DESDE_CASO = """
  from public.caso c
  join public.imagen i on i.id = c.imagen_id
  join public.clase_hallazgo ch on ch.id = c.referencia_id
  join public.ubicacion_3d u on u.id = c.ubicacion_id
  join public.hito_anatomico h on h.id = u.hito_id
"""


async def rol_de(conexion, perfil_id: UUID) -> str | None:
    fila = await (await conexion.execute("select rol from public.perfil where id = %s", (perfil_id,))).fetchone()
    return None if fila is None else fila["rol"]


async def elegir_imagen(conexion, dificultad: str, region: str | None, azar: random.Random) -> dict | None:
    """RF-14.1: imagen activa de la dificultad y región pedidas.
    Si no hay de esa dificultad, usa cualquiera de la región (mejor que no dar caso)."""
    sql = """
      select i.id, i.ruta_storage, ch.id as clase_id, ch.codigo as clase, ch.region
      from public.imagen i join public.clase_hallazgo ch on ch.id = i.clase_id
      where i.activa and (%(region)s::region_t is null or ch.region = %(region)s::region_t)
        and (%(dificultad)s::dificultad_t is null or i.dificultad = %(dificultad)s::dificultad_t)
      order by i.id
    """
    for filtro in (dificultad, None):
        filas = await (await conexion.execute(sql, {"region": region, "dificultad": filtro})).fetchall()
        if filas:
            return azar.choice(filas)
    return None


async def elegir_ubicacion(conexion, clase_id: int, azar: random.Random) -> dict | None:
    """RF-14.3: punto de la ruta 3D donde aparece esta clase."""
    filas = await (await conexion.execute(
        """select u.id, u.x, u.y, u.z, u.radio_visibilidad, h.codigo as hito, h.nombre as hito_nombre,
                  h.region as region_hito
           from public.ubicacion_3d u join public.hito_anatomico h on h.id = u.hito_id
           where u.clase_id = %s order by u.id""",
        (clase_id,),
    )).fetchall()
    return azar.choice(filas) if filas else None


async def guardar_caso(conexion, *, imagen_id: int, ubicacion_id: int, dificultad: str, historia: dict,
                       referencia_id: int, modelo_llm: str, version_prompt: str, semilla: int,
                       validacion: dict, tiempo_ms: int) -> UUID:
    """RF-14.5: guarda todo lo necesario para reproducir el caso."""
    fila = await (await conexion.execute(
        """insert into public.caso (imagen_id, ubicacion_id, dificultad, historia, referencia_id, modelo_llm,
                                    version_prompt, semilla, validacion, tiempo_generacion_ms)
           values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id""",
        (imagen_id, ubicacion_id, dificultad, Jsonb(historia), referencia_id, modelo_llm, version_prompt,
         semilla, Jsonb(validacion), tiempo_ms),
    )).fetchone()
    return fila["id"]


async def registrar_fallo(conexion, *, perfil_id: UUID, dificultad: str, region: str | None,
                          intentos: int, motivos: list[str], modelo_llm: str | None) -> None:
    """RF-14.4: deja constancia cuando 3 intentos seguidos fallan."""
    await conexion.execute(
        """insert into public.generacion_fallida (perfil_id, dificultad, region, intentos, motivos, modelo_llm)
           values (%s, %s, %s, %s, %s, %s)""",
        (perfil_id, dificultad, region, intentos, Jsonb(motivos), modelo_llm),
    )


async def obtener_caso(conexion, caso_id: UUID) -> dict | None:
    return await (await conexion.execute(
        f"select {_COLUMNAS_CASO} {_DESDE_CASO} where c.id = %s", (caso_id,)
    )).fetchone()


async def listar_casos(conexion, estado: str | None, limite: int) -> list[dict]:
    """RF-14.6: bandeja del docente, los más recientes primero."""
    return await (await conexion.execute(
        f"""select {_COLUMNAS_CASO} {_DESDE_CASO}
            where (%(estado)s::estado_caso_t is null or c.estado = %(estado)s::estado_caso_t)
            order by c.creado_en desc limit %(limite)s""",
        {"estado": estado, "limite": limite},
    )).fetchall()


async def revisar_caso(conexion, caso_id: UUID, estado: str, motivo: str | None, revisor: UUID) -> bool:
    """RF-14.6: aprobar o descartar. Devuelve False si el caso no existe."""
    cursor = await conexion.execute(
        """update public.caso
           set estado = %s, motivo_descarte = %s, revisado_por = %s, revisado_en = now()
           where id = %s""",
        (estado, motivo if estado == "descartado" else None, revisor, caso_id),
    )
    return cursor.rowcount == 1


async def contar_por_estado(conexion) -> dict[str, int]:
    """Fase 6 (W18): cuántos casos hay en cada pestaña de la bandeja del docente."""
    filas = await (await conexion.execute("select estado::text, count(*) as n from public.caso group by estado")).fetchall()
    conteo = {"pendiente": 0, "aprobado": 0, "descartado": 0}
    conteo.update({f["estado"]: f["n"] for f in filas})
    return conteo

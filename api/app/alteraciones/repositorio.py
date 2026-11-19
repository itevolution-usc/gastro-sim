"""
Configuración de alteraciones guardada por el docente (patrón Repository).
Responsable: Emmanuel Ospina · Actividad 4404 (RF-08.1).

La tabla config_alteracion es un histórico: nunca se actualiza una fila,
se agrega una nueva. La vigente es la más reciente (del grupo o global).
Así cada intento guarda qué configuración se le aplicó (config_id).
"""
from uuid import UUID

from .estrategias import CONFIG_POR_DEFECTO, ConfigAlteracion


async def config_vigente(conexion, grupo_id: UUID | None) -> ConfigAlteracion:
    """La del grupo del estudiante si existe; si no, la global; si no, la de por defecto."""
    fila = await (await conexion.execute(
        """select id, porcentaje, tipos, vigente_desde from public.config_alteracion
           where grupo_id = %s or grupo_id is null
           order by (grupo_id is null), vigente_desde desc limit 1""",
        (grupo_id,),
    )).fetchone()
    if fila is None:
        return CONFIG_POR_DEFECTO
    return ConfigAlteracion(id=fila["id"], porcentaje=float(fila["porcentaje"]), tipos=tuple(fila["tipos"]))


async def detalle_vigente(conexion) -> dict | None:
    return await (await conexion.execute(
        """select id, porcentaje, tipos, vigente_desde from public.config_alteracion
           where grupo_id is null order by vigente_desde desc limit 1"""
    )).fetchone()


async def guardar_config(conexion, porcentaje: float, tipos: list[str], creado_por: UUID) -> dict:
    return await (await conexion.execute(
        """insert into public.config_alteracion (grupo_id, porcentaje, tipos, creado_por)
           values (null, %s, %s, %s) returning id, porcentaje, tipos, vigente_desde""",
        (porcentaje, tipos, creado_por),
    )).fetchone()

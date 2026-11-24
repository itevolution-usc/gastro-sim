"""
Consultas de administración de cuentas (patrón Repository).
Responsable: Diego Agudelo · Actividades 4603 y 4607 (RF-01.3 y RF-01.7).

Cada cambio deja una fila en public.auditoria_cuenta: quién lo hizo (actor),
a qué cuenta (afectado), qué hizo (accion) y cuándo (creado_en).
"""
from uuid import UUID

from psycopg.types.json import Jsonb


def _patron(buscar: str) -> str:
    """Texto del buscador → patrón para ILIKE. Se escapan % y _ para que se busquen literales."""
    limpio = buscar.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{limpio}%"


async def listar_usuarios(conexion, buscar: str | None, limite: int) -> list[dict]:
    return await (await conexion.execute(
        """select p.id, p.nombre_visible, u.email, p.rol::text as rol, p.mfa_activado, p.creado_en
           from public.perfil p join auth.users u on u.id = p.id
           where %(patron)s::text is null or lower(u.email) like %(patron)s or lower(p.nombre_visible) like %(patron)s
           order by p.creado_en desc
           limit %(limite)s""",
        {"patron": _patron(buscar) if buscar and buscar.strip() else None, "limite": limite},
    )).fetchall()


async def usuario(conexion, perfil_id: UUID) -> dict | None:
    return await (await conexion.execute(
        """select p.id, p.nombre_visible, u.email, p.rol::text as rol, p.mfa_activado
           from public.perfil p join auth.users u on u.id = p.id where p.id = %s""",
        (perfil_id,),
    )).fetchone()


async def cambiar_rol(conexion, actor: UUID, afectado: UUID, antes: str, nuevo: str) -> bool:
    """RF-01.3. Solo cambia si el rol sigue siendo el que vio el docente (dos cambios a la vez: gana uno)."""
    cursor = await conexion.execute(
        "update public.perfil set rol = %s::rol_t where id = %s and rol = %s::rol_t", (nuevo, afectado, antes)
    )
    if cursor.rowcount != 1:
        return False
    await conexion.execute(
        "insert into public.auditoria_cuenta (actor_id, afectado_id, accion, detalle) values (%s, %s, %s, %s)",
        (actor, afectado, "asignar_rol" if nuevo == "docente" else "retirar_rol",
         Jsonb({"antes": antes, "despues": nuevo})),
    )
    return True


async def quitar_2fa_local(conexion, afectado: UUID) -> int:
    """RF-01.7: borra los códigos de recuperación y marca el 2FA como no activado. Devuelve cuántos códigos había."""
    cursor = await conexion.execute("delete from public.codigo_recuperacion where perfil_id = %s", (afectado,))
    await conexion.execute("update public.perfil set mfa_activado = false where id = %s", (afectado,))
    return cursor.rowcount


async def auditar_2fa(conexion, actor: UUID, afectado: UUID, codigos: int, factores: int) -> None:
    await conexion.execute(
        "insert into public.auditoria_cuenta (actor_id, afectado_id, accion, detalle) "
        "values (%s, %s, 'restablecer_2fa', %s)",
        (actor, afectado, Jsonb({"via": "administrador", "codigos_eliminados": codigos, "factores_eliminados": factores})),
    )


async def ultimos_cambios(conexion, limite: int) -> list[dict]:
    """El registro que pide RF-01.7, para mostrarlo en el W20."""
    return await (await conexion.execute(
        """select a.accion, a.detalle, a.creado_en, actor.nombre_visible as actor, u.email as afectado
           from public.auditoria_cuenta a
           join public.perfil actor on actor.id = a.actor_id
           join auth.users u on u.id = a.afectado_id
           order by a.creado_en desc, a.id desc
           limit %s""",
        (limite,),
    )).fetchall()

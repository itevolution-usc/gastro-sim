"""
Usuarios, roles y restablecimiento del 2FA (W20 y W21, RF-01.3 y RF-01.7).
Responsable: Diego Agudelo · Actividades 4603 y 4607.

  GET   /admin/usuarios                        lista y busca por correo o nombre (docente o admin)
  PATCH /admin/usuarios/{id}/rol               estudiante ↔ docente (docente o admin)
  POST  /admin/usuarios/{id}/restablecer-2fa   borra el 2FA de otra cuenta (solo admin)
  GET   /admin/auditoria                       últimos cambios registrados (docente o admin)

Reglas:
  - Nadie cambia su propio rol ni restablece su propio 2FA aquí (para eso está W05).
  - El rol "admin" no se asigna ni se quita desde la app: solo en la base de datos.
  - El cambio de rol aplica en la siguiente petición: la API lee el rol cada vez.
Todas exigen sesión con 2FA (aal2).
"""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..admin import repositorio as repo
from ..auth_admin import ClienteAuthAdmin, ErrorAuthAdmin, obtener_admin
from ..casos.repositorio import rol_de
from ..db import obtener_conexion
from ..seguridad import Usuario, usuario_con_2fa
from .casos import docente_actual

router = APIRouter(prefix="/admin", tags=["administración"])


async def admin_actual(usuario: Usuario = Depends(usuario_con_2fa), conexion=Depends(obtener_conexion)) -> Usuario:
    """RF-01.7: restablecer el 2FA de otra persona es solo para administradores."""
    if await rol_de(conexion, usuario.id) != "admin":
        raise HTTPException(403, "Esta función es solo para administradores")
    return usuario


class CambioRol(BaseModel):
    rol: Literal["estudiante", "docente"]


def _vista(f: dict) -> dict:
    return {"id": str(f["id"]), "nombre": f["nombre_visible"], "correo": f["email"], "rol": f["rol"],
            "mfa_activado": f["mfa_activado"]}


async def _otra_cuenta(conexion, actor: Usuario, perfil_id: UUID) -> dict:
    if perfil_id == actor.id:
        raise HTTPException(409, "No puedes cambiar tu propia cuenta desde aquí")
    cuenta = await repo.usuario(conexion, perfil_id)
    if cuenta is None:
        raise HTTPException(404, "La cuenta no existe")
    if cuenta["rol"] == "admin":
        raise HTTPException(409, "Las cuentas de administrador no se modifican desde la app")
    return cuenta


@router.get("/usuarios")
async def listar(buscar: str | None = Query(default=None, max_length=100), limite: int = Query(default=50, ge=1, le=200),
                 _: Usuario = Depends(docente_actual), conexion=Depends(obtener_conexion)):
    return [_vista(f) for f in await repo.listar_usuarios(conexion, buscar, limite)]


@router.patch("/usuarios/{perfil_id}/rol")
async def cambiar_rol(perfil_id: UUID, cambio: CambioRol, actor: Usuario = Depends(docente_actual),
                      conexion=Depends(obtener_conexion)):
    async with conexion.transaction():
        cuenta = await _otra_cuenta(conexion, actor, perfil_id)
        if cuenta["rol"] != cambio.rol and not await repo.cambiar_rol(conexion, actor.id, perfil_id, cuenta["rol"], cambio.rol):
            raise HTTPException(409, "El rol cambió mientras tanto. Recarga la lista.")
    return {**_vista(cuenta), "rol": cambio.rol}


@router.post("/usuarios/{perfil_id}/restablecer-2fa")
async def restablecer_2fa(perfil_id: UUID, actor: Usuario = Depends(admin_actual), conexion=Depends(obtener_conexion),
                          admin: ClienteAuthAdmin = Depends(obtener_admin)):
    async with conexion.transaction():
        cuenta = await _otra_cuenta(conexion, actor, perfil_id)
        codigos = await repo.quitar_2fa_local(conexion, perfil_id)
        # Igual que en W05: se llama a Supabase dentro de la transacción. Si falla, nada se guarda.
        try:
            factores = await admin.eliminar_factores_totp(perfil_id)
        except ErrorAuthAdmin:
            raise HTTPException(503, "No se pudo contactar el servicio de autenticación")
        await repo.auditar_2fa(conexion, actor.id, perfil_id, codigos, factores)
    return {**_vista(cuenta), "mfa_activado": False, "codigos_eliminados": codigos, "factores_eliminados": factores}


@router.get("/auditoria")
async def auditoria(limite: int = Query(default=20, ge=1, le=100), _: Usuario = Depends(docente_actual),
                    conexion=Depends(obtener_conexion)):
    return [
        {"accion": f["accion"], "detalle": f["detalle"], "fecha": f["creado_en"].isoformat(),
         "actor": f["actor"], "afectado": f["afectado"]}
        for f in await repo.ultimos_cambios(conexion, limite)
    ]

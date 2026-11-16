"""
Cuentas: perfil, aviso académico y códigos de recuperación del 2FA.
Responsable: Diego Agudelo · Actividades 4601, 4604, 4605 y 4606
(RF-01.1, RF-01.4, RF-01.5 y RF-01.6).

El registro, la contraseña y el código TOTP los maneja Supabase Auth desde el
navegador. Esta API completa lo que Supabase no trae:
  - el perfil del usuario (rol, aviso, estado del 2FA),
  - la aceptación del aviso académico,
  - los 10 códigos de recuperación de un solo uso.
"""
import hashlib
import hmac
import json
import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from ..auth_admin import ClienteAuthAdmin, ErrorAuthAdmin, obtener_admin
from ..db import obtener_conexion
from ..seguridad import Usuario, usuario_actual, usuario_con_2fa

router = APIRouter(prefix="/cuentas", tags=["cuentas"])

# Versión vigente del aviso académico (pantalla W03). Si el texto cambia,
# se sube la versión y todos deben aceptarlo de nuevo.
VERSION_AVISO = "2026-10"
CANTIDAD_CODIGOS = 10
# Sin letras ni números que se confundan (O/0, I/1): fáciles de copiar a mano.
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


# ---------- Códigos de recuperación ----------

def generar_codigo() -> str:
    """Código de 10 caracteres en dos bloques, por ejemplo K7QM2-XW9PD (≈50 bits de azar)."""
    texto = "".join(secrets.choice(ALFABETO) for _ in range(10))
    return f"{texto[:5]}-{texto[5:]}"


def normalizar(codigo: str) -> str:
    # El usuario puede escribirlo en minúsculas, con espacios o sin guion.
    return "".join(c for c in codigo.upper() if c in ALFABETO)


def cifrar_codigo(codigo: str) -> str:
    """Huella scrypt con sal aleatoria: en la base de datos nunca queda el código en claro."""
    sal = secrets.token_bytes(16)
    huella = hashlib.scrypt(normalizar(codigo).encode(), salt=sal, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${sal.hex()}${huella.hex()}"


def coincide(codigo: str, guardado: str) -> bool:
    try:
        _, sal, huella = guardado.split("$")
        calculada = hashlib.scrypt(normalizar(codigo).encode(), salt=bytes.fromhex(sal), n=2**14, r=8, p=1, dklen=32)
    except ValueError:
        return False
    # Comparación en tiempo constante: no revela cuántos caracteres acertó.
    return hmac.compare_digest(calculada.hex(), huella)


# ---------- Modelos de entrada ----------

class AvisoEntrada(BaseModel):
    version: str = Field(min_length=1, max_length=20)


class RecuperarEntrada(BaseModel):
    codigo: str = Field(min_length=10, max_length=20)


# ---------- Rutas ----------

@router.get("/yo")
async def mi_perfil(usuario: Usuario = Depends(usuario_actual), conexion=Depends(obtener_conexion)):
    """Perfil de la sesión actual. Acepta aal1: el frontend lo usa para decidir
    si muestra el aviso (W03), la activación del 2FA o la verificación (W04)."""
    fila = await (await conexion.execute(
        """select p.nombre_visible, p.rol, p.aviso_aceptado_en, p.version_aviso, p.mfa_activado,
                  (select count(*) from public.codigo_recuperacion c
                    where c.perfil_id = p.id and c.usado_en is null) as codigos_disponibles
             from public.perfil p where p.id = %s""",
        (usuario.id,),
    )).fetchone()
    if fila is None:
        raise HTTPException(status_code=404, detail="No existe un perfil para esta cuenta")
    return {
        "id": str(usuario.id),
        "email": usuario.email,
        "nombre_visible": fila["nombre_visible"],
        "rol": fila["rol"],
        "aviso_aceptado": fila["version_aviso"] == VERSION_AVISO and fila["aviso_aceptado_en"] is not None,
        "version_aviso_vigente": VERSION_AVISO,
        "mfa_activado": fila["mfa_activado"],
        "codigos_disponibles": fila["codigos_disponibles"],
        "nivel_sesion": usuario.aal,
    }


@router.post("/aviso")
async def aceptar_aviso(
    entrada: AvisoEntrada, usuario: Usuario = Depends(usuario_actual), conexion=Depends(obtener_conexion)
):
    """RF-01.4: registra que el usuario aceptó el aviso académico vigente."""
    if entrada.version != VERSION_AVISO:
        raise HTTPException(status_code=409, detail=f"La versión vigente del aviso es {VERSION_AVISO}")
    async with conexion.transaction():
        await conexion.execute(
            "update public.perfil set aviso_aceptado_en = now(), version_aviso = %s where id = %s",
            (VERSION_AVISO, usuario.id),
        )
    return {"aviso_aceptado": True, "version": VERSION_AVISO}


@router.post("/2fa/codigos")
async def generar_codigos(usuario: Usuario = Depends(usuario_con_2fa), conexion=Depends(obtener_conexion)):
    """RF-01.6: tras verificar su primer código TOTP (sesión aal2), el usuario
    recibe 10 códigos de recuperación. Se muestran UNA sola vez (W03, paso 3).
    Volver a llamarla invalida los anteriores."""
    codigos = [generar_codigo() for _ in range(CANTIDAD_CODIGOS)]
    # scrypt es lento a propósito (dificulta adivinar): se calcula en otro hilo.
    huellas = await run_in_threadpool(lambda: [cifrar_codigo(c) for c in codigos])
    async with conexion.transaction():
        await conexion.execute("delete from public.codigo_recuperacion where perfil_id = %s", (usuario.id,))
        async with conexion.cursor() as cursor:
            await cursor.executemany(
                "insert into public.codigo_recuperacion (perfil_id, codigo_hash) values (%s, %s)",
                [(usuario.id, h) for h in huellas],
            )
        await conexion.execute("update public.perfil set mfa_activado = true where id = %s", (usuario.id,))
    return {"codigos": codigos, "aviso": "Guárdalos en un lugar seguro: no se volverán a mostrar."}


@router.post("/2fa/recuperar")
async def recuperar_con_codigo(
    entrada: RecuperarEntrada,
    usuario: Usuario = Depends(usuario_actual),
    conexion=Depends(obtener_conexion),
    admin: ClienteAuthAdmin = Depends(obtener_admin),
):
    """RF-01.6 (W05): el usuario perdió su aplicación autenticadora. Con la
    contraseña (aal1) y un código de recuperación válido se borra su factor
    TOTP y debe activarlo de nuevo. Cada código sirve una sola vez."""
    async with conexion.transaction():
        filas = await (await conexion.execute(
            "select id, codigo_hash from public.codigo_recuperacion "
            "where perfil_id = %s and usado_en is null for update",
            (usuario.id,),
        )).fetchall()
        usado = await run_in_threadpool(
            lambda: next((f["id"] for f in filas if coincide(entrada.codigo, f["codigo_hash"])), None)
        )
        if usado is None:
            raise HTTPException(status_code=400, detail="Código inválido o ya usado")
        await conexion.execute("update public.codigo_recuperacion set usado_en = now() where id = %s", (usado,))
        await conexion.execute("update public.perfil set mfa_activado = false where id = %s", (usuario.id,))
        await conexion.execute(
            "insert into public.auditoria_cuenta (actor_id, afectado_id, accion, detalle) "
            "values (%s, %s, 'restablecer_2fa', %s)",
            (usuario.id, usuario.id, json.dumps({"via": "codigo_recuperacion"})),
        )
        # Se llama a Supabase dentro de la transacción: si falla, nada se guarda
        # y el código sigue disponible.
        try:
            await admin.eliminar_factores_totp(usuario.id)
        except ErrorAuthAdmin:
            raise HTTPException(status_code=503, detail="No se pudo contactar el servicio de autenticación")
    return {"recuperado": True, "codigos_restantes": len(filas) - 1}

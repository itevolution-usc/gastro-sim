"""
Verificación de la sesión (token de Supabase Auth) y del segundo factor.
Responsable: Diego Agudelo · Actividades 4602 y 4605 (RF-01.2, RF-01.5).

El navegador inicia sesión directamente con Supabase Auth y envía su token
en la cabecera "Authorization: Bearer <token>". La API nunca ve contraseñas:
solo comprueba que el token sea auténtico, que no haya vencido y qué nivel de
seguridad tiene la sesión:
    aal1 = solo contraseña        aal2 = contraseña + código 2FA
"""
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Configuracion, obtener_configuracion

# Supabase emite los tokens de usuario con esta audiencia.
AUDIENCIA = "authenticated"
# Lista cerrada de algoritmos: evita el ataque de token sin firma ("none")
# y la confusión entre claves simétricas y asimétricas.
ALGORITMOS_ASIMETRICOS = ("ES256", "RS256")

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Usuario:
    id: UUID
    email: str | None
    aal: str

    @property
    def con_2fa(self) -> bool:
        return self.aal == "aal2"


@lru_cache
def _cliente_jwks(url_supabase: str) -> jwt.PyJWKClient:
    # Las claves públicas del proyecto se descargan una vez y se guardan 10 min.
    return jwt.PyJWKClient(
        f"{url_supabase.rstrip('/')}/auth/v1/.well-known/jwks.json", cache_keys=True, lifespan=600
    )


def decodificar_token(token: str, config: Configuracion) -> dict:
    """Valida firma, vencimiento y audiencia. Lanza jwt.PyJWTError si algo falla."""
    algoritmo = jwt.get_unverified_header(token).get("alg")
    if algoritmo == "HS256":
        if not config.supabase_jwt_secret:
            raise jwt.InvalidTokenError("Token HS256 sin SUPABASE_JWT_SECRET configurado")
        clave = config.supabase_jwt_secret
    elif algoritmo in ALGORITMOS_ASIMETRICOS:
        if not config.supabase_url:
            raise jwt.InvalidTokenError("Token asimétrico sin SUPABASE_URL configurada")
        clave = _cliente_jwks(config.supabase_url).get_signing_key_from_jwt(token).key
    else:
        raise jwt.InvalidTokenError(f"Algoritmo no permitido: {algoritmo}")
    return jwt.decode(
        token, clave, algorithms=[algoritmo], audience=AUDIENCIA, options={"require": ["exp", "sub"]}
    )


async def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    config: Configuracion = Depends(obtener_configuracion),
) -> Usuario:
    """Dependencia: exige una sesión válida (aal1 o aal2)."""
    if credenciales is None:
        raise HTTPException(status_code=401, detail="Falta el token de sesión")
    try:
        # La descarga de claves (JWKS) es bloqueante: se hace en un hilo aparte.
        datos = await run_in_threadpool(decodificar_token, credenciales.credentials, config)
        return Usuario(id=UUID(datos["sub"]), email=datos.get("email"), aal=datos.get("aal", "aal1"))
    except (jwt.PyJWTError, ValueError):
        # No se explica la causa exacta: no se le dan pistas a un atacante.
        raise HTTPException(status_code=401, detail="Sesión inválida o vencida")


async def usuario_con_2fa(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    """Dependencia: exige sesión con segundo factor verificado (RF-01.5).
    Todas las rutas del simulador (casos, intentos, tutor) la usarán."""
    if not usuario.con_2fa:
        raise HTTPException(status_code=403, detail="Debes verificar tu código de doble factor")
    return usuario

"""
Respuestas de error con el estándar problem+json (RFC 9457).
Responsable: Diego Agudelo.

Todas las rutas responden los errores con la misma forma, en español:
{"type": "about:blank", "title": "...", "status": 404, "detail": "..."}
Así el frontend (fase 2) muestra los errores de una sola manera.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

TITULOS = {
    400: "Solicitud inválida",
    401: "No autenticado",
    403: "Sin permiso",
    404: "No encontrado",
    409: "Conflicto",
    422: "Datos inválidos",
    503: "Servicio no disponible",
}


def problema(status: int, detalle: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={"type": "about:blank", "title": TITULOS.get(status, "Error"), "status": status, "detail": detalle},
    )


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detalle = exc.detail if exc.status_code != 404 or exc.detail != "Not Found" else "La ruta solicitada no existe"
        return problema(exc.status_code, str(detalle))

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        campos = ", ".join(".".join(str(p) for p in e["loc"][1:]) for e in exc.errors())
        return problema(422, f"Revisa los campos: {campos}")

"""Traducción de errores de dominio, aplicación e infraestructura a HTTP.

Los casos de uso no conocen HTTP: la capa de presentación es la única que
decide los códigos de estado. El cuerpo de error es uniforme para que el
frontend pueda mostrar mensajes sin depender del proveedor.
"""

from __future__ import annotations

from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ..application.exceptions import ErrorDeAplicacion
from ..domain.exceptions import ErrorDeDominio
from ..infrastructure.exceptions import ErrorDeInfraestructura

_ESTADOS_APLICACION: dict[str, int] = {
    "solicitud_invalida": status.HTTP_400_BAD_REQUEST,
    "producto_no_encontrado": status.HTTP_404_NOT_FOUND,
    "precio_reportado_no_encontrado": status.HTTP_404_NOT_FOUND,
    "producto_duplicado": status.HTTP_409_CONFLICT,
    "producto_inactivo": status.HTTP_409_CONFLICT,
    "precio_mercado_no_disponible": status.HTTP_409_CONFLICT,
    "precio_reportado_de_otro_producto": status.HTTP_409_CONFLICT,
}

_ESTADOS_INFRAESTRUCTURA: dict[str, int] = {
    "configuracion_faltante": status.HTTP_503_SERVICE_UNAVAILABLE,
    "error_de_persistencia": status.HTTP_503_SERVICE_UNAVAILABLE,
    "documento_invalido": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "error_de_extraccion": status.HTTP_502_BAD_GATEWAY,
    "error_de_busqueda_mercado": status.HTTP_502_BAD_GATEWAY,
}


def _respuesta_error(
    *,
    estado: int,
    codigo: str,
    mensaje: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=estado,
        content={"error": {"codigo": codigo, "mensaje": mensaje}},
    )


def registrar_manejadores(app: FastAPI) -> None:
    """Registra los manejadores de excepciones de la API."""

    @app.exception_handler(ErrorDeDominio)
    async def manejar_error_dominio(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        error = cast(ErrorDeDominio, exc)
        return _respuesta_error(
            estado=status.HTTP_422_UNPROCESSABLE_ENTITY,
            codigo=error.codigo,
            mensaje=str(error),
        )

    @app.exception_handler(ErrorDeAplicacion)
    async def manejar_error_aplicacion(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        error = cast(ErrorDeAplicacion, exc)
        estado = _ESTADOS_APLICACION.get(
            error.codigo,
            status.HTTP_400_BAD_REQUEST,
        )
        return _respuesta_error(
            estado=estado,
            codigo=error.codigo,
            mensaje=str(error),
        )

    @app.exception_handler(ErrorDeInfraestructura)
    async def manejar_error_infraestructura(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        error = cast(ErrorDeInfraestructura, exc)
        estado = _ESTADOS_INFRAESTRUCTURA.get(
            error.codigo,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        return _respuesta_error(
            estado=estado,
            codigo=error.codigo,
            mensaje=str(error),
        )


__all__ = ["registrar_manejadores"]

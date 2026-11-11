"""Errores de la capa de aplicación.

Representan fallos de orquestación (recurso inexistente, duplicados, solicitudes
inválidas), no violaciones de reglas de negocio puras.
"""

from __future__ import annotations


class ErrorDeAplicacion(Exception):
    """Base para los errores de los casos de uso."""

    codigo: str = "error_de_aplicacion"

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje

    def __str__(self) -> str:
        return self.mensaje


class SolicitudInvalidaError(ErrorDeAplicacion):
    """Los parámetros de entrada no cumplen el contrato del caso de uso."""

    codigo = "solicitud_invalida"


class ProductoNoEncontradoError(ErrorDeAplicacion):
    """No existe un producto con el identificador solicitado."""

    codigo = "producto_no_encontrado"

    def __init__(self, producto_id: str) -> None:
        super().__init__(f"No existe un producto con identificador '{producto_id}'.")


class ProductoDuplicadoError(ErrorDeAplicacion):
    """Ya existe un producto con el mismo nombre normalizado."""

    codigo = "producto_duplicado"

    def __init__(self, nombre: str) -> None:
        super().__init__(f"Ya existe un producto con el nombre '{nombre}'.")


class ProductoInactivoError(ErrorDeAplicacion):
    """El producto existe, pero está inactivo para nuevas operaciones."""

    codigo = "producto_inactivo"

    def __init__(self, producto_id: str) -> None:
        super().__init__(
            f"El producto '{producto_id}' está inactivo y no admite nuevas operaciones."
        )


class PrecioReportadoNoEncontradoError(ErrorDeAplicacion):
    """No existe el precio reportado solicitado."""

    codigo = "precio_reportado_no_encontrado"

    def __init__(self, precio_reportado_id: str) -> None:
        super().__init__(
            f"No existe un precio reportado con identificador '{precio_reportado_id}'."
        )


class PrecioMercadoNoDisponibleError(ErrorDeAplicacion):
    """No hay un precio de mercado vigente para el producto."""

    codigo = "precio_mercado_no_disponible"

    def __init__(self, producto_id: str) -> None:
        super().__init__(
            f"No hay un precio de mercado vigente para el producto '{producto_id}'."
        )


class PrecioReportadoDeOtroProductoError(ErrorDeAplicacion):
    """El precio reportado no pertenece al producto que se intenta evaluar."""

    codigo = "precio_reportado_de_otro_producto"

    def __init__(self, precio_reportado_id: str, producto_id: str) -> None:
        super().__init__(
            f"El precio reportado '{precio_reportado_id}' no pertenece al producto "
            f"'{producto_id}'."
        )

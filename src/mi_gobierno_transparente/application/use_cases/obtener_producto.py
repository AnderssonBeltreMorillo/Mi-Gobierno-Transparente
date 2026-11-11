"""Caso de uso: obtener un producto por identificador."""

from __future__ import annotations

from ..dto.producto_dto import ProductoDTO
from ..dto.queries import ObtenerProductoQuery
from ..mappers import a_producto_dto
from ..ports.repositories import ProductoRepositorio
from ._comun import obtener_producto


class ObtenerProducto:
    """Devuelve el detalle de un producto existente."""

    def __init__(self, productos: ProductoRepositorio) -> None:
        self._productos = productos

    def ejecutar(self, consulta: ObtenerProductoQuery) -> ProductoDTO:
        """Obtiene el producto.

        Raises:
            ProductoNoEncontradoError: si no existe.
        """
        producto = obtener_producto(self._productos, consulta.producto_id)
        return a_producto_dto(producto)

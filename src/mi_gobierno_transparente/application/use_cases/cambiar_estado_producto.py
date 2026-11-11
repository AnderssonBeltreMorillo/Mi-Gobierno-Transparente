"""Caso de uso: activar o desactivar un producto."""

from __future__ import annotations

from ..dto.commands import CambiarEstadoProductoCommand
from ..dto.producto_dto import ProductoDTO
from ..mappers import a_producto_dto
from ..ports.repositories import ProductoRepositorio
from ._comun import obtener_producto


class CambiarEstadoProducto:
    """Activa o desactiva un producto sin borrar su histórico."""

    def __init__(self, productos: ProductoRepositorio) -> None:
        self._productos = productos

    def ejecutar(self, comando: CambiarEstadoProductoCommand) -> ProductoDTO:
        """Aplica el cambio de estado de forma idempotente.

        Raises:
            ProductoNoEncontradoError: si el producto no existe.
        """
        producto = obtener_producto(self._productos, comando.producto_id)
        actualizado = producto.activar() if comando.activo else producto.desactivar()

        if actualizado != producto:
            self._productos.guardar(actualizado)
        return a_producto_dto(actualizado)

"""Caso de uso: listar productos permitidos."""

from __future__ import annotations

from ...domain.value_objects.categoria_producto import CategoriaProducto
from ..dto.producto_dto import ProductoDTO
from ..dto.queries import ListarProductosQuery
from ..mappers import a_producto_dto
from ..ports.repositories import ProductoRepositorio
from ._comun import validar_paginacion


class ListarProductos:
    """Lista productos de alimentos y aseo, opcionalmente por categoría."""

    def __init__(self, productos: ProductoRepositorio) -> None:
        self._productos = productos

    def ejecutar(self, consulta: ListarProductosQuery) -> list[ProductoDTO]:
        """Devuelve los productos que cumplen los filtros.

        Raises:
            CategoriaNoPermitidaError: si se filtra por una categoría no procesable.
            SolicitudInvalidaError: si la paginación es inválida.
        """
        validar_paginacion(
            limite=consulta.limite,
            desplazamiento=consulta.desplazamiento,
        )
        if consulta.categoria is not None:
            CategoriaProducto.validar_permitida(consulta.categoria)

        productos = self._productos.listar(
            categoria=consulta.categoria,
            incluir_inactivos=consulta.incluir_inactivos,
            limite=consulta.limite,
            desplazamiento=consulta.desplazamiento,
        )
        return [a_producto_dto(producto) for producto in productos]

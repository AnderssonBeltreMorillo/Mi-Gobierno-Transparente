"""Caso de uso: registrar un producto."""

from __future__ import annotations

from ...domain.entities.producto import Producto
from ..dto.commands import RegistrarProductoCommand
from ..dto.producto_dto import ProductoDTO
from ..exceptions import ProductoDuplicadoError
from ..mappers import a_producto_dto
from ..ports.generador_identificadores import GeneradorIdentificadores
from ..ports.repositories import ProductoRepositorio


class RegistrarProducto:
    """Registra un producto de alimentos o aseo, evitando duplicados por nombre.

    La entidad ``Producto`` aplica las validaciones de campos y la regla de
    categorías permitidas; este caso de uso solo orquesta la creación.
    """

    def __init__(
        self,
        productos: ProductoRepositorio,
        generador_id: GeneradorIdentificadores,
    ) -> None:
        self._productos = productos
        self._generador_id = generador_id

    def ejecutar(self, comando: RegistrarProductoCommand) -> ProductoDTO:
        """Crea y persiste el producto.

        Raises:
            CategoriaNoPermitidaError: si la categoría no es alimentos o aseo.
            ProductoInvalidoError: si algún campo no cumple las invariantes.
            ProductoDuplicadoError: si ya existe el mismo nombre normalizado.
        """
        producto = Producto(
            id=self._generador_id.nuevo(),
            nombre=comando.nombre,
            categoria=comando.categoria,
            unidad_medida=comando.unidad_medida,
            marca=comando.marca,
            descripcion=comando.descripcion,
        )
        if self._productos.existe_por_nombre(producto.nombre_normalizado):
            raise ProductoDuplicadoError(producto.nombre)

        self._productos.guardar(producto)
        return a_producto_dto(producto)

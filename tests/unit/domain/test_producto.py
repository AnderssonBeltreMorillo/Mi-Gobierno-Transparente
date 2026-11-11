"""Pruebas de la entidad Producto y de la regla de categorías permitidas."""

from __future__ import annotations

import unittest

from mi_gobierno_transparente.domain.entities import Producto
from mi_gobierno_transparente.domain.exceptions import (
    CategoriaNoPermitidaError,
    ProductoInvalidoError,
)
from mi_gobierno_transparente.domain.value_objects import (
    CategoriaProducto,
    UnidadMedida,
)


class TestProducto(unittest.TestCase):
    def _producto(self, **cambios: object) -> Producto:
        datos: dict[str, object] = {
            "id": "prod-1",
            "nombre": "Arroz extra",
            "categoria": CategoriaProducto.ALIMENTOS,
            "unidad_medida": UnidadMedida.KILOGRAMO,
        }
        datos.update(cambios)
        return Producto(**datos)  # type: ignore[arg-type]

    def test_acepta_alimentos_y_aseo(self) -> None:
        self.assertTrue(self._producto().pertenece_a_categoria_permitida())
        self.assertTrue(
            self._producto(categoria=CategoriaProducto.ASEO).pertenece_a_categoria_permitida()
        )

    def test_rechaza_categoria_no_permitida(self) -> None:
        with self.assertRaises(CategoriaNoPermitidaError):
            self._producto(categoria=CategoriaProducto.ELECTRONICA)

    def test_normaliza_espacios_del_nombre(self) -> None:
        producto = self._producto(nombre="  Arroz   extra  ")
        self.assertEqual(producto.nombre, "Arroz extra")
        self.assertEqual(producto.nombre_normalizado, "arroz extra")

    def test_rechaza_nombre_demasiado_corto(self) -> None:
        with self.assertRaises(ProductoInvalidoError):
            self._producto(nombre="A")

    def test_desactivar_devuelve_una_copia(self) -> None:
        producto = self._producto()
        inactivo = producto.desactivar()

        self.assertTrue(producto.activo)
        self.assertFalse(inactivo.activo)
        self.assertEqual(inactivo.id, producto.id)


if __name__ == "__main__":
    unittest.main()

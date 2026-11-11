"""Pruebas del caso de uso RegistrarProducto."""

from __future__ import annotations

import unittest

from mi_gobierno_transparente.application.dto import RegistrarProductoCommand
from mi_gobierno_transparente.application.exceptions import ProductoDuplicadoError
from mi_gobierno_transparente.application.use_cases import RegistrarProducto
from mi_gobierno_transparente.domain.exceptions import (
    CategoriaNoPermitidaError,
    ProductoInvalidoError,
)
from mi_gobierno_transparente.domain.value_objects import (
    CategoriaProducto,
    UnidadMedida,
)

from .fakes import GeneradorSecuencial, ProductoRepositorioEnMemoria


class TestRegistrarProducto(unittest.TestCase):
    def setUp(self) -> None:
        self.repositorio = ProductoRepositorioEnMemoria()
        self.caso = RegistrarProducto(self.repositorio, GeneradorSecuencial("prod"))

    def _comando(
        self,
        *,
        nombre: str = "Arroz extra",
        categoria: CategoriaProducto = CategoriaProducto.ALIMENTOS,
        unidad_medida: UnidadMedida = UnidadMedida.KILOGRAMO,
    ) -> RegistrarProductoCommand:
        return RegistrarProductoCommand(
            nombre=nombre,
            categoria=categoria,
            unidad_medida=unidad_medida,
        )

    def test_registra_producto_valido(self) -> None:
        dto = self.caso.ejecutar(self._comando())

        self.assertEqual(dto.id, "prod-1")
        self.assertTrue(dto.activo)
        self.assertEqual(dto.categoria, CategoriaProducto.ALIMENTOS)
        self.assertIsNotNone(self.repositorio.obtener_por_id(dto.id))

    def test_permite_productos_de_aseo(self) -> None:
        dto = self.caso.ejecutar(
            self._comando(
                nombre="Detergente líquido",
                categoria=CategoriaProducto.ASEO,
                unidad_medida=UnidadMedida.LITRO,
            )
        )

        self.assertEqual(dto.categoria, CategoriaProducto.ASEO)
        self.assertEqual(dto.unidad_medida, UnidadMedida.LITRO)

    def test_rechaza_duplicado_por_nombre_normalizado(self) -> None:
        self.caso.ejecutar(self._comando(nombre="Arroz  Costeño"))

        with self.assertRaises(ProductoDuplicadoError):
            self.caso.ejecutar(self._comando(nombre="  arroz costeño "))

    def test_rechaza_categoria_no_permitida(self) -> None:
        with self.assertRaises(CategoriaNoPermitidaError):
            self.caso.ejecutar(self._comando(categoria=CategoriaProducto.ELECTRONICA))

    def test_rechaza_nombre_invalido(self) -> None:
        with self.assertRaises(ProductoInvalidoError):
            self.caso.ejecutar(self._comando(nombre="A"))


if __name__ == "__main__":
    unittest.main()

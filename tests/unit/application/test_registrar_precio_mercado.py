"""Pruebas del caso de uso RegistrarPrecioMercado."""

from __future__ import annotations

import unittest
from datetime import UTC, date, datetime
from decimal import Decimal

from mi_gobierno_transparente.application.dto import (
    RegistrarPrecioMercadoCommand,
    RegistrarProductoCommand,
)
from mi_gobierno_transparente.application.exceptions import (
    ProductoInactivoError,
    ProductoNoEncontradoError,
    SolicitudInvalidaError,
)
from mi_gobierno_transparente.application.use_cases import (
    RegistrarPrecioMercado,
    RegistrarProducto,
)
from mi_gobierno_transparente.domain.value_objects import (
    CategoriaProducto,
    UnidadMedida,
)

from .fakes import (
    GeneradorSecuencial,
    PrecioMercadoRepositorioEnMemoria,
    ProductoRepositorioEnMemoria,
    RelojFijo,
)


class TestRegistrarPrecioMercado(unittest.TestCase):
    def setUp(self) -> None:
        self.reloj = RelojFijo(datetime(2026, 11, 7, 12, 0, tzinfo=UTC))
        self.generador = GeneradorSecuencial("id")
        self.productos = ProductoRepositorioEnMemoria()
        self.precios = PrecioMercadoRepositorioEnMemoria()

        registrar_producto = RegistrarProducto(self.productos, self.generador)
        self.producto = registrar_producto.ejecutar(
            RegistrarProductoCommand(
                nombre="Arroz extra",
                categoria=CategoriaProducto.ALIMENTOS,
                unidad_medida=UnidadMedida.KILOGRAMO,
            )
        )
        self.caso = RegistrarPrecioMercado(
            self.productos,
            self.precios,
            self.generador,
            self.reloj,
        )

    def _comando(
        self,
        *,
        monto: str = "100",
        fecha_registro: date | None = None,
        producto_id: str | None = None,
    ) -> RegistrarPrecioMercadoCommand:
        return RegistrarPrecioMercadoCommand(
            producto_id=producto_id or self.producto.id,
            monto=Decimal(monto),
            fuente="Mercado mayorista",
            fecha_registro=fecha_registro,
        )

    def test_registra_precio_vigente(self) -> None:
        dto = self.caso.ejecutar(self._comando())

        self.assertTrue(dto.vigente)
        self.assertEqual(dto.monto, Decimal("100.00"))
        self.assertEqual(dto.fecha_registro, date(2026, 11, 7))

        vigente = self.precios.obtener_vigente(self.producto.id)
        self.assertIsNotNone(vigente)
        assert vigente is not None
        self.assertEqual(vigente.id, dto.id)

    def test_reemplaza_el_precio_vigente_anterior(self) -> None:
        primero = self.caso.ejecutar(self._comando(monto="100"))
        segundo = self.caso.ejecutar(self._comando(monto="110"))

        anterior = self.precios.obtener_por_id(primero.id)
        self.assertIsNotNone(anterior)
        assert anterior is not None
        self.assertFalse(anterior.vigente)

        vigente = self.precios.obtener_vigente(self.producto.id)
        self.assertIsNotNone(vigente)
        assert vigente is not None
        self.assertEqual(vigente.id, segundo.id)

    def test_rechaza_fecha_futura(self) -> None:
        with self.assertRaises(SolicitudInvalidaError):
            self.caso.ejecutar(self._comando(fecha_registro=date(2026, 11, 8)))

    def test_rechaza_producto_inexistente(self) -> None:
        with self.assertRaises(ProductoNoEncontradoError):
            self.caso.ejecutar(self._comando(producto_id="no-existe"))

    def test_rechaza_producto_inactivo(self) -> None:
        entidad = self.productos.obtener_por_id(self.producto.id)
        self.assertIsNotNone(entidad)
        assert entidad is not None
        self.productos.guardar(entidad.desactivar())

        with self.assertRaises(ProductoInactivoError):
            self.caso.ejecutar(self._comando())


if __name__ == "__main__":
    unittest.main()

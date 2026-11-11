"""Pruebas del caso de uso EvaluarPrecio."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from mi_gobierno_transparente.application.dto import (
    EvaluacionDTO,
    EvaluarPrecioCommand,
    RegistrarPrecioMercadoCommand,
    RegistrarPrecioReportadoCommand,
    RegistrarProductoCommand,
)
from mi_gobierno_transparente.application.exceptions import (
    PrecioMercadoNoDisponibleError,
    PrecioReportadoDeOtroProductoError,
    ProductoInactivoError,
    ProductoNoEncontradoError,
)
from mi_gobierno_transparente.application.use_cases import (
    EvaluarPrecio,
    RegistrarPrecioMercado,
    RegistrarPrecioReportado,
    RegistrarProducto,
)
from mi_gobierno_transparente.domain.services import EvaluadorPrecio
from mi_gobierno_transparente.domain.value_objects import (
    CategoriaProducto,
    NivelRiesgo,
    UnidadMedida,
)

from .fakes import (
    EvaluacionPrecioRepositorioEnMemoria,
    GeneradorSecuencial,
    PrecioMercadoRepositorioEnMemoria,
    PrecioReportadoRepositorioEnMemoria,
    ProductoRepositorioEnMemoria,
    RelojFijo,
)


class TestEvaluarPrecio(unittest.TestCase):
    def setUp(self) -> None:
        self.reloj = RelojFijo(datetime(2026, 11, 7, 12, 0, tzinfo=UTC))
        self.generador = GeneradorSecuencial("id")
        self.productos = ProductoRepositorioEnMemoria()
        self.precios_mercado = PrecioMercadoRepositorioEnMemoria()
        self.precios_reportados = PrecioReportadoRepositorioEnMemoria()
        self.evaluaciones = EvaluacionPrecioRepositorioEnMemoria()

        self.registrar_producto = RegistrarProducto(self.productos, self.generador)
        self.registrar_mercado = RegistrarPrecioMercado(
            self.productos,
            self.precios_mercado,
            self.generador,
            self.reloj,
        )
        self.registrar_reportado = RegistrarPrecioReportado(
            self.productos,
            self.precios_reportados,
            self.generador,
            self.reloj,
        )
        self.caso = EvaluarPrecio(
            self.productos,
            self.precios_mercado,
            self.precios_reportados,
            self.evaluaciones,
            EvaluadorPrecio(),
            self.generador,
            self.reloj,
        )

        self.producto = self.registrar_producto.ejecutar(
            RegistrarProductoCommand(
                nombre="Arroz extra",
                categoria=CategoriaProducto.ALIMENTOS,
                unidad_medida=UnidadMedida.KILOGRAMO,
            )
        )

    def _registrar_mercado(self, monto: str = "100") -> None:
        self.registrar_mercado.ejecutar(
            RegistrarPrecioMercadoCommand(
                producto_id=self.producto.id,
                monto=Decimal(monto),
                fuente="Mercado mayorista",
            )
        )

    def _registrar_reporte(
        self,
        monto: str,
        *,
        producto_id: str | None = None,
    ) -> str:
        reporte = self.registrar_reportado.ejecutar(
            RegistrarPrecioReportadoCommand(
                producto_id=producto_id or self.producto.id,
                monto=Decimal(monto),
                establecimiento="Bodega Central",
            )
        )
        return reporte.id

    def _evaluar(
        self,
        monto_reportado: str,
        *,
        monto_mercado: str = "100",
    ) -> EvaluacionDTO:
        self._registrar_mercado(monto_mercado)
        reporte_id = self._registrar_reporte(monto_reportado)
        return self.caso.ejecutar(
            EvaluarPrecioCommand(
                producto_id=self.producto.id,
                precio_reportado_id=reporte_id,
            )
        )

    def test_genera_alto_riesgo_y_persiste_la_evaluacion(self) -> None:
        dto = self._evaluar("120")

        self.assertIs(dto.nivel_riesgo, NivelRiesgo.ALTO_RIESGO)
        self.assertEqual(dto.monto_reportado, Decimal("120.00"))
        self.assertEqual(dto.monto_mercado, Decimal("100.00"))
        self.assertEqual(dto.excedente, Decimal("20.00"))
        self.assertEqual(dto.sobreprecio_porcentaje, Decimal("20.00"))
        self.assertEqual(dto.moneda, "PEN")
        self.assertTrue(dto.requiere_intervencion)
        self.assertFalse(dto.dentro_de_tolerancia)
        self.assertEqual(dto.evaluado_en, self.reloj.ahora())
        self.assertEqual(dto.version_regla, EvaluadorPrecio.VERSION)
        self.assertIsNotNone(self.evaluaciones.obtener_por_id(dto.id))

    def test_genera_alerta_amarilla(self) -> None:
        dto = self._evaluar("110")

        self.assertIs(dto.nivel_riesgo, NivelRiesgo.ALERTA_AMARILLA)
        self.assertEqual(dto.sobreprecio_porcentaje, Decimal("10.00"))
        self.assertTrue(dto.requiere_intervencion)

    def test_genera_precio_justo(self) -> None:
        dto = self._evaluar("95")

        self.assertIs(dto.nivel_riesgo, NivelRiesgo.PRECIO_JUSTO)
        self.assertEqual(dto.excedente, Decimal("0.00"))
        self.assertEqual(dto.sobreprecio_porcentaje, Decimal("0.00"))
        self.assertFalse(dto.requiere_intervencion)

    def test_marca_la_banda_de_tolerancia(self) -> None:
        dto = self._evaluar("100.50")

        self.assertIs(dto.nivel_riesgo, NivelRiesgo.PRECIO_JUSTO)
        self.assertTrue(dto.dentro_de_tolerancia)
        self.assertEqual(dto.sobreprecio_porcentaje, Decimal("0.50"))

    def test_falla_si_no_hay_precio_de_mercado(self) -> None:
        reporte_id = self._registrar_reporte("120")

        with self.assertRaises(PrecioMercadoNoDisponibleError):
            self.caso.ejecutar(
                EvaluarPrecioCommand(
                    producto_id=self.producto.id,
                    precio_reportado_id=reporte_id,
                )
            )

    def test_falla_si_el_reporte_es_de_otro_producto(self) -> None:
        otro_producto = self.registrar_producto.ejecutar(
            RegistrarProductoCommand(
                nombre="Detergente líquido",
                categoria=CategoriaProducto.ASEO,
                unidad_medida=UnidadMedida.LITRO,
            )
        )
        reporte_id = self._registrar_reporte("120", producto_id=otro_producto.id)
        self._registrar_mercado("100")

        with self.assertRaises(PrecioReportadoDeOtroProductoError):
            self.caso.ejecutar(
                EvaluarPrecioCommand(
                    producto_id=self.producto.id,
                    precio_reportado_id=reporte_id,
                )
            )

    def test_falla_si_el_producto_no_existe(self) -> None:
        with self.assertRaises(ProductoNoEncontradoError):
            self.caso.ejecutar(
                EvaluarPrecioCommand(
                    producto_id="no-existe",
                    precio_reportado_id="reporte-1",
                )
            )

    def test_falla_si_el_producto_esta_inactivo(self) -> None:
        reporte_id = self._registrar_reporte("120")
        entidad = self.productos.obtener_por_id(self.producto.id)
        self.assertIsNotNone(entidad)
        assert entidad is not None
        self.productos.guardar(entidad.desactivar())

        with self.assertRaises(ProductoInactivoError):
            self.caso.ejecutar(
                EvaluarPrecioCommand(
                    producto_id=self.producto.id,
                    precio_reportado_id=reporte_id,
                )
            )


if __name__ == "__main__":
    unittest.main()

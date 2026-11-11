"""Prueba de flujo completo del demo, usando solo los casos de uso."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from mi_gobierno_transparente.application.dto import (
    CambiarEstadoProductoCommand,
    EvaluarPrecioCommand,
    ListarEvaluacionesQuery,
    ListarProductosQuery,
    ObtenerResumenRiesgoQuery,
    RegistrarPrecioMercadoCommand,
    RegistrarPrecioReportadoCommand,
    RegistrarProductoCommand,
)
from mi_gobierno_transparente.application.use_cases import (
    CambiarEstadoProducto,
    EvaluarPrecio,
    ListarEvaluaciones,
    ListarProductos,
    ObtenerResumenRiesgo,
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


class TestFlujoCompleto(unittest.TestCase):
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
        self.evaluar = EvaluarPrecio(
            self.productos,
            self.precios_mercado,
            self.precios_reportados,
            self.evaluaciones,
            EvaluadorPrecio(),
            self.generador,
            self.reloj,
        )
        self.listar_evaluaciones = ListarEvaluaciones(self.evaluaciones)
        self.listar_productos = ListarProductos(self.productos)
        self.resumen = ObtenerResumenRiesgo(self.evaluaciones)
        self.cambiar_estado = CambiarEstadoProducto(self.productos)

    def _producto(
        self,
        nombre: str,
        categoria: CategoriaProducto,
        unidad: UnidadMedida,
    ) -> str:
        return self.registrar_producto.ejecutar(
            RegistrarProductoCommand(
                nombre=nombre,
                categoria=categoria,
                unidad_medida=unidad,
            )
        ).id

    def _evaluar(
        self,
        producto_id: str,
        *,
        precio_mercado: str,
        precio_reportado: str,
    ) -> str:
        self.registrar_mercado.ejecutar(
            RegistrarPrecioMercadoCommand(
                producto_id=producto_id,
                monto=Decimal(precio_mercado),
                fuente="Mercado mayorista",
            )
        )
        reporte = self.registrar_reportado.ejecutar(
            RegistrarPrecioReportadoCommand(
                producto_id=producto_id,
                monto=Decimal(precio_reportado),
                establecimiento="Bodega Central",
            )
        )
        return self.evaluar.ejecutar(
            EvaluarPrecioCommand(
                producto_id=producto_id,
                precio_reportado_id=reporte.id,
            )
        ).id

    def test_flujo_de_transparencia_de_precios(self) -> None:
        arroz = self._producto(
            "Arroz extra",
            CategoriaProducto.ALIMENTOS,
            UnidadMedida.KILOGRAMO,
        )
        detergente = self._producto(
            "Detergente líquido",
            CategoriaProducto.ASEO,
            UnidadMedida.LITRO,
        )
        aceite = self._producto(
            "Aceite vegetal",
            CategoriaProducto.ALIMENTOS,
            UnidadMedida.LITRO,
        )

        evaluacion_arroz = self._evaluar(
            arroz,
            precio_mercado="100",
            precio_reportado="95",
        )
        evaluacion_detergente = self._evaluar(
            detergente,
            precio_mercado="20",
            precio_reportado="22",
        )
        evaluacion_aceite = self._evaluar(
            aceite,
            precio_mercado="50",
            precio_reportado="65",
        )

        resumen = self.resumen.ejecutar(ObtenerResumenRiesgoQuery())
        self.assertEqual(resumen.total_evaluaciones, 3)
        self.assertEqual(resumen.precio_justo, 1)
        self.assertEqual(resumen.alerta_amarilla, 1)
        self.assertEqual(resumen.alto_riesgo, 1)
        self.assertEqual(resumen.porcentaje_alto_riesgo, Decimal("33.33"))

        resumen_arroz = self.resumen.ejecutar(
            ObtenerResumenRiesgoQuery(producto_id=arroz)
        )
        self.assertEqual(resumen_arroz.total_evaluaciones, 1)
        self.assertEqual(resumen_arroz.precio_justo, 1)
        self.assertEqual(resumen_arroz.alto_riesgo, 0)

        altos = self.listar_evaluaciones.ejecutar(
            ListarEvaluacionesQuery(nivel_riesgo=NivelRiesgo.ALTO_RIESGO)
        )
        self.assertEqual(len(altos), 1)
        self.assertEqual(altos[0].id, evaluacion_aceite)

        amarillas = self.listar_evaluaciones.ejecutar(
            ListarEvaluacionesQuery(nivel_riesgo=NivelRiesgo.ALERTA_AMARILLA)
        )
        self.assertEqual(len(amarillas), 1)
        self.assertEqual(amarillas[0].id, evaluacion_detergente)

        justos = self.listar_evaluaciones.ejecutar(
            ListarEvaluacionesQuery(producto_id=arroz)
        )
        self.assertEqual(len(justos), 1)
        self.assertEqual(justos[0].id, evaluacion_arroz)

        alimentos = self.listar_productos.ejecutar(
            ListarProductosQuery(categoria=CategoriaProducto.ALIMENTOS)
        )
        self.assertEqual(len(alimentos), 2)

        self.cambiar_estado.ejecutar(
            CambiarEstadoProductoCommand(producto_id=aceite, activo=False)
        )
        activos = self.listar_productos.ejecutar(ListarProductosQuery())
        self.assertEqual(len(activos), 2)

        todos = self.listar_productos.ejecutar(
            ListarProductosQuery(incluir_inactivos=True)
        )
        self.assertEqual(len(todos), 3)


if __name__ == "__main__":
    unittest.main()

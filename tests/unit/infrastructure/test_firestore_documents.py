"""Pruebas del mapeo entre entidades y documentos de Firestore.

No requieren firebase-admin ni el emulador: el módulo de mapeo es puro.
"""

from __future__ import annotations

import unittest
from datetime import UTC, date, datetime
from decimal import Decimal

from mi_gobierno_transparente.domain.entities import (
    EvaluacionPrecio,
    PrecioMercado,
    PrecioReportado,
    Producto,
)
from mi_gobierno_transparente.domain.services import EvaluadorPrecio
from mi_gobierno_transparente.domain.value_objects import (
    CategoriaProducto,
    Dinero,
    UnidadMedida,
)
from mi_gobierno_transparente.infrastructure.exceptions import DocumentoInvalidoError
from mi_gobierno_transparente.infrastructure.firestore_documents import (
    dinero_a_documento,
    evaluacion_a_documento,
    evaluacion_desde_documento,
    precio_mercado_a_documento,
    precio_mercado_desde_documento,
    precio_reportado_a_documento,
    precio_reportado_desde_documento,
    producto_a_documento,
    producto_desde_documento,
)


class TestFirestoreDocuments(unittest.TestCase):
    def setUp(self) -> None:
        self.producto = Producto(
            id="prod-1",
            nombre="Arroz extra",
            categoria=CategoriaProducto.ALIMENTOS,
            unidad_medida=UnidadMedida.KILOGRAMO,
            marca="Costeño",
            descripcion="Arroz grano largo",
        )
        self.precio_mercado = PrecioMercado(
            id="pm-1",
            producto_id=self.producto.id,
            precio=Dinero(Decimal("4.50")),
            fuente="DGCP",
            fecha_registro=date(2026, 2, 1),
        )
        self.precio_reportado = PrecioReportado(
            id="rep-1",
            producto_id=self.producto.id,
            precio=Dinero(Decimal("5.20")),
            establecimiento="Bodega Central",
            fecha_reporte=date(2026, 2, 2),
            distrito="Lima",
            reportado_por="Ciudadano",
        )

    def test_round_trip_de_producto(self) -> None:
        documento = producto_a_documento(self.producto)

        recuperado = producto_desde_documento(documento, documento_id="prod-1")

        self.assertEqual(recuperado, self.producto)
        self.assertEqual(documento["nombre_normalizado"], "arroz extra")

    def test_round_trip_de_precio_mercado(self) -> None:
        documento = precio_mercado_a_documento(self.precio_mercado)

        recuperado = precio_mercado_desde_documento(
            documento,
            documento_id="pm-1",
        )

        self.assertEqual(recuperado, self.precio_mercado)
        self.assertEqual(documento["fecha_registro"], "2026-02-01")
        self.assertEqual(documento["precio"], {"monto": "4.50", "moneda": "PEN"})

    def test_round_trip_de_precio_reportado(self) -> None:
        documento = precio_reportado_a_documento(self.precio_reportado)

        recuperado = precio_reportado_desde_documento(
            documento,
            documento_id="rep-1",
        )

        self.assertEqual(recuperado, self.precio_reportado)

    def test_round_trip_de_evaluacion(self) -> None:
        evaluador = EvaluadorPrecio()
        resultado = evaluador.evaluar(
            precio_reportado=self.precio_reportado.precio,
            precio_mercado=self.precio_mercado.precio,
        )
        evaluacion = EvaluacionPrecio(
            id="eval-1",
            producto_id=self.producto.id,
            precio_reportado_id=self.precio_reportado.id,
            precio_mercado_id=self.precio_mercado.id,
            resultado=resultado,
            evaluado_en=datetime(2026, 2, 2, 12, 0, tzinfo=UTC),
            version_regla=evaluador.version,
            observacion="Revisión ciudadana",
        )

        documento = evaluacion_a_documento(evaluacion)
        recuperada = evaluacion_desde_documento(documento, documento_id="eval-1")

        self.assertEqual(recuperada, evaluacion)
        self.assertEqual(documento["resultado"]["nivel_riesgo"], "alto_riesgo")
        self.assertEqual(documento["resultado"]["sobreprecio"], "0.1555555555555555555555555556")

    def test_dinero_se_serializa_como_texto(self) -> None:
        documento = dinero_a_documento(Dinero(Decimal("1234.5")))

        self.assertEqual(documento, {"monto": "1234.50", "moneda": "PEN"})

    def test_documento_invalido_lanza_error_de_infraestructura(self) -> None:
        with self.assertRaises(DocumentoInvalidoError):
            producto_desde_documento({"nombre": "Sin categoría"})

    def test_documento_con_categoria_no_permitida_es_invalido(self) -> None:
        documento = producto_a_documento(self.producto)
        documento["categoria"] = "electronica"

        with self.assertRaises(DocumentoInvalidoError):
            producto_desde_documento(documento, documento_id="prod-1")


if __name__ == "__main__":
    unittest.main()

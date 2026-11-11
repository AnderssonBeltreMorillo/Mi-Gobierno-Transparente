"""Pruebas de las utilidades de parseo de los adaptadores."""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from mi_gobierno_transparente.infrastructure.parsing import (
    normalizar_moneda,
    parsear_fecha,
    parsear_precio,
    precio_desde_numero,
    texto_opcional,
)


class TestParsing(unittest.TestCase):
    def test_parsear_precio_con_simbolo_de_sol(self) -> None:
        monto, moneda = parsear_precio("S/ 1,234.50")

        self.assertEqual(monto, Decimal("1234.50"))
        self.assertEqual(moneda, "PEN")

    def test_parsear_precio_en_dolares(self) -> None:
        monto, moneda = parsear_precio("US$ 12.99")

        self.assertEqual(monto, Decimal("12.99"))
        self.assertEqual(moneda, "USD")

    def test_parsear_precio_con_separadores_europeos(self) -> None:
        monto, moneda = parsear_precio("1.234,50")

        self.assertEqual(monto, Decimal("1234.50"))
        self.assertEqual(moneda, "PEN")

    def test_parsear_precio_invalido_devuelve_none(self) -> None:
        monto, moneda = parsear_precio("sin precio")

        self.assertIsNone(monto)
        self.assertEqual(moneda, "PEN")

    def test_normalizar_moneda_reconoce_simbolos_y_codigos(self) -> None:
        self.assertEqual(normalizar_moneda("S/"), "PEN")
        self.assertEqual(normalizar_moneda("US$"), "USD")
        self.assertEqual(normalizar_moneda("eur"), "EUR")
        self.assertEqual(normalizar_moneda(None), "PEN")

    def test_parsear_fecha_en_formatos_habituales(self) -> None:
        self.assertEqual(parsear_fecha("01/02/2026"), date(2026, 2, 1))
        self.assertEqual(parsear_fecha("2026-02-01"), date(2026, 2, 1))
        self.assertIsNone(parsear_fecha("no es fecha"))

    def test_precio_desde_numero_no_usa_float_puro(self) -> None:
        self.assertEqual(precio_desde_numero(25.9), Decimal("25.9"))
        self.assertEqual(precio_desde_numero("S/ 8.50"), Decimal("8.50"))
        self.assertIsNone(precio_desde_numero(True))

    def test_texto_opcional_colapsa_espacios(self) -> None:
        self.assertEqual(texto_opcional("  hola   mundo "), "hola mundo")
        self.assertIsNone(texto_opcional("   "))
        self.assertIsNone(texto_opcional(None))


if __name__ == "__main__":
    unittest.main()

"""Pruebas del objeto de valor Dinero."""

from __future__ import annotations

import unittest
from decimal import Decimal

from mi_gobierno_transparente.domain.exceptions import (
    MonedaIncompatibleError,
    PrecioInvalidoError,
)
from mi_gobierno_transparente.domain.value_objects import Dinero


class TestDinero(unittest.TestCase):
    def test_normaliza_a_dos_decimales_con_redondeo_comercial(self) -> None:
        self.assertEqual(Dinero(Decimal("10.005")).monto, Decimal("10.01"))
        self.assertEqual(Dinero(Decimal("10.004")).monto, Decimal("10.00"))

    def test_rechaza_float(self) -> None:
        with self.assertRaises(PrecioInvalidoError):
            Dinero(10.5)  # type: ignore[arg-type]

    def test_rechaza_monto_negativo(self) -> None:
        with self.assertRaises(PrecioInvalidoError):
            Dinero(Decimal("-1"))

    def test_rechaza_moneda_invalida(self) -> None:
        with self.assertRaises(PrecioInvalidoError):
            Dinero(Decimal("10"), "SOLES")

    def test_suma_y_resta(self) -> None:
        total = Dinero(Decimal("10.50")).sumar(Dinero(Decimal("2.25")))
        self.assertEqual(total, Dinero(Decimal("12.75")))

        diferencia = total.restar(Dinero(Decimal("2.25")))
        self.assertEqual(diferencia, Dinero(Decimal("10.50")))

    def test_resta_no_permite_resultado_negativo(self) -> None:
        with self.assertRaises(PrecioInvalidoError):
            Dinero(Decimal("5")).restar(Dinero(Decimal("6")))

    def test_excedente_se_acota_a_cero(self) -> None:
        self.assertEqual(
            Dinero(Decimal("80")).excedente_sobre(Dinero(Decimal("100"))),
            Dinero(Decimal("0")),
        )
        self.assertEqual(
            Dinero(Decimal("120")).excedente_sobre(Dinero(Decimal("100"))),
            Dinero(Decimal("20")),
        )

    def test_rechaza_operaciones_entre_monedas(self) -> None:
        with self.assertRaises(MonedaIncompatibleError):
            Dinero(Decimal("10"), "PEN").sumar(Dinero(Decimal("10"), "USD"))

    def test_desde_texto(self) -> None:
        self.assertEqual(Dinero.desde_texto("12.5"), Dinero(Decimal("12.50")))

        with self.assertRaises(PrecioInvalidoError):
            Dinero.desde_texto("doce soles")

    def test_formateado(self) -> None:
        self.assertEqual(Dinero(Decimal("1234.5")).formateado(), "S/ 1,234.50")
        self.assertEqual(Dinero(Decimal("10"), "USD").formateado(), "US$ 10.00")


if __name__ == "__main__":
    unittest.main()

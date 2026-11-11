"""Pruebas del objeto de valor Porcentaje."""

from __future__ import annotations

import unittest
from decimal import Decimal

from mi_gobierno_transparente.domain.exceptions import PorcentajeInvalidoError
from mi_gobierno_transparente.domain.value_objects import Porcentaje


class TestPorcentaje(unittest.TestCase):
    def test_desde_porcentaje(self) -> None:
        porcentaje = Porcentaje.desde_porcentaje(Decimal("15"))
        self.assertEqual(porcentaje.fraccion, Decimal("0.15"))
        self.assertEqual(porcentaje.como_porcentaje(), Decimal("15.00"))

    def test_formateado(self) -> None:
        self.assertEqual(Porcentaje(Decimal("0.155")).formateado(), "15.50 %")
        self.assertEqual(Porcentaje.cero().formateado(), "0.00 %")

    def test_comparaciones(self) -> None:
        quince = Porcentaje.desde_porcentaje(Decimal("15"))
        diez = Porcentaje.desde_porcentaje(Decimal("10"))

        self.assertTrue(quince.es_mayor_que(diez))
        self.assertTrue(diez.es_menor_que(quince))
        self.assertTrue(quince.es_mayor_o_igual_que(quince))
        self.assertTrue(quince.es_menor_o_igual_que(quince))

    def test_rechaza_float(self) -> None:
        with self.assertRaises(PorcentajeInvalidoError):
            Porcentaje(0.15)  # type: ignore[arg-type]

    def test_rechaza_perdida_mayor_al_cien_por_ciento(self) -> None:
        with self.assertRaises(PorcentajeInvalidoError):
            Porcentaje(Decimal("-1.01"))


if __name__ == "__main__":
    unittest.main()

"""Pruebas del servicio de dominio EvaluadorPrecio.

Casos límite de la regla:
- <= 0 %: precio justo.
- (0 %, 1 %): banda de tolerancia, precio justo.
- 1 % a 15 %: alerta amarilla.
- > 15 %: alto riesgo.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from mi_gobierno_transparente.domain.exceptions import (
    MonedaIncompatibleError,
    PrecioInvalidoError,
)
from mi_gobierno_transparente.domain.services import EvaluadorPrecio
from mi_gobierno_transparente.domain.value_objects import (
    Dinero,
    NivelRiesgo,
    Porcentaje,
    ResultadoEvaluacion,
    UmbralesEvaluacion,
)


class TestEvaluadorPrecio(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluador = EvaluadorPrecio()

    def _evaluar(
        self,
        reportado: str,
        mercado: str,
        *,
        evaluador: EvaluadorPrecio | None = None,
    ) -> ResultadoEvaluacion:
        servicio = evaluador or self.evaluador
        return servicio.evaluar(
            precio_reportado=Dinero(Decimal(reportado)),
            precio_mercado=Dinero(Decimal(mercado)),
        )

    def test_precio_igual_al_mercado_es_justo(self) -> None:
        resultado = self._evaluar("100", "100")

        self.assertIs(resultado.nivel_riesgo, NivelRiesgo.PRECIO_JUSTO)
        self.assertEqual(resultado.sobreprecio.como_porcentaje(), Decimal("0.00"))
        self.assertEqual(resultado.excedente, Dinero(Decimal("0")))
        self.assertFalse(resultado.dentro_de_tolerancia)

    def test_precio_por_debajo_del_mercado_es_justo(self) -> None:
        resultado = self._evaluar("80", "100")

        self.assertIs(resultado.nivel_riesgo, NivelRiesgo.PRECIO_JUSTO)
        self.assertEqual(resultado.sobreprecio, Porcentaje.cero())
        self.assertEqual(resultado.excedente, Dinero(Decimal("0")))

    def test_sobreprecio_menor_al_uno_por_ciento_es_tolerancia(self) -> None:
        resultado = self._evaluar("100.50", "100")

        self.assertIs(resultado.nivel_riesgo, NivelRiesgo.PRECIO_JUSTO)
        self.assertTrue(resultado.dentro_de_tolerancia)
        self.assertEqual(resultado.sobreprecio.como_porcentaje(), Decimal("0.50"))
        self.assertEqual(resultado.excedente, Dinero(Decimal("0.50")))

    def test_sobreprecio_de_uno_por_ciento_es_alerta_amarilla(self) -> None:
        resultado = self._evaluar("101", "100")

        self.assertIs(resultado.nivel_riesgo, NivelRiesgo.ALERTA_AMARILLA)
        self.assertEqual(resultado.sobreprecio.como_porcentaje(), Decimal("1.00"))
        self.assertTrue(resultado.requiere_intervencion)

    def test_sobreprecio_de_diez_por_ciento_es_alerta_amarilla(self) -> None:
        resultado = self._evaluar("110", "100")

        self.assertIs(resultado.nivel_riesgo, NivelRiesgo.ALERTA_AMARILLA)
        self.assertEqual(resultado.sobreprecio.como_porcentaje(), Decimal("10.00"))

    def test_sobreprecio_de_quince_por_ciento_sigue_siendo_alerta_amarilla(self) -> None:
        resultado = self._evaluar("115", "100")

        self.assertIs(resultado.nivel_riesgo, NivelRiesgo.ALERTA_AMARILLA)
        self.assertEqual(resultado.sobreprecio.como_porcentaje(), Decimal("15.00"))
        self.assertEqual(resultado.excedente, Dinero(Decimal("15")))

    def test_sobreprecio_mayor_al_quince_por_ciento_es_alto_riesgo(self) -> None:
        resultado = self._evaluar("115.01", "100")

        self.assertIs(resultado.nivel_riesgo, NivelRiesgo.ALTO_RIESGO)
        self.assertEqual(resultado.sobreprecio.como_porcentaje(), Decimal("15.01"))
        self.assertTrue(resultado.requiere_intervencion)

    def test_sobreprecio_del_cincuenta_por_ciento_es_alto_riesgo(self) -> None:
        resultado = self._evaluar("150", "100")

        self.assertIs(resultado.nivel_riesgo, NivelRiesgo.ALTO_RIESGO)
        self.assertEqual(resultado.sobreprecio.como_porcentaje(), Decimal("50.00"))
        self.assertEqual(resultado.excedente, Dinero(Decimal("50")))

    def test_umbral_de_alerta_configurable_en_cero(self) -> None:
        evaluador = EvaluadorPrecio(
            UmbralesEvaluacion(alerta_amarilla_desde=Porcentaje.cero())
        )
        resultado = self._evaluar("100.50", "100", evaluador=evaluador)

        self.assertIs(resultado.nivel_riesgo, NivelRiesgo.ALERTA_AMARILLA)
        self.assertFalse(resultado.dentro_de_tolerancia)

    def test_rechaza_monedas_distintas(self) -> None:
        with self.assertRaises(MonedaIncompatibleError):
            self.evaluador.evaluar(
                precio_reportado=Dinero(Decimal("120"), "USD"),
                precio_mercado=Dinero(Decimal("100"), "PEN"),
            )

    def test_rechaza_precio_de_mercado_cero(self) -> None:
        with self.assertRaises(PrecioInvalidoError):
            self.evaluador.evaluar(
                precio_reportado=Dinero(Decimal("10")),
                precio_mercado=Dinero(Decimal("0")),
            )


if __name__ == "__main__":
    unittest.main()

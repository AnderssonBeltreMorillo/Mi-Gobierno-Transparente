"""Objeto de valor para porcentajes.

Internamente se almacena la fracción (``0.15``), no el valor porcentual (``15``).
Esto evita confusiones al comparar con umbrales.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ..exceptions import PorcentajeInvalidoError

_DOS_DECIMALES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Porcentaje:
    """Porcentaje inmutable almacenado como fracción decimal.

    Ejemplos:
    - ``Porcentaje(Decimal("0.15"))`` equivale a 15 %.
    - ``Porcentaje.desde_porcentaje(Decimal("15"))`` también equivale a 15 %.
    """

    fraccion: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.fraccion, Decimal):
            raise PorcentajeInvalidoError("El porcentaje debe construirse con Decimal.")
        if not self.fraccion.is_finite():
            raise PorcentajeInvalidoError("El porcentaje debe ser un número finito.")
        if self.fraccion < Decimal("-1"):
            raise PorcentajeInvalidoError(
                "Un porcentaje no puede representar una pérdida mayor al 100 %."
            )

    @classmethod
    def cero(cls) -> Porcentaje:
        """Porcentaje neutro (0 %)."""
        return cls(Decimal("0"))

    @classmethod
    def desde_porcentaje(cls, valor: Decimal) -> Porcentaje:
        """Construye el porcentaje a partir del valor porcentual (``15`` -> ``0.15``)."""
        if not isinstance(valor, Decimal):
            raise PorcentajeInvalidoError("El valor porcentual debe ser un Decimal.")
        return cls(valor / Decimal("100"))

    def como_porcentaje(self) -> Decimal:
        """Devuelve el valor porcentual redondeado a dos decimales (``0.155`` -> ``15.50``)."""
        return (self.fraccion * Decimal("100")).quantize(_DOS_DECIMALES, rounding=ROUND_HALF_UP)

    def es_cero(self) -> bool:
        return self.fraccion == Decimal("0")

    def es_positivo(self) -> bool:
        return self.fraccion > Decimal("0")

    def comparar(self, otro: Porcentaje) -> int:
        """Devuelve -1, 0 o 1 según la comparación con ``otro``."""
        self._verificar_tipo(otro)
        return (self.fraccion > otro.fraccion) - (self.fraccion < otro.fraccion)

    def es_mayor_que(self, otro: Porcentaje) -> bool:
        return self.comparar(otro) > 0

    def es_menor_que(self, otro: Porcentaje) -> bool:
        return self.comparar(otro) < 0

    def es_mayor_o_igual_que(self, otro: Porcentaje) -> bool:
        return self.comparar(otro) >= 0

    def es_menor_o_igual_que(self, otro: Porcentaje) -> bool:
        return self.comparar(otro) <= 0

    def formateado(self) -> str:
        """Representación legible, por ejemplo ``15.50 %``."""
        return f"{self.como_porcentaje():.2f} %"

    def _verificar_tipo(self, otro: Porcentaje) -> None:
        if not isinstance(otro, Porcentaje):
            raise PorcentajeInvalidoError("Solo se pueden comparar porcentajes entre sí.")

    def __str__(self) -> str:
        return self.formateado()

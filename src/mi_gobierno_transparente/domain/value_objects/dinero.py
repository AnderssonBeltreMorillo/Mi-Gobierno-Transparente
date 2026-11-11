"""Objeto de valor para importes monetarios.

Se usa ``Decimal`` (nunca ``float``) para evitar errores de redondeo en precios.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from ..exceptions import MonedaIncompatibleError, PrecioInvalidoError

_CENTIMOS = Decimal("0.01")
_SIMBOLOS: dict[str, str] = {"PEN": "S/", "USD": "US$"}


@dataclass(frozen=True, slots=True)
class Dinero:
    """Importe inmutable expresado en una moneda ISO 4217.

    Invariantes:
    - El monto es un ``Decimal`` finito y no negativo.
    - Se normaliza a dos decimales con redondeo comercial (half-up).
    - La moneda se guarda en mayúsculas (por ejemplo ``PEN``).
    """

    monto: Decimal
    moneda: str = "PEN"

    def __post_init__(self) -> None:
        if not isinstance(self.monto, Decimal):
            raise PrecioInvalidoError(
                "El monto debe ser un Decimal (nunca float) para evitar errores de redondeo."
            )
        if not self.monto.is_finite():
            raise PrecioInvalidoError("El monto debe ser un número finito.")
        if self.monto < Decimal("0"):
            raise PrecioInvalidoError("El monto no puede ser negativo.")
        if not isinstance(self.moneda, str):
            raise PrecioInvalidoError("La moneda debe ser un texto ISO 4217.")

        moneda = self.moneda.strip().upper()
        if len(moneda) != 3 or not moneda.isalpha():
            raise PrecioInvalidoError(
                "La moneda debe ser un código ISO 4217 de tres letras, por ejemplo 'PEN'."
            )

        object.__setattr__(self, "monto", self.monto.quantize(_CENTIMOS, rounding=ROUND_HALF_UP))
        object.__setattr__(self, "moneda", moneda)

    @classmethod
    def cero(cls, moneda: str = "PEN") -> Dinero:
        """Devuelve un importe de cero en la moneda indicada."""
        return cls(Decimal("0"), moneda)

    @classmethod
    def desde_texto(cls, valor: str, moneda: str = "PEN") -> Dinero:
        """Construye un importe a partir de un texto decimal (por ejemplo ``"12.50"``)."""
        try:
            monto = Decimal(valor.strip())
        except (AttributeError, InvalidOperation) as exc:
            raise PrecioInvalidoError(f"'{valor}' no es un monto válido.") from exc
        return cls(monto, moneda)

    def sumar(self, otro: Dinero) -> Dinero:
        """Suma dos importes de la misma moneda."""
        self._verificar_misma_moneda(otro)
        return Dinero(self.monto + otro.monto, self.moneda)

    def restar(self, otro: Dinero) -> Dinero:
        """Resta dos importes de la misma moneda; el resultado no puede ser negativo."""
        self._verificar_misma_moneda(otro)
        if otro.monto > self.monto:
            raise PrecioInvalidoError("El resultado de la resta no puede ser negativo.")
        return Dinero(self.monto - otro.monto, self.moneda)

    def excedente_sobre(self, referencia: Dinero) -> Dinero:
        """Diferencia positiva respecto a una referencia; cero si el precio es menor."""
        self._verificar_misma_moneda(referencia)
        diferencia = self.monto - referencia.monto
        return Dinero(max(diferencia, Decimal("0")), self.moneda)

    def multiplicar(self, factor: Decimal) -> Dinero:
        """Multiplica el importe por un factor decimal no negativo."""
        if not isinstance(factor, Decimal) or not factor.is_finite() or factor < Decimal("0"):
            raise PrecioInvalidoError("El factor debe ser un Decimal finito no negativo.")
        return Dinero(self.monto * factor, self.moneda)

    def comparar(self, otro: Dinero) -> int:
        """Devuelve -1, 0 o 1 según la comparación con ``otro``."""
        self._verificar_misma_moneda(otro)
        return (self.monto > otro.monto) - (self.monto < otro.monto)

    def es_mayor_que(self, otro: Dinero) -> bool:
        return self.comparar(otro) > 0

    def es_menor_que(self, otro: Dinero) -> bool:
        return self.comparar(otro) < 0

    def es_cero(self) -> bool:
        return self.monto == Decimal("0")

    def formateado(self) -> str:
        """Representación legible, por ejemplo ``S/ 1,234.50``."""
        simbolo = _SIMBOLOS.get(self.moneda, self.moneda)
        return f"{simbolo} {self.monto:,.2f}"

    def _verificar_misma_moneda(self, otro: Dinero) -> None:
        if self.moneda != otro.moneda:
            raise MonedaIncompatibleError(
                f"No se pueden operar montos en {self.moneda} y {otro.moneda}."
            )

    def __str__(self) -> str:
        return self.formateado()

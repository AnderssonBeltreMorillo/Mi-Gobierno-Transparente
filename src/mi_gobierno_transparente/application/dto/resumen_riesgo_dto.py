"""DTO de salida para el tablero de riesgo."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_DOS_DECIMALES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class ResumenRiesgoDTO:
    """Conteo agregado de evaluaciones por nivel de riesgo."""

    total_evaluaciones: int
    precio_justo: int
    alerta_amarilla: int
    alto_riesgo: int

    @property
    def porcentaje_alto_riesgo(self) -> Decimal:
        """Porcentaje de evaluaciones en alto riesgo (0.00 si no hay datos)."""
        if self.total_evaluaciones == 0:
            return Decimal("0.00")
        proporcion = Decimal(self.alto_riesgo) / Decimal(self.total_evaluaciones)
        return (proporcion * Decimal("100")).quantize(_DOS_DECIMALES, rounding=ROUND_HALF_UP)

    def to_dict(self) -> dict[str, object]:
        """Serializa a primitivas JSON-friendly."""
        return {
            "total_evaluaciones": self.total_evaluaciones,
            "precio_justo": self.precio_justo,
            "alerta_amarilla": self.alerta_amarilla,
            "alto_riesgo": self.alto_riesgo,
            "porcentaje_alto_riesgo": str(self.porcentaje_alto_riesgo),
        }

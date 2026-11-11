"""DTO de salida para precios reportados."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PrecioReportadoDTO:
    """Precio observado en un establecimiento."""

    id: str
    producto_id: str
    monto: Decimal
    moneda: str
    establecimiento: str
    distrito: str | None
    reportado_por: str | None
    fecha_reporte: date

    def to_dict(self) -> dict[str, object]:
        """Serializa a primitivas JSON-friendly (el monto va como texto)."""
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "monto": str(self.monto),
            "moneda": self.moneda,
            "establecimiento": self.establecimiento,
            "distrito": self.distrito,
            "reportado_por": self.reportado_por,
            "fecha_reporte": self.fecha_reporte.isoformat(),
        }

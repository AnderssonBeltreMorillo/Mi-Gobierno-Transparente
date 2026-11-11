"""DTO de salida para precios de mercado."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PrecioMercadoDTO:
    """Precio de referencia vigente o histórico."""

    id: str
    producto_id: str
    monto: Decimal
    moneda: str
    fuente: str
    fecha_registro: date
    vigente: bool

    def to_dict(self) -> dict[str, object]:
        """Serializa a primitivas JSON-friendly (el monto va como texto)."""
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "monto": str(self.monto),
            "moneda": self.moneda,
            "fuente": self.fuente,
            "fecha_registro": self.fecha_registro.isoformat(),
            "vigente": self.vigente,
        }

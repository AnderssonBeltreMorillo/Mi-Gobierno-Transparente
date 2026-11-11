"""DTO de salida para evaluaciones de precio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ...domain.value_objects.nivel_riesgo import NivelRiesgo


@dataclass(frozen=True, slots=True)
class EvaluacionDTO:
    """Foto auditable de una comparación entre precio reportado y de mercado."""

    id: str
    producto_id: str
    precio_reportado_id: str
    precio_mercado_id: str
    monto_reportado: Decimal
    monto_mercado: Decimal
    moneda: str
    diferencia: Decimal
    excedente: Decimal
    sobreprecio_porcentaje: Decimal
    nivel_riesgo: NivelRiesgo
    dentro_de_tolerancia: bool
    requiere_intervencion: bool
    alerta_amarilla_desde_porcentaje: Decimal
    alto_riesgo_desde_porcentaje: Decimal
    evaluado_en: datetime
    version_regla: str
    observacion: str | None

    def to_dict(self) -> dict[str, object]:
        """Serializa a primitivas JSON-friendly (los montos van como texto)."""
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "precio_reportado_id": self.precio_reportado_id,
            "precio_mercado_id": self.precio_mercado_id,
            "monto_reportado": str(self.monto_reportado),
            "monto_mercado": str(self.monto_mercado),
            "moneda": self.moneda,
            "diferencia": str(self.diferencia),
            "excedente": str(self.excedente),
            "sobreprecio_porcentaje": str(self.sobreprecio_porcentaje),
            "nivel_riesgo": self.nivel_riesgo.value,
            "dentro_de_tolerancia": self.dentro_de_tolerancia,
            "requiere_intervencion": self.requiere_intervencion,
            "alerta_amarilla_desde_porcentaje": str(
                self.alerta_amarilla_desde_porcentaje
            ),
            "alto_riesgo_desde_porcentaje": str(self.alto_riesgo_desde_porcentaje),
            "evaluado_en": self.evaluado_en.isoformat(),
            "version_regla": self.version_regla,
            "observacion": self.observacion,
        }

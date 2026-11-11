"""Entidad PrecioReportado: precio observado en un establecimiento."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..exceptions import PrecioInvalidoError
from ..value_objects.dinero import Dinero
from ._validacion import (
    exigir_fecha,
    exigir_identificador,
    exigir_texto,
    limpiar_texto_opcional,
)


@dataclass(frozen=True, slots=True)
class PrecioReportado:
    """Precio declarado por un ciudadano, una bodega o un fiscalizador."""

    id: str
    producto_id: str
    precio: Dinero
    establecimiento: str
    fecha_reporte: date
    distrito: str | None = None
    reportado_por: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            exigir_identificador(self.id, campo="id", error=PrecioInvalidoError),
        )
        object.__setattr__(
            self,
            "producto_id",
            exigir_identificador(self.producto_id, campo="producto_id", error=PrecioInvalidoError),
        )
        if not isinstance(self.precio, Dinero):
            raise PrecioInvalidoError("El precio reportado debe ser un Dinero.")
        if self.precio.es_cero():
            raise PrecioInvalidoError("El precio reportado debe ser mayor que cero.")
        object.__setattr__(
            self,
            "establecimiento",
            exigir_texto(
                self.establecimiento,
                campo="establecimiento",
                minimo=2,
                maximo=150,
                error=PrecioInvalidoError,
            ),
        )
        object.__setattr__(
            self,
            "fecha_reporte",
            exigir_fecha(
                self.fecha_reporte,
                campo="fecha_reporte",
                error=PrecioInvalidoError,
            ),
        )
        object.__setattr__(
            self,
            "distrito",
            limpiar_texto_opcional(
                self.distrito,
                campo="distrito",
                maximo=100,
                error=PrecioInvalidoError,
            ),
        )
        object.__setattr__(
            self,
            "reportado_por",
            limpiar_texto_opcional(
                self.reportado_por,
                campo="reportado_por",
                maximo=120,
                error=PrecioInvalidoError,
            ),
        )

    @property
    def moneda(self) -> str:
        return self.precio.moneda

    def es_del_producto(self, producto_id: str) -> bool:
        """Verifica la coherencia entre el reporte y el producto evaluado."""
        return self.producto_id == producto_id

    def __str__(self) -> str:
        return f"{self.precio} en {self.establecimiento} ({self.fecha_reporte.isoformat()})"

"""Entidad PrecioMercado: precio de referencia para un producto."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from ..exceptions import PrecioInvalidoError
from ..value_objects.dinero import Dinero
from ._validacion import (
    exigir_booleano,
    exigir_fecha,
    exigir_identificador,
    exigir_texto,
)


@dataclass(frozen=True, slots=True)
class PrecioMercado:
    """Precio de referencia (por ejemplo, de un mercado mayorista o del INEI).

    Solo puede existir un precio vigente por producto; el repositorio es quien
    garantiza esa invariante al reemplazar el anterior.
    """

    id: str
    producto_id: str
    precio: Dinero
    fuente: str
    fecha_registro: date
    vigente: bool = True

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
            raise PrecioInvalidoError("El precio de mercado debe ser un Dinero.")
        if self.precio.es_cero():
            raise PrecioInvalidoError("El precio de mercado debe ser mayor que cero.")
        object.__setattr__(
            self,
            "fuente",
            exigir_texto(
                self.fuente,
                campo="fuente",
                minimo=3,
                maximo=150,
                error=PrecioInvalidoError,
            ),
        )
        object.__setattr__(
            self,
            "fecha_registro",
            exigir_fecha(
                self.fecha_registro,
                campo="fecha_registro",
                error=PrecioInvalidoError,
            ),
        )
        object.__setattr__(
            self,
            "vigente",
            exigir_booleano(self.vigente, campo="vigente", error=PrecioInvalidoError),
        )

    @property
    def moneda(self) -> str:
        return self.precio.moneda

    def es_vigente_en(self, fecha: date) -> bool:
        """Indica si este precio puede usarse como referencia en ``fecha``."""
        return self.vigente and self.fecha_registro <= fecha

    def desactivar(self) -> PrecioMercado:
        """Devuelve una copia no vigente."""
        return replace(self, vigente=False)

    def __str__(self) -> str:
        return f"{self.precio} ({self.fuente}, {self.fecha_registro.isoformat()})"

"""Umbrales configurables para clasificar el sobreprecio.

Decisión de arquitectura
------------------------
La regla original define ``Precio Justo (<= mercado)``, ``Alerta Amarilla
(1 % - 15 %)`` y ``Alto Riesgo (> 15 %)``, dejando sin cubrir el intervalo
``(0 %, 1 %)``. Para no dejar precios sin clasificar, ese intervalo se trata
como **banda de tolerancia operativa** y se reporta como ``PRECIO_JUSTO``.
Si se desea una lectura estricta, basta con construir los umbrales con
``alerta_amarilla_desde=Porcentaje.cero()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..exceptions import UmbralesInvalidosError
from .nivel_riesgo import NivelRiesgo
from .porcentaje import Porcentaje


@dataclass(frozen=True, slots=True)
class UmbralesEvaluacion:
    """Umbrales que determinan el nivel de riesgo de un sobreprecio.

    Invariantes:
    - ``alerta_amarilla_desde`` es mayor o igual a 0.
    - ``alto_riesgo_desde`` es estrictamente mayor que ``alerta_amarilla_desde``.
    """

    alerta_amarilla_desde: Porcentaje = Porcentaje(Decimal("0.01"))
    alto_riesgo_desde: Porcentaje = Porcentaje(Decimal("0.15"))

    def __post_init__(self) -> None:
        if not isinstance(self.alerta_amarilla_desde, Porcentaje):
            raise UmbralesInvalidosError("El umbral de alerta amarilla debe ser un Porcentaje.")
        if not isinstance(self.alto_riesgo_desde, Porcentaje):
            raise UmbralesInvalidosError("El umbral de alto riesgo debe ser un Porcentaje.")
        if self.alerta_amarilla_desde.fraccion < Decimal("0"):
            raise UmbralesInvalidosError("El umbral de alerta amarilla no puede ser negativo.")
        if self.alto_riesgo_desde.es_menor_o_igual_que(self.alerta_amarilla_desde):
            raise UmbralesInvalidosError(
                "El umbral de alto riesgo debe ser mayor que el de alerta amarilla."
            )

    def clasificar(self, sobreprecio: Porcentaje) -> NivelRiesgo:
        """Clasifica un sobreprecio (fracción) según los umbrales configurados."""
        if not isinstance(sobreprecio, Porcentaje):
            raise UmbralesInvalidosError("El sobreprecio debe ser un Porcentaje.")

        if not sobreprecio.es_positivo():
            return NivelRiesgo.PRECIO_JUSTO
        if sobreprecio.es_menor_que(self.alerta_amarilla_desde):
            return NivelRiesgo.PRECIO_JUSTO
        if sobreprecio.es_menor_o_igual_que(self.alto_riesgo_desde):
            return NivelRiesgo.ALERTA_AMARILLA
        return NivelRiesgo.ALTO_RIESGO

    @classmethod
    def estandar(cls) -> UmbralesEvaluacion:
        """Umbrales por defecto del demo (1 % y 15 %)."""
        return cls()

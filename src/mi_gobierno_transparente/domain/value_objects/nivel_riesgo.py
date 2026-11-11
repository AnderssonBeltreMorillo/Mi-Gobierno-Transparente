"""Niveles de riesgo resultantes de evaluar un precio reportado."""

from __future__ import annotations

from enum import StrEnum


class NivelRiesgo(StrEnum):
    """Clasificación de riesgo de un sobreprecio.

    - ``PRECIO_JUSTO``: precio igual o por debajo del mercado (o dentro de la
      banda de tolerancia configurada).
    - ``ALERTA_AMARILLA``: sobreprecio entre el umbral de alerta y el umbral alto.
    - ``ALTO_RIESGO``: sobreprecio superior al umbral alto.
    """

    PRECIO_JUSTO = "precio_justo"
    ALERTA_AMARILLA = "alerta_amarilla"
    ALTO_RIESGO = "alto_riesgo"

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS[self]

    @property
    def prioridad(self) -> int:
        """Prioridad de atención: 0 (ninguna), 1 (amarilla), 2 (alta)."""
        return _PRIORIDADES[self]

    @property
    def requiere_intervencion(self) -> bool:
        """Solo los niveles amarillo y alto requieren acción."""
        return self is not NivelRiesgo.PRECIO_JUSTO

    def __str__(self) -> str:
        return self.value


_ETIQUETAS: dict[NivelRiesgo, str] = {
    NivelRiesgo.PRECIO_JUSTO: "Precio justo",
    NivelRiesgo.ALERTA_AMARILLA: "Alerta amarilla",
    NivelRiesgo.ALTO_RIESGO: "Alto riesgo",
}

_PRIORIDADES: dict[NivelRiesgo, int] = {
    NivelRiesgo.PRECIO_JUSTO: 0,
    NivelRiesgo.ALERTA_AMARILLA: 1,
    NivelRiesgo.ALTO_RIESGO: 2,
}

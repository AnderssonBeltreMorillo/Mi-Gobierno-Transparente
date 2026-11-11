"""Caso de uso: obtener el resumen de riesgo para el tablero."""

from __future__ import annotations

from ...domain.value_objects.nivel_riesgo import NivelRiesgo
from ..dto.queries import ObtenerResumenRiesgoQuery
from ..dto.resumen_riesgo_dto import ResumenRiesgoDTO
from ..ports.repositories import EvaluacionPrecioRepositorio


class ObtenerResumenRiesgo:
    """Agrega las evaluaciones por nivel de riesgo (global o por producto)."""

    def __init__(self, evaluaciones: EvaluacionPrecioRepositorio) -> None:
        self._evaluaciones = evaluaciones

    def ejecutar(self, consulta: ObtenerResumenRiesgoQuery) -> ResumenRiesgoDTO:
        """Devuelve el conteo por nivel y el porcentaje de alto riesgo."""
        conteo = self._evaluaciones.resumen_por_nivel(producto_id=consulta.producto_id)
        return ResumenRiesgoDTO(
            total_evaluaciones=sum(conteo.values()),
            precio_justo=conteo.get(NivelRiesgo.PRECIO_JUSTO, 0),
            alerta_amarilla=conteo.get(NivelRiesgo.ALERTA_AMARILLA, 0),
            alto_riesgo=conteo.get(NivelRiesgo.ALTO_RIESGO, 0),
        )

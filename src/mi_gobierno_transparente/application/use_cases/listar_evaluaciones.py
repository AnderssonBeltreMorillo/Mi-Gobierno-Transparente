"""Caso de uso: listar evaluaciones con filtros."""

from __future__ import annotations

from ..dto.evaluacion_dto import EvaluacionDTO
from ..dto.queries import ListarEvaluacionesQuery
from ..mappers import a_evaluacion_dto
from ..ports.repositories import EvaluacionPrecioRepositorio
from ._comun import validar_paginacion, validar_rango_fechas


class ListarEvaluaciones:
    """Devuelve evaluaciones filtradas por producto, nivel de riesgo y fechas."""

    def __init__(self, evaluaciones: EvaluacionPrecioRepositorio) -> None:
        self._evaluaciones = evaluaciones

    def ejecutar(self, consulta: ListarEvaluacionesQuery) -> list[EvaluacionDTO]:
        """Lista las evaluaciones, de la más reciente a la más antigua.

        Raises:
            SolicitudInvalidaError: si la paginación o el rango de fechas son inválidos.
        """
        validar_paginacion(
            limite=consulta.limite,
            desplazamiento=consulta.desplazamiento,
        )
        validar_rango_fechas(desde=consulta.desde, hasta=consulta.hasta)

        evaluaciones = self._evaluaciones.listar(
            producto_id=consulta.producto_id,
            nivel_riesgo=consulta.nivel_riesgo,
            desde=consulta.desde,
            hasta=consulta.hasta,
            limite=consulta.limite,
            desplazamiento=consulta.desplazamiento,
        )
        return [a_evaluacion_dto(evaluacion) for evaluacion in evaluaciones]

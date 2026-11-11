"""Endpoints de evaluaciones de precio."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from ...application.dto.queries import ListarEvaluacionesQuery
from ...domain.value_objects.nivel_riesgo import NivelRiesgo
from ..cache import cache_lecturas
from ..dependencies import ListarEvaluacionesDep
from ..schemas import EvaluacionRespuesta

router = APIRouter(tags=["evaluaciones"])


@router.get(
    "/evaluaciones",
    response_model=list[EvaluacionRespuesta],
    summary="Lista las evaluaciones de precios con su nivel de riesgo",
    description=(
        "Devuelve las evaluaciones de más reciente a más antigua. El nivel de "
        "riesgo puede ser precio_justo, alerta_amarilla o alto_riesgo."
    ),
)
def listar_evaluaciones(
    caso_uso: ListarEvaluacionesDep,
    producto_id: Annotated[
        str | None,
        Query(description="Filtra por identificador de producto."),
    ] = None,
    nivel_riesgo: Annotated[
        NivelRiesgo | None,
        Query(description="Filtra por nivel de riesgo."),
    ] = None,
    desde: Annotated[
        datetime | None,
        Query(
            description=(
                "Fecha y hora mínima de evaluación en formato ISO 8601. "
                "Debe incluir zona horaria."
            )
        ),
    ] = None,
    hasta: Annotated[
        datetime | None,
        Query(
            description=(
                "Fecha y hora máxima de evaluación en formato ISO 8601. "
                "Debe incluir zona horaria."
            )
        ),
    ] = None,
    limite: Annotated[
        int,
        Query(ge=1, le=200, description="Cantidad máxima de resultados."),
    ] = 50,
    desplazamiento: Annotated[
        int,
        Query(ge=0, description="Cantidad de resultados a omitir."),
    ] = 0,
    force_refresh: Annotated[bool, Query(description="Solicita refresco global; limitado a uno cada 60 segundos y responde desde caché.")] = False,
) -> list[EvaluacionRespuesta]:
    """Lista las evaluaciones registradas según los filtros indicados."""
    consulta = ListarEvaluacionesQuery(
        producto_id=producto_id,
        nivel_riesgo=nivel_riesgo,
        desde=desde,
        hasta=hasta,
        limite=limite,
        desplazamiento=desplazamiento,
    )
    evaluaciones = cache_lecturas.obtener(
        f"evaluaciones:{id(getattr(caso_uso, '_evaluaciones', caso_uso))}:{producto_id}:{nivel_riesgo}:{desde}:{hasta}:{limite}:{desplazamiento}",
        lambda: caso_uso.ejecutar(consulta),
        force_refresh=force_refresh,
    )
    return [
        EvaluacionRespuesta.model_validate(evaluacion.to_dict())
        for evaluacion in evaluaciones
    ]


__all__ = ["router"]

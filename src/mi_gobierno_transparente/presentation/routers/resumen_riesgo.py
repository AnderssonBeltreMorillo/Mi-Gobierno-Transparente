"""Endpoint del resumen de riesgo."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from ...application.dto.queries import ObtenerResumenRiesgoQuery
from ..cache import cache_lecturas
from ..dependencies import ObtenerResumenRiesgoDep
from ..schemas import ResumenRiesgoRespuesta

router = APIRouter(tags=["riesgo"])


@router.get(
    "/resumen-riesgo",
    response_model=ResumenRiesgoRespuesta,
    summary="Devuelve el resumen general de riesgo",
    description=(
        "Agrega las evaluaciones por nivel de riesgo y calcula el porcentaje "
        "de evaluaciones en alto riesgo."
    ),
)
def obtener_resumen_riesgo(
    caso_uso: ObtenerResumenRiesgoDep,
    producto_id: Annotated[
        str | None,
        Query(description="Limita el resumen a un producto específico."),
    ] = None,
    force_refresh: Annotated[bool, Query(description="Solicita refresco global; limitado a uno cada 60 segundos y responde desde caché.")] = False,
) -> ResumenRiesgoRespuesta:
    """Devuelve el conteo agregado por nivel de riesgo."""
    resumen = cache_lecturas.obtener(
        f"resumen-riesgo:{id(getattr(caso_uso, '_evaluaciones', caso_uso))}:{producto_id}",
        lambda: caso_uso.ejecutar(ObtenerResumenRiesgoQuery(producto_id=producto_id)),
        force_refresh=force_refresh,
    )
    return ResumenRiesgoRespuesta.model_validate(resumen.to_dict())


__all__ = ["router"]

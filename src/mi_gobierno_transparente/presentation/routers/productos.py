"""Endpoints de productos."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from ...application.dto.queries import ListarProductosQuery
from ...domain.value_objects.categoria_producto import CategoriaProducto
from ..cache import cache_lecturas
from ..dependencies import ListarProductosDep
from ..schemas import ProductoRespuesta

router = APIRouter(tags=["productos"])


@router.get(
    "/productos",
    response_model=list[ProductoRespuesta],
    summary="Lista los productos registrados",
    description=(
        "Devuelve productos de alimentos y aseo. Por defecto solo incluye los "
        "activos y ordena por nombre normalizado."
    ),
)
def listar_productos(
    caso_uso: ListarProductosDep,
    categoria: Annotated[
        CategoriaProducto | None,
        Query(description="Filtra por categoría (alimentos o aseo)."),
    ] = None,
    incluir_inactivos: Annotated[
        bool,
        Query(description="Incluye productos desactivados."),
    ] = False,
    limite: Annotated[
        int,
        Query(ge=1, le=200, description="Cantidad máxima de resultados."),
    ] = 50,
    desplazamiento: Annotated[
        int,
        Query(ge=0, description="Cantidad de resultados a omitir."),
    ] = 0,
    force_refresh: Annotated[bool, Query(description="Solicita refresco global; limitado a uno cada 60 segundos y responde desde caché.")] = False,
) -> list[ProductoRespuesta]:
    """Lista los productos registrados según los filtros indicados."""
    consulta = ListarProductosQuery(
        categoria=categoria,
        incluir_inactivos=incluir_inactivos,
        limite=limite,
        desplazamiento=desplazamiento,
    )
    productos = cache_lecturas.obtener(
        f"productos:{id(getattr(caso_uso, '_productos', caso_uso))}:{categoria}:{incluir_inactivos}:{limite}:{desplazamiento}",
        lambda: caso_uso.ejecutar(consulta),
        force_refresh=force_refresh,
    )
    return [
        ProductoRespuesta.model_validate(producto.to_dict())
        for producto in productos
    ]


__all__ = ["router"]

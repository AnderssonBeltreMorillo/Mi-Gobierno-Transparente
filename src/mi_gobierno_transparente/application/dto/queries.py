"""Consultas de entrada para los casos de uso de lectura."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ...domain.value_objects.categoria_producto import CategoriaProducto
from ...domain.value_objects.nivel_riesgo import NivelRiesgo


@dataclass(frozen=True, slots=True)
class ListarProductosQuery:
    """Filtros y paginación para listar productos."""

    categoria: CategoriaProducto | None = None
    incluir_inactivos: bool = False
    limite: int = 50
    desplazamiento: int = 0


@dataclass(frozen=True, slots=True)
class ObtenerProductoQuery:
    """Identificador del producto a consultar."""

    producto_id: str


@dataclass(frozen=True, slots=True)
class ListarEvaluacionesQuery:
    """Filtros y paginación para listar evaluaciones."""

    producto_id: str | None = None
    nivel_riesgo: NivelRiesgo | None = None
    desde: datetime | None = None
    hasta: datetime | None = None
    limite: int = 50
    desplazamiento: int = 0


@dataclass(frozen=True, slots=True)
class ObtenerResumenRiesgoQuery:
    """Filtro opcional por producto para el tablero de riesgo."""

    producto_id: str | None = None

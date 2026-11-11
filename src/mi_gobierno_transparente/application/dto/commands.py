"""Comandos de entrada para los casos de uso de escritura."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ...domain.value_objects.categoria_producto import CategoriaProducto
from ...domain.value_objects.unidad_medida import UnidadMedida


@dataclass(frozen=True, slots=True)
class RegistrarProductoCommand:
    """Datos para registrar un producto de alimentos o aseo."""

    nombre: str
    categoria: CategoriaProducto
    unidad_medida: UnidadMedida
    marca: str | None = None
    descripcion: str | None = None


@dataclass(frozen=True, slots=True)
class RegistrarPrecioMercadoCommand:
    """Datos para registrar un precio de referencia y dejarlo vigente."""

    producto_id: str
    monto: Decimal
    fuente: str
    moneda: str = "PEN"
    fecha_registro: date | None = None


@dataclass(frozen=True, slots=True)
class RegistrarPrecioReportadoCommand:
    """Datos para registrar el precio observado en un establecimiento."""

    producto_id: str
    monto: Decimal
    establecimiento: str
    moneda: str = "PEN"
    distrito: str | None = None
    reportado_por: str | None = None
    fecha_reporte: date | None = None


@dataclass(frozen=True, slots=True)
class EvaluarPrecioCommand:
    """Datos para evaluar un precio reportado contra el mercado vigente."""

    producto_id: str
    precio_reportado_id: str
    observacion: str | None = None


@dataclass(frozen=True, slots=True)
class CambiarEstadoProductoCommand:
    """Activa o desactiva un producto existente."""

    producto_id: str
    activo: bool

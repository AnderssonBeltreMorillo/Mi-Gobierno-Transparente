"""Helpers compartidos por los casos de uso (validaciones de entrada)."""

from __future__ import annotations

from datetime import date, datetime

from ...domain.entities.producto import Producto
from ...domain.value_objects.categoria_producto import CategoriaProducto
from ..exceptions import (
    ProductoInactivoError,
    ProductoNoEncontradoError,
    SolicitudInvalidaError,
)
from ..ports.repositories import ProductoRepositorio

LIMITE_POR_DEFECTO = 50
LIMITE_MAXIMO = 200


def validar_paginacion(*, limite: int, desplazamiento: int) -> None:
    """Valida los parámetros de paginación de las consultas."""
    if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= LIMITE_MAXIMO:
        raise SolicitudInvalidaError(
            f"El límite debe ser un entero entre 1 y {LIMITE_MAXIMO}."
        )
    if (
        not isinstance(desplazamiento, int)
        or isinstance(desplazamiento, bool)
        or desplazamiento < 0
    ):
        raise SolicitudInvalidaError(
            "El desplazamiento debe ser un entero mayor o igual a cero."
        )


def validar_rango_fechas(*, desde: datetime | None, hasta: datetime | None) -> None:
    """Valida que el rango sea coherente y que ambas fechas tengan zona horaria."""
    for nombre, valor in (("desde", desde), ("hasta", hasta)):
        if valor is None:
            continue
        if not isinstance(valor, datetime) or valor.tzinfo is None or valor.utcoffset() is None:
            raise SolicitudInvalidaError(f"La fecha '{nombre}' debe incluir zona horaria.")
    if desde is not None and hasta is not None and desde > hasta:
        raise SolicitudInvalidaError("La fecha 'desde' no puede ser posterior a 'hasta'.")


def validar_fecha_no_futura(*, fecha: date, hoy: date, campo: str) -> None:
    """Impide registrar precios con fecha futura o con hora."""
    if not isinstance(fecha, date) or isinstance(fecha, datetime):
        raise SolicitudInvalidaError(f"La fecha de {campo} debe ser una fecha válida.")
    if fecha > hoy:
        raise SolicitudInvalidaError(f"La fecha de {campo} no puede ser futura.")


def obtener_producto(productos: ProductoRepositorio, producto_id: str) -> Producto:
    """Obtiene un producto o lanza ``ProductoNoEncontradoError``."""
    producto = productos.obtener_por_id(producto_id)
    if producto is None:
        raise ProductoNoEncontradoError(producto_id)
    return producto


def obtener_producto_activo(productos: ProductoRepositorio, producto_id: str) -> Producto:
    """Obtiene un producto activo y revalida la regla de categorías permitidas."""
    producto = obtener_producto(productos, producto_id)
    if not producto.activo:
        raise ProductoInactivoError(producto_id)
    CategoriaProducto.validar_permitida(producto.categoria)
    return producto

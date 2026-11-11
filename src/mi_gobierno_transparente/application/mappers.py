"""Mapeadores de entidades de dominio a DTOs de aplicación."""

from __future__ import annotations

from ..domain.entities.evaluacion_precio import EvaluacionPrecio
from ..domain.entities.precio_mercado import PrecioMercado
from ..domain.entities.precio_reportado import PrecioReportado
from ..domain.entities.producto import Producto
from .dto.evaluacion_dto import EvaluacionDTO
from .dto.precio_mercado_dto import PrecioMercadoDTO
from .dto.precio_reportado_dto import PrecioReportadoDTO
from .dto.producto_dto import ProductoDTO


def a_producto_dto(producto: Producto) -> ProductoDTO:
    """Convierte un producto de dominio en su DTO de salida."""
    return ProductoDTO(
        id=producto.id,
        nombre=producto.nombre,
        categoria=producto.categoria,
        unidad_medida=producto.unidad_medida,
        marca=producto.marca,
        descripcion=producto.descripcion,
        activo=producto.activo,
    )


def a_precio_mercado_dto(precio: PrecioMercado) -> PrecioMercadoDTO:
    """Convierte un precio de mercado en su DTO de salida."""
    return PrecioMercadoDTO(
        id=precio.id,
        producto_id=precio.producto_id,
        monto=precio.precio.monto,
        moneda=precio.precio.moneda,
        fuente=precio.fuente,
        fecha_registro=precio.fecha_registro,
        vigente=precio.vigente,
    )


def a_precio_reportado_dto(precio: PrecioReportado) -> PrecioReportadoDTO:
    """Convierte un precio reportado en su DTO de salida."""
    return PrecioReportadoDTO(
        id=precio.id,
        producto_id=precio.producto_id,
        monto=precio.precio.monto,
        moneda=precio.precio.moneda,
        establecimiento=precio.establecimiento,
        distrito=precio.distrito,
        reportado_por=precio.reportado_por,
        fecha_reporte=precio.fecha_reporte,
    )


def a_evaluacion_dto(evaluacion: EvaluacionPrecio) -> EvaluacionDTO:
    """Convierte una evaluación en su DTO de salida."""
    resultado = evaluacion.resultado
    return EvaluacionDTO(
        id=evaluacion.id,
        producto_id=evaluacion.producto_id,
        precio_reportado_id=evaluacion.precio_reportado_id,
        precio_mercado_id=evaluacion.precio_mercado_id,
        monto_reportado=resultado.precio_reportado.monto,
        monto_mercado=resultado.precio_mercado.monto,
        moneda=resultado.precio_reportado.moneda,
        diferencia=resultado.precio_reportado.monto - resultado.precio_mercado.monto,
        excedente=resultado.excedente.monto,
        sobreprecio_porcentaje=resultado.sobreprecio.como_porcentaje(),
        nivel_riesgo=resultado.nivel_riesgo,
        dentro_de_tolerancia=resultado.dentro_de_tolerancia,
        requiere_intervencion=resultado.requiere_intervencion,
        alerta_amarilla_desde_porcentaje=resultado.umbrales.alerta_amarilla_desde.como_porcentaje(),
        alto_riesgo_desde_porcentaje=resultado.umbrales.alto_riesgo_desde.como_porcentaje(),
        evaluado_en=evaluacion.evaluado_en,
        version_regla=evaluacion.version_regla,
        observacion=evaluacion.observacion,
    )

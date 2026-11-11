"""Esquemas de respuesta HTTP.

Los DTOs de aplicación ya serializan ``Decimal`` y ``datetime`` a texto para
evitar pérdida de precisión y ambigüedades de zona horaria. Estos esquemas solo
describen la forma JSON y alimentan la documentación OpenAPI.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Respuesta(BaseModel):
    """Base común para respuestas de solo lectura."""

    model_config = ConfigDict(extra="forbid")


class ProductoRespuesta(_Respuesta):
    """Producto registrado en el catálogo."""

    id: str
    nombre: str
    categoria: str
    unidad_medida: str
    marca: str | None
    descripcion: str | None
    activo: bool


class EvaluacionRespuesta(_Respuesta):
    """Evaluación auditable de un precio reportado contra el mercado."""

    id: str
    producto_id: str
    precio_reportado_id: str
    precio_mercado_id: str
    monto_reportado: str
    monto_mercado: str
    moneda: str
    diferencia: str
    excedente: str
    sobreprecio_porcentaje: str
    nivel_riesgo: str
    dentro_de_tolerancia: bool
    requiere_intervencion: bool
    alerta_amarilla_desde_porcentaje: str
    alto_riesgo_desde_porcentaje: str
    evaluado_en: str
    version_regla: str
    observacion: str | None


class ResumenRiesgoRespuesta(_Respuesta):
    """Conteo agregado de evaluaciones por nivel de riesgo."""

    total_evaluaciones: int
    precio_justo: int
    alerta_amarilla: int
    alto_riesgo: int
    porcentaje_alto_riesgo: str


class ErrorRespuesta(BaseModel):
    """Cuerpo uniforme de error de la API."""

    codigo: str
    mensaje: str


class ErrorEnvoltorio(BaseModel):
    """Envoltura para documentar errores en OpenAPI."""

    error: ErrorRespuesta


__all__ = [
    "ErrorEnvoltorio",
    "ErrorRespuesta",
    "EvaluacionRespuesta",
    "ProductoRespuesta",
    "ResumenRiesgoRespuesta",
]

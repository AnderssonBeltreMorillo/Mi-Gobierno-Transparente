"""Entidad EvaluacionPrecio: auditoría inmutable de una comparación de precios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..exceptions import EvaluacionInvalidaError
from ..value_objects.dinero import Dinero
from ..value_objects.nivel_riesgo import NivelRiesgo
from ..value_objects.porcentaje import Porcentaje
from ..value_objects.resultado_evaluacion import ResultadoEvaluacion
from ._validacion import exigir_identificador, exigir_texto, limpiar_texto_opcional


@dataclass(frozen=True, slots=True)
class EvaluacionPrecio:
    """Resultado persistible de evaluar un precio reportado.

    Guarda las referencias y una foto del resultado (precios, sobreprecio,
    nivel y umbrales) para que la decisión sea auditable en el tiempo.
    """

    id: str
    producto_id: str
    precio_reportado_id: str
    precio_mercado_id: str
    resultado: ResultadoEvaluacion
    evaluado_en: datetime
    version_regla: str = "1.0.0"
    observacion: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            exigir_identificador(self.id, campo="id", error=EvaluacionInvalidaError),
        )
        object.__setattr__(
            self,
            "producto_id",
            exigir_identificador(
                self.producto_id,
                campo="producto_id",
                error=EvaluacionInvalidaError,
            ),
        )
        object.__setattr__(
            self,
            "precio_reportado_id",
            exigir_identificador(
                self.precio_reportado_id,
                campo="precio_reportado_id",
                error=EvaluacionInvalidaError,
            ),
        )
        object.__setattr__(
            self,
            "precio_mercado_id",
            exigir_identificador(
                self.precio_mercado_id,
                campo="precio_mercado_id",
                error=EvaluacionInvalidaError,
            ),
        )
        if not isinstance(self.resultado, ResultadoEvaluacion):
            raise EvaluacionInvalidaError("El resultado debe ser un ResultadoEvaluacion.")
        if (
            not isinstance(self.evaluado_en, datetime)
            or self.evaluado_en.tzinfo is None
            or self.evaluado_en.utcoffset() is None
        ):
            raise EvaluacionInvalidaError(
                "La fecha de evaluación debe ser un datetime con zona horaria."
            )
        object.__setattr__(
            self,
            "version_regla",
            exigir_texto(
                self.version_regla,
                campo="version_regla",
                minimo=1,
                maximo=20,
                error=EvaluacionInvalidaError,
            ),
        )
        object.__setattr__(
            self,
            "observacion",
            limpiar_texto_opcional(
                self.observacion,
                campo="observación",
                maximo=500,
                error=EvaluacionInvalidaError,
            ),
        )

    @property
    def precio_reportado(self) -> Dinero:
        return self.resultado.precio_reportado

    @property
    def precio_mercado(self) -> Dinero:
        return self.resultado.precio_mercado

    @property
    def excedente(self) -> Dinero:
        return self.resultado.excedente

    @property
    def sobreprecio(self) -> Porcentaje:
        return self.resultado.sobreprecio

    @property
    def nivel_riesgo(self) -> NivelRiesgo:
        return self.resultado.nivel_riesgo

    @property
    def requiere_intervencion(self) -> bool:
        return self.resultado.requiere_intervencion

    def __str__(self) -> str:
        return (
            f"Evaluación {self.id}: {self.nivel_riesgo.etiqueta} "
            f"({self.sobreprecio.formateado()})"
        )

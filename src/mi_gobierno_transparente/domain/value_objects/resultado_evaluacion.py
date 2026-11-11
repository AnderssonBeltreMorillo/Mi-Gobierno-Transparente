"""Resultado inmutable de comparar un precio reportado contra el de mercado."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import EvaluacionInvalidaError
from .dinero import Dinero
from .nivel_riesgo import NivelRiesgo
from .porcentaje import Porcentaje
from .umbrales_evaluacion import UmbralesEvaluacion


@dataclass(frozen=True, slots=True)
class ResultadoEvaluacion:
    """Foto consistente de una evaluación de precio.

    Se guarda junto con los umbrales aplicados para que la evaluación sea
    auditable incluso si las reglas cambian en el futuro.
    """

    precio_reportado: Dinero
    precio_mercado: Dinero
    excedente: Dinero
    sobreprecio: Porcentaje
    nivel_riesgo: NivelRiesgo
    umbrales: UmbralesEvaluacion

    def __post_init__(self) -> None:
        if not isinstance(self.precio_reportado, Dinero):
            raise EvaluacionInvalidaError("El precio reportado debe ser un Dinero.")
        if not isinstance(self.precio_mercado, Dinero):
            raise EvaluacionInvalidaError("El precio de mercado debe ser un Dinero.")
        if self.precio_reportado.moneda != self.precio_mercado.moneda:
            raise EvaluacionInvalidaError("Los precios comparados deben estar en la misma moneda.")
        if not isinstance(self.excedente, Dinero):
            raise EvaluacionInvalidaError("El excedente debe ser un Dinero.")
        if self.excedente.moneda != self.precio_mercado.moneda:
            raise EvaluacionInvalidaError(
                "El excedente debe estar en la moneda del precio de mercado."
            )
        if self.precio_mercado.es_cero():
            raise EvaluacionInvalidaError("El precio de mercado debe ser mayor que cero.")
        if not isinstance(self.sobreprecio, Porcentaje):
            raise EvaluacionInvalidaError("El sobreprecio debe ser un Porcentaje.")
        if not isinstance(self.nivel_riesgo, NivelRiesgo):
            raise EvaluacionInvalidaError("El nivel de riesgo debe ser un NivelRiesgo.")
        if not isinstance(self.umbrales, UmbralesEvaluacion):
            raise EvaluacionInvalidaError("Los umbrales deben ser un UmbralesEvaluacion.")

        excedente_esperado = self.precio_reportado.excedente_sobre(self.precio_mercado)
        if self.excedente != excedente_esperado:
            raise EvaluacionInvalidaError(
                "El excedente no coincide con la diferencia entre el precio reportado "
                "y el de mercado."
            )

        sobreprecio_esperado = Porcentaje(
            self.excedente.monto / self.precio_mercado.monto
        )
        if self.sobreprecio != sobreprecio_esperado:
            raise EvaluacionInvalidaError(
                "El sobreprecio no coincide con el excedente y el precio de mercado."
            )

        nivel_esperado = self.umbrales.clasificar(self.sobreprecio)
        if self.nivel_riesgo is not nivel_esperado:
            raise EvaluacionInvalidaError(
                "El nivel de riesgo no coincide con los umbrales y el sobreprecio indicados."
            )

    @property
    def requiere_intervencion(self) -> bool:
        """Indica si el resultado exige revisión (amarilla o alto riesgo)."""
        return self.nivel_riesgo.requiere_intervencion

    @property
    def dentro_de_tolerancia(self) -> bool:
        """Precio por encima del mercado, pero dentro de la banda de tolerancia."""
        return self.nivel_riesgo is NivelRiesgo.PRECIO_JUSTO and self.sobreprecio.es_positivo()

    def __str__(self) -> str:
        return (
            f"{self.nivel_riesgo.etiqueta}: {self.sobreprecio.formateado()} "
            f"({self.precio_reportado} vs {self.precio_mercado})"
        )

"""Servicio de dominio que calcula el sobreprecio y su nivel de riesgo."""

from __future__ import annotations

from typing import Final

from ..exceptions import PrecioInvalidoError
from ..value_objects.dinero import Dinero
from ..value_objects.porcentaje import Porcentaje
from ..value_objects.resultado_evaluacion import ResultadoEvaluacion
from ..value_objects.umbrales_evaluacion import UmbralesEvaluacion


class EvaluadorPrecio:
    """Compara un precio reportado contra un precio de mercado.

    Es un servicio de dominio puro: no conoce repositorios, fechas del sistema
    ni frameworks. La versión de la regla se persiste con cada evaluación.
    """

    VERSION: Final[str] = "1.0.0"

    def __init__(self, umbrales: UmbralesEvaluacion | None = None) -> None:
        if umbrales is not None and not isinstance(umbrales, UmbralesEvaluacion):
            raise PrecioInvalidoError("Los umbrales deben ser un UmbralesEvaluacion.")
        self._umbrales: Final[UmbralesEvaluacion] = umbrales or UmbralesEvaluacion.estandar()

    @property
    def umbrales(self) -> UmbralesEvaluacion:
        return self._umbrales

    @property
    def version(self) -> str:
        return self.VERSION

    def evaluar(self, *, precio_reportado: Dinero, precio_mercado: Dinero) -> ResultadoEvaluacion:
        """Calcula excedente, sobreprecio y nivel de riesgo.

        El sobreprecio se calcula sobre el precio de mercado y nunca es negativo:
        un precio por debajo del mercado reporta 0 % de sobreprecio.

        Raises:
            PrecioInvalidoError: si el precio de mercado es cero o los importes
                no son ``Dinero``.
            MonedaIncompatibleError: si los precios están en monedas distintas.
        """
        if not isinstance(precio_reportado, Dinero):
            raise PrecioInvalidoError("El precio reportado debe ser un Dinero.")
        if not isinstance(precio_mercado, Dinero):
            raise PrecioInvalidoError("El precio de mercado debe ser un Dinero.")
        if precio_mercado.es_cero():
            raise PrecioInvalidoError(
                "El precio de mercado debe ser mayor que cero para calcular el sobreprecio."
            )

        excedente = precio_reportado.excedente_sobre(precio_mercado)
        sobreprecio = Porcentaje(excedente.monto / precio_mercado.monto)
        nivel_riesgo = self._umbrales.clasificar(sobreprecio)

        return ResultadoEvaluacion(
            precio_reportado=precio_reportado,
            precio_mercado=precio_mercado,
            excedente=excedente,
            sobreprecio=sobreprecio,
            nivel_riesgo=nivel_riesgo,
            umbrales=self._umbrales,
        )

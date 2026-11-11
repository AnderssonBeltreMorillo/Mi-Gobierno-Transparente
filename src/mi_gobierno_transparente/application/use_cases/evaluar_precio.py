"""Caso de uso: evaluar un precio reportado contra el mercado vigente."""

from __future__ import annotations

from ...domain.entities.evaluacion_precio import EvaluacionPrecio
from ...domain.services.evaluador_precio import EvaluadorPrecio
from ..dto.commands import EvaluarPrecioCommand
from ..dto.evaluacion_dto import EvaluacionDTO
from ..exceptions import (
    PrecioMercadoNoDisponibleError,
    PrecioReportadoDeOtroProductoError,
    PrecioReportadoNoEncontradoError,
)
from ..mappers import a_evaluacion_dto
from ..ports.generador_identificadores import GeneradorIdentificadores
from ..ports.reloj import Reloj
from ..ports.repositories import (
    EvaluacionPrecioRepositorio,
    PrecioMercadoRepositorio,
    PrecioReportadoRepositorio,
    ProductoRepositorio,
)
from ._comun import obtener_producto_activo


class EvaluarPrecio:
    """Orquesta la comparación y persiste una evaluación auditable.

    La comparación se hace contra el precio de mercado **vigente al momento de
    la evaluación**. Cada ejecución genera una nueva evaluación histórica.
    """

    def __init__(
        self,
        productos: ProductoRepositorio,
        precios_mercado: PrecioMercadoRepositorio,
        precios_reportados: PrecioReportadoRepositorio,
        evaluaciones: EvaluacionPrecioRepositorio,
        evaluador: EvaluadorPrecio,
        generador_id: GeneradorIdentificadores,
        reloj: Reloj,
    ) -> None:
        self._productos = productos
        self._precios_mercado = precios_mercado
        self._precios_reportados = precios_reportados
        self._evaluaciones = evaluaciones
        self._evaluador = evaluador
        self._generador_id = generador_id
        self._reloj = reloj

    def ejecutar(self, comando: EvaluarPrecioCommand) -> EvaluacionDTO:
        """Evalúa el reporte y guarda el resultado.

        Raises:
            ProductoNoEncontradoError: si el producto no existe.
            ProductoInactivoError: si el producto está inactivo.
            CategoriaNoPermitidaError: si el producto no es de alimentos o aseo.
            PrecioReportadoNoEncontradoError: si el reporte no existe.
            PrecioReportadoDeOtroProductoError: si el reporte es de otro producto.
            PrecioMercadoNoDisponibleError: si no hay precio de mercado vigente.
        """
        producto = obtener_producto_activo(self._productos, comando.producto_id)

        precio_reportado = self._precios_reportados.obtener_por_id(
            comando.precio_reportado_id
        )
        if precio_reportado is None:
            raise PrecioReportadoNoEncontradoError(comando.precio_reportado_id)
        if not precio_reportado.es_del_producto(producto.id):
            raise PrecioReportadoDeOtroProductoError(
                comando.precio_reportado_id,
                producto.id,
            )

        precio_mercado = self._precios_mercado.obtener_vigente(
            producto.id,
            en_fecha=self._reloj.hoy(),
        )
        if precio_mercado is None:
            raise PrecioMercadoNoDisponibleError(producto.id)

        resultado = self._evaluador.evaluar(
            precio_reportado=precio_reportado.precio,
            precio_mercado=precio_mercado.precio,
        )

        evaluacion = EvaluacionPrecio(
            id=self._generador_id.nuevo(),
            producto_id=producto.id,
            precio_reportado_id=precio_reportado.id,
            precio_mercado_id=precio_mercado.id,
            resultado=resultado,
            evaluado_en=self._reloj.ahora(),
            version_regla=self._evaluador.version,
            observacion=comando.observacion,
        )
        self._evaluaciones.guardar(evaluacion)
        return a_evaluacion_dto(evaluacion)

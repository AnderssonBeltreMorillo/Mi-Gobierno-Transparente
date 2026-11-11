"""Caso de uso: registrar un precio observado en un establecimiento."""

from __future__ import annotations

from ...domain.entities.precio_reportado import PrecioReportado
from ...domain.value_objects.dinero import Dinero
from ..dto.commands import RegistrarPrecioReportadoCommand
from ..dto.precio_reportado_dto import PrecioReportadoDTO
from ..mappers import a_precio_reportado_dto
from ..ports.generador_identificadores import GeneradorIdentificadores
from ..ports.reloj import Reloj
from ..ports.repositories import PrecioReportadoRepositorio, ProductoRepositorio
from ._comun import obtener_producto_activo, validar_fecha_no_futura


class RegistrarPrecioReportado:
    """Registra un precio ciudadano para un producto permitido."""

    def __init__(
        self,
        productos: ProductoRepositorio,
        precios_reportados: PrecioReportadoRepositorio,
        generador_id: GeneradorIdentificadores,
        reloj: Reloj,
    ) -> None:
        self._productos = productos
        self._precios_reportados = precios_reportados
        self._generador_id = generador_id
        self._reloj = reloj

    def ejecutar(self, comando: RegistrarPrecioReportadoCommand) -> PrecioReportadoDTO:
        """Crea y persiste el reporte de precio.

        Raises:
            ProductoNoEncontradoError: si el producto no existe.
            ProductoInactivoError: si el producto está inactivo.
            CategoriaNoPermitidaError: si el producto no es de alimentos o aseo.
            PrecioInvalidoError: si el monto o el establecimiento no son válidos.
            SolicitudInvalidaError: si la fecha es futura.
        """
        producto = obtener_producto_activo(self._productos, comando.producto_id)

        fecha = comando.fecha_reporte if comando.fecha_reporte is not None else self._reloj.hoy()
        validar_fecha_no_futura(
            fecha=fecha,
            hoy=self._reloj.hoy(),
            campo="reporte del precio",
        )

        precio = PrecioReportado(
            id=self._generador_id.nuevo(),
            producto_id=producto.id,
            precio=Dinero(comando.monto, comando.moneda),
            establecimiento=comando.establecimiento,
            fecha_reporte=fecha,
            distrito=comando.distrito,
            reportado_por=comando.reportado_por,
        )
        self._precios_reportados.guardar(precio)
        return a_precio_reportado_dto(precio)

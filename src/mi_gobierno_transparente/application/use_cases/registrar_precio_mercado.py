"""Caso de uso: registrar el precio de mercado vigente de un producto."""

from __future__ import annotations

from ...domain.entities.precio_mercado import PrecioMercado
from ...domain.value_objects.dinero import Dinero
from ..dto.commands import RegistrarPrecioMercadoCommand
from ..dto.precio_mercado_dto import PrecioMercadoDTO
from ..mappers import a_precio_mercado_dto
from ..ports.generador_identificadores import GeneradorIdentificadores
from ..ports.reloj import Reloj
from ..ports.repositories import PrecioMercadoRepositorio, ProductoRepositorio
from ._comun import obtener_producto_activo, validar_fecha_no_futura


class RegistrarPrecioMercado:
    """Registra un precio de referencia y lo deja como el vigente del producto."""

    def __init__(
        self,
        productos: ProductoRepositorio,
        precios_mercado: PrecioMercadoRepositorio,
        generador_id: GeneradorIdentificadores,
        reloj: Reloj,
    ) -> None:
        self._productos = productos
        self._precios_mercado = precios_mercado
        self._generador_id = generador_id
        self._reloj = reloj

    def ejecutar(self, comando: RegistrarPrecioMercadoCommand) -> PrecioMercadoDTO:
        """Crea el precio y reemplaza el vigente anterior.

        Raises:
            ProductoNoEncontradoError: si el producto no existe.
            ProductoInactivoError: si el producto está inactivo.
            CategoriaNoPermitidaError: si el producto no es de alimentos o aseo.
            PrecioInvalidoError: si el monto o la fuente no son válidos.
            SolicitudInvalidaError: si la fecha es futura.
        """
        producto = obtener_producto_activo(self._productos, comando.producto_id)

        fecha = comando.fecha_registro if comando.fecha_registro is not None else self._reloj.hoy()
        validar_fecha_no_futura(
            fecha=fecha,
            hoy=self._reloj.hoy(),
            campo="registro del precio de mercado",
        )

        precio = PrecioMercado(
            id=self._generador_id.nuevo(),
            producto_id=producto.id,
            precio=Dinero(comando.monto, comando.moneda),
            fuente=comando.fuente,
            fecha_registro=fecha,
        )
        self._precios_mercado.reemplazar_vigente(precio)
        return a_precio_mercado_dto(precio)

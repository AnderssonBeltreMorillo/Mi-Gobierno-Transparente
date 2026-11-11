"""Dobles de prueba en memoria para los puertos de la aplicación.

No forman parte de la capa de infraestructura del producto: son implementaciones
mínimas usadas únicamente por la suite de pruebas.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime

from mi_gobierno_transparente.application.ports import (
    EvaluacionPrecioRepositorio,
    GeneradorIdentificadores,
    PrecioMercadoRepositorio,
    PrecioReportadoRepositorio,
    ProductoRepositorio,
    Reloj,
)
from mi_gobierno_transparente.domain.entities import (
    EvaluacionPrecio,
    PrecioMercado,
    PrecioReportado,
    Producto,
)
from mi_gobierno_transparente.domain.value_objects import (
    CategoriaProducto,
    NivelRiesgo,
)


class RelojFijo(Reloj):
    """Reloj determinista para pruebas."""

    def __init__(self, momento: datetime) -> None:
        if momento.tzinfo is None or momento.utcoffset() is None:
            raise ValueError("RelojFijo requiere un datetime con zona horaria.")
        self._momento = momento

    def ahora(self) -> datetime:
        return self._momento


class GeneradorSecuencial(GeneradorIdentificadores):
    """Genera identificadores predecibles (``prefijo-1``, ``prefijo-2``, ...)."""

    def __init__(self, prefijo: str = "id") -> None:
        self._prefijo = prefijo
        self._contador = 0

    def nuevo(self) -> str:
        self._contador += 1
        return f"{self._prefijo}-{self._contador}"


class ProductoRepositorioEnMemoria(ProductoRepositorio):
    """Repositorio de productos en un diccionario."""

    def __init__(self) -> None:
        self._productos: dict[str, Producto] = {}

    def guardar(self, producto: Producto) -> None:
        self._productos[producto.id] = producto

    def obtener_por_id(self, producto_id: str) -> Producto | None:
        return self._productos.get(producto_id)

    def obtener_por_nombre(self, nombre_normalizado: str) -> Producto | None:
        buscado = " ".join(nombre_normalizado.split()).casefold()
        for producto in self._productos.values():
            if producto.nombre_normalizado == buscado:
                return producto
        return None

    def existe_por_nombre(self, nombre_normalizado: str) -> bool:
        return self.obtener_por_nombre(nombre_normalizado) is not None

    def listar(
        self,
        *,
        categoria: CategoriaProducto | None = None,
        incluir_inactivos: bool = False,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> list[Producto]:
        productos = self._filtrar(
            categoria=categoria,
            incluir_inactivos=incluir_inactivos,
        )
        productos.sort(key=lambda producto: (producto.nombre_normalizado, producto.id))
        return productos[desplazamiento : desplazamiento + limite]

    def contar(
        self,
        *,
        categoria: CategoriaProducto | None = None,
        incluir_inactivos: bool = False,
    ) -> int:
        return len(
            self._filtrar(categoria=categoria, incluir_inactivos=incluir_inactivos)
        )

    def _filtrar(
        self,
        *,
        categoria: CategoriaProducto | None,
        incluir_inactivos: bool,
    ) -> list[Producto]:
        return [
            producto
            for producto in self._productos.values()
            if (incluir_inactivos or producto.activo)
            and (categoria is None or producto.categoria is categoria)
        ]


class PrecioMercadoRepositorioEnMemoria(PrecioMercadoRepositorio):
    """Repositorio de precios de mercado en un diccionario."""

    def __init__(self) -> None:
        self._precios: dict[str, PrecioMercado] = {}

    def guardar(self, precio: PrecioMercado) -> None:
        self._precios[precio.id] = precio

    def reemplazar_vigente(self, precio: PrecioMercado) -> None:
        for existente in list(self._precios.values()):
            if existente.producto_id == precio.producto_id and existente.vigente:
                self._precios[existente.id] = existente.desactivar()
        self._precios[precio.id] = precio

    def obtener_por_id(self, precio_id: str) -> PrecioMercado | None:
        return self._precios.get(precio_id)

    def obtener_vigente(
        self,
        producto_id: str,
        *,
        en_fecha: date | None = None,
    ) -> PrecioMercado | None:
        candidatos = [
            precio
            for precio in self._precios.values()
            if precio.producto_id == producto_id
            and precio.vigente
            and (en_fecha is None or precio.es_vigente_en(en_fecha))
        ]
        if not candidatos:
            return None
        return max(candidatos, key=lambda precio: (precio.fecha_registro, precio.id))

    def listar_por_producto(
        self,
        producto_id: str,
        *,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> list[PrecioMercado]:
        precios = [
            precio
            for precio in self._precios.values()
            if precio.producto_id == producto_id
        ]
        precios.sort(key=lambda precio: (precio.fecha_registro, precio.id), reverse=True)
        return precios[desplazamiento : desplazamiento + limite]


class PrecioReportadoRepositorioEnMemoria(PrecioReportadoRepositorio):
    """Repositorio de precios reportados en un diccionario."""

    def __init__(self) -> None:
        self._precios: dict[str, PrecioReportado] = {}

    def guardar(self, precio: PrecioReportado) -> None:
        self._precios[precio.id] = precio

    def obtener_por_id(self, precio_id: str) -> PrecioReportado | None:
        return self._precios.get(precio_id)

    def listar_por_producto(
        self,
        producto_id: str,
        *,
        desde: date | None = None,
        hasta: date | None = None,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> list[PrecioReportado]:
        precios = self._filtrar(producto_id=producto_id, desde=desde, hasta=hasta)
        precios.sort(key=lambda precio: (precio.fecha_reporte, precio.id), reverse=True)
        return precios[desplazamiento : desplazamiento + limite]

    def contar_por_producto(
        self,
        producto_id: str,
        *,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> int:
        return len(self._filtrar(producto_id=producto_id, desde=desde, hasta=hasta))

    def _filtrar(
        self,
        *,
        producto_id: str,
        desde: date | None,
        hasta: date | None,
    ) -> list[PrecioReportado]:
        return [
            precio
            for precio in self._precios.values()
            if precio.producto_id == producto_id
            and (desde is None or precio.fecha_reporte >= desde)
            and (hasta is None or precio.fecha_reporte <= hasta)
        ]


class EvaluacionPrecioRepositorioEnMemoria(EvaluacionPrecioRepositorio):
    """Repositorio de evaluaciones en un diccionario."""

    def __init__(self) -> None:
        self._evaluaciones: dict[str, EvaluacionPrecio] = {}

    def guardar(self, evaluacion: EvaluacionPrecio) -> None:
        self._evaluaciones[evaluacion.id] = evaluacion

    def obtener_por_id(self, evaluacion_id: str) -> EvaluacionPrecio | None:
        return self._evaluaciones.get(evaluacion_id)

    def listar(
        self,
        *,
        producto_id: str | None = None,
        nivel_riesgo: NivelRiesgo | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> list[EvaluacionPrecio]:
        evaluaciones = self._filtrar(
            producto_id=producto_id,
            nivel_riesgo=nivel_riesgo,
            desde=desde,
            hasta=hasta,
        )
        evaluaciones.sort(
            key=lambda evaluacion: (evaluacion.evaluado_en, evaluacion.id),
            reverse=True,
        )
        return evaluaciones[desplazamiento : desplazamiento + limite]

    def contar(
        self,
        *,
        producto_id: str | None = None,
        nivel_riesgo: NivelRiesgo | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> int:
        return len(
            self._filtrar(
                producto_id=producto_id,
                nivel_riesgo=nivel_riesgo,
                desde=desde,
                hasta=hasta,
            )
        )

    def resumen_por_nivel(
        self,
        *,
        producto_id: str | None = None,
    ) -> Mapping[NivelRiesgo, int]:
        conteo: dict[NivelRiesgo, int] = {nivel: 0 for nivel in NivelRiesgo}
        for evaluacion in self._evaluaciones.values():
            if producto_id is None or evaluacion.producto_id == producto_id:
                conteo[evaluacion.nivel_riesgo] += 1
        return conteo

    def _filtrar(
        self,
        *,
        producto_id: str | None,
        nivel_riesgo: NivelRiesgo | None,
        desde: datetime | None,
        hasta: datetime | None,
    ) -> list[EvaluacionPrecio]:
        return [
            evaluacion
            for evaluacion in self._evaluaciones.values()
            if (producto_id is None or evaluacion.producto_id == producto_id)
            and (nivel_riesgo is None or evaluacion.nivel_riesgo is nivel_riesgo)
            and (desde is None or evaluacion.evaluado_en >= desde)
            and (hasta is None or evaluacion.evaluado_en <= hasta)
        ]

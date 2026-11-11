"""Puertos de salida (interfaces abstractas) para la persistencia.

La infraestructura (Firestore) implementará estas ABCs. La capa de aplicación
solo conoce estos contratos, nunca el SDK de Firebase.

Convenciones de contrato:
- Los métodos de escritura son *upsert* por identificador.
- ``reemplazar_vigente`` debe ser atómico: desactiva el precio vigente anterior
  del producto y persiste el nuevo en una sola operación lógica.
- ``listar`` devuelve listas ordenadas de forma estable y aplica paginación.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import date, datetime

from ...domain.entities.evaluacion_precio import EvaluacionPrecio
from ...domain.entities.precio_mercado import PrecioMercado
from ...domain.entities.precio_reportado import PrecioReportado
from ...domain.entities.producto import Producto
from ...domain.value_objects.categoria_producto import CategoriaProducto
from ...domain.value_objects.nivel_riesgo import NivelRiesgo


class ProductoRepositorio(ABC):
    """Contrato de persistencia para productos."""

    @abstractmethod
    def guardar(self, producto: Producto) -> None:
        """Inserta o actualiza un producto."""

    @abstractmethod
    def obtener_por_id(self, producto_id: str) -> Producto | None:
        """Devuelve el producto o ``None`` si no existe."""

    @abstractmethod
    def obtener_por_nombre(self, nombre_normalizado: str) -> Producto | None:
        """Busca por nombre normalizado (minúsculas, espacios colapsados)."""

    @abstractmethod
    def existe_por_nombre(self, nombre_normalizado: str) -> bool:
        """Indica si ya existe un producto con ese nombre normalizado."""

    @abstractmethod
    def listar(
        self,
        *,
        categoria: CategoriaProducto | None = None,
        incluir_inactivos: bool = False,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> list[Producto]:
        """Lista productos con filtros y paginación."""

    @abstractmethod
    def contar(
        self,
        *,
        categoria: CategoriaProducto | None = None,
        incluir_inactivos: bool = False,
    ) -> int:
        """Cuenta productos con los mismos filtros de ``listar`` (sin paginar)."""


class PrecioMercadoRepositorio(ABC):
    """Contrato de persistencia para precios de referencia."""

    @abstractmethod
    def guardar(self, precio: PrecioMercado) -> None:
        """Inserta o actualiza un precio de mercado."""

    @abstractmethod
    def reemplazar_vigente(self, precio: PrecioMercado) -> None:
        """Desactiva el precio vigente anterior del producto y guarda el nuevo."""

    @abstractmethod
    def obtener_por_id(self, precio_id: str) -> PrecioMercado | None:
        """Devuelve el precio o ``None`` si no existe."""

    @abstractmethod
    def obtener_vigente(
        self,
        producto_id: str,
        *,
        en_fecha: date | None = None,
    ) -> PrecioMercado | None:
        """Devuelve el precio vigente del producto en la fecha indicada."""

    @abstractmethod
    def listar_por_producto(
        self,
        producto_id: str,
        *,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> list[PrecioMercado]:
        """Lista el histórico de precios de mercado de un producto."""


class PrecioReportadoRepositorio(ABC):
    """Contrato de persistencia para precios reportados."""

    @abstractmethod
    def guardar(self, precio: PrecioReportado) -> None:
        """Inserta o actualiza un precio reportado."""

    @abstractmethod
    def obtener_por_id(self, precio_id: str) -> PrecioReportado | None:
        """Devuelve el reporte o ``None`` si no existe."""

    @abstractmethod
    def listar_por_producto(
        self,
        producto_id: str,
        *,
        desde: date | None = None,
        hasta: date | None = None,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> list[PrecioReportado]:
        """Lista reportes de un producto, opcionalmente en un rango de fechas."""

    @abstractmethod
    def contar_por_producto(
        self,
        producto_id: str,
        *,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> int:
        """Cuenta reportes de un producto con los filtros indicados."""


class EvaluacionPrecioRepositorio(ABC):
    """Contrato de persistencia para evaluaciones."""

    @abstractmethod
    def guardar(self, evaluacion: EvaluacionPrecio) -> None:
        """Inserta o actualiza una evaluación."""

    @abstractmethod
    def obtener_por_id(self, evaluacion_id: str) -> EvaluacionPrecio | None:
        """Devuelve la evaluación o ``None`` si no existe."""

    @abstractmethod
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
        """Lista evaluaciones con filtros y paginación, de más reciente a más antigua."""

    @abstractmethod
    def contar(
        self,
        *,
        producto_id: str | None = None,
        nivel_riesgo: NivelRiesgo | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> int:
        """Cuenta evaluaciones con los mismos filtros de ``listar`` (sin paginar)."""

    @abstractmethod
    def resumen_por_nivel(self, *, producto_id: str | None = None) -> Mapping[NivelRiesgo, int]:
        """Devuelve el conteo de evaluaciones por nivel de riesgo."""

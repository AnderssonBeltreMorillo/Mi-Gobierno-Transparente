"""Adaptadores de Firestore para los puertos de persistencia.

La capa de aplicación depende de las ABCs de ``application.ports``; este módulo
las implementa con ``firebase-admin``. El cliente se inyecta para poder usar el
emulador de Firestore o un doble de prueba.

Esquema de colecciones:

- ``productos``: un documento por producto (ID = ``Producto.id``).
- ``precios_mercado``: histórico; solo un documento con ``vigente = true`` por
  producto. ``reemplazar_vigente`` lo garantiza en una transacción.
- ``precios_reportados``: reportes ciudadanos.
- ``evaluaciones``: auditoría inmutable de cada comparación.

Los errores del SDK se traducen a ``ErrorDePersistencia`` y los documentos
corruptos a ``DocumentoInvalidoError`` para no filtrar detalles del proveedor.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any, TypeVar, cast

import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.exceptions import FirebaseError
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import DefaultCredentialsError
from google.cloud.firestore_v1 import Query
from google.cloud.firestore_v1.base_query import FieldFilter

from ..application.ports.repositories import (
    EvaluacionPrecioRepositorio,
    PrecioMercadoRepositorio,
    PrecioReportadoRepositorio,
    ProductoRepositorio,
)
from ..domain.entities.evaluacion_precio import EvaluacionPrecio
from ..domain.entities.precio_mercado import PrecioMercado
from ..domain.entities.precio_reportado import PrecioReportado
from ..domain.entities.producto import Producto
from ..domain.value_objects.categoria_producto import CategoriaProducto
from ..domain.value_objects.nivel_riesgo import NivelRiesgo
from .exceptions import (
    ConfiguracionFaltanteError,
    DocumentoInvalidoError,
    ErrorDePersistencia,
)
from .firestore_documents import (
    evaluacion_a_documento,
    evaluacion_desde_documento,
    precio_mercado_a_documento,
    precio_mercado_desde_documento,
    precio_reportado_a_documento,
    precio_reportado_desde_documento,
    producto_a_documento,
    producto_desde_documento,
)

COLECCION_PRODUCTOS = "productos"
COLECCION_PRECIOS_MERCADO = "precios_mercado"
COLECCION_PRECIOS_REPORTADOS = "precios_reportados"
COLECCION_EVALUACIONES = "evaluaciones"

_T = TypeVar("_T")


def _normalizar_nombre(nombre: str) -> str:
    return " ".join(nombre.split()).casefold()


def _datos_de_documento(documento: Any) -> tuple[str, Mapping[str, object]]:
    """Extrae el ID y el mapa de un ``DocumentSnapshot`` ya existente."""
    datos = documento.to_dict()
    if datos is None:
        raise DocumentoInvalidoError(
            f"El documento '{documento.id}' no contiene datos."
        )
    if not isinstance(datos, Mapping):
        raise DocumentoInvalidoError(
            f"El documento '{documento.id}' no contiene un mapa de campos."
        )
    return str(documento.id), cast(Mapping[str, object], datos)


def _documentos(consulta: Any) -> list[tuple[str, Mapping[str, object]]]:
    """Materializa una consulta como pares ``(id, datos)``."""
    return [_datos_de_documento(documento) for documento in consulta.stream()]


def _documento_individual(
    snapshot: Any,
    *,
    contexto: str,
) -> tuple[str, Mapping[str, object]] | None:
    if not snapshot.exists:
        return None
    try:
        return _datos_de_documento(snapshot)
    except DocumentoInvalidoError as exc:
        raise DocumentoInvalidoError(f"{contexto}: {exc}") from exc


def _contar(consulta: Any) -> int:
    """Cuenta documentos usando la agregación nativa de Firestore.

    ``AggregationQuery.get`` devuelve una lista plana de ``AggregationResult``
    en las versiones recientes y una lista de listas en algunas versiones
    antiguas; se admiten ambas formas.
    """
    try:
        resultados = consulta.count().get()
    except AttributeError:
        return len(list(consulta.stream()))
    if not resultados:
        return 0
    primero = resultados[0]
    if hasattr(primero, "value"):
        return int(primero.value)
    return int(primero[0].value)


class _RepositorioFirestore:
    """Base con cliente, nombre de colección y traducción de errores."""

    _coleccion: str

    def __init__(self, cliente: firestore.Client) -> None:
        self._cliente = cliente

    @property
    def _referencia(self) -> Any:
        return self._cliente.collection(self._coleccion)

    def _ejecutar(self, operacion: Callable[[], _T], *, contexto: str) -> _T:
        try:
            return operacion()
        except (GoogleAPICallError, FirebaseError) as exc:
            raise ErrorDePersistencia(f"No se pudo {contexto}: {exc}") from exc


class ProductoRepositorioFirestore(_RepositorioFirestore, ProductoRepositorio):
    """Implementación del puerto ``ProductoRepositorio`` sobre Firestore."""

    _coleccion = COLECCION_PRODUCTOS

    def guardar(self, producto: Producto) -> None:
        self._ejecutar(
            lambda: self._referencia.document(producto.id).set(
                producto_a_documento(producto)
            ),
            contexto=f"guardar el producto '{producto.id}'",
        )

    def obtener_por_id(self, producto_id: str) -> Producto | None:
        def operacion() -> Producto | None:
            snapshot = self._referencia.document(producto_id).get()
            encontrado = _documento_individual(
                snapshot,
                contexto=f"producto '{producto_id}'",
            )
            if encontrado is None:
                return None
            documento_id, datos = encontrado
            return producto_desde_documento(datos, documento_id=documento_id)

        return self._ejecutar(
            operacion,
            contexto=f"obtener el producto '{producto_id}'",
        )

    def obtener_por_nombre(self, nombre_normalizado: str) -> Producto | None:
        buscado = _normalizar_nombre(nombre_normalizado)
        if not buscado:
            return None

        def operacion() -> Producto | None:
            consulta = (
                self._referencia.where(
                    filter=FieldFilter("nombre_normalizado", "==", buscado)
                )
                .limit(1)
            )
            documentos = _documentos(consulta)
            if not documentos:
                return None
            documento_id, datos = documentos[0]
            return producto_desde_documento(datos, documento_id=documento_id)

        return self._ejecutar(
            operacion,
            contexto=f"buscar el producto '{buscado}'",
        )

    def existe_por_nombre(self, nombre_normalizado: str) -> bool:
        buscado = _normalizar_nombre(nombre_normalizado)
        if not buscado:
            return False

        def operacion() -> bool:
            consulta = self._referencia.where(
                filter=FieldFilter("nombre_normalizado", "==", buscado)
            ).limit(1)
            return bool(_documentos(consulta))

        return self._ejecutar(
            operacion,
            contexto=f"verificar el producto '{buscado}'",
        )

    def listar(
        self,
        *,
        categoria: CategoriaProducto | None = None,
        incluir_inactivos: bool = False,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> list[Producto]:
        if limite <= 0:
            return []

        def operacion() -> list[Producto]:
            # Solo se usan filtros de igualdad: Firestore los resuelve con los
            # índices de un solo campo (index merging) y no exige un índice
            # compuesto. El orden y la paginación se aplican en memoria; para
            # el volumen del demo es suficiente y evita depender de que el
            # índice compuesto esté creado en cada proyecto.
            consulta = self._referencia
            if categoria is not None:
                consulta = consulta.where(
                    filter=FieldFilter("categoria", "==", categoria.value)
                )
            if not incluir_inactivos:
                consulta = consulta.where(filter=FieldFilter("activo", "==", True))

            productos = [
                producto_desde_documento(datos, documento_id=documento_id)
                for documento_id, datos in _documentos(consulta)
            ]
            productos.sort(
                key=lambda producto: (
                    producto.nombre_normalizado,
                    producto.id,
                )
            )
            inicio = max(0, desplazamiento)
            return productos[inicio : inicio + limite]

        return self._ejecutar(operacion, contexto="listar productos")

    def contar(
        self,
        *,
        categoria: CategoriaProducto | None = None,
        incluir_inactivos: bool = False,
    ) -> int:
        def operacion() -> int:
            consulta = self._referencia
            if categoria is not None:
                consulta = consulta.where(
                    filter=FieldFilter("categoria", "==", categoria.value)
                )
            if not incluir_inactivos:
                consulta = consulta.where(filter=FieldFilter("activo", "==", True))
            return _contar(consulta)

        return self._ejecutar(operacion, contexto="contar productos")


class PrecioMercadoRepositorioFirestore(
    _RepositorioFirestore,
    PrecioMercadoRepositorio,
):
    """Implementación del puerto ``PrecioMercadoRepositorio`` sobre Firestore."""

    _coleccion = COLECCION_PRECIOS_MERCADO

    def guardar(self, precio: PrecioMercado) -> None:
        self._ejecutar(
            lambda: self._referencia.document(precio.id).set(
                precio_mercado_a_documento(precio)
            ),
            contexto=f"guardar el precio de mercado '{precio.id}'",
        )

    def reemplazar_vigente(self, precio: PrecioMercado) -> None:
        nuevo = replace(precio, vigente=True)

        # ``firestore.transactional`` inicia la transacción, reintenta ante
        # conflictos y hace commit al terminar. Usar el context manager de
        # ``Transaction`` no basta: no llama a ``_begin`` en esta versión del
        # SDK y la primera lectura falla con "Transaction not in progress".
        @firestore.transactional  # type: ignore[untyped-decorator]
        def operacion(transaccion: Any) -> None:
            consulta = self._referencia.where(
                filter=FieldFilter("producto_id", "==", nuevo.producto_id)
            ).where(filter=FieldFilter("vigente", "==", True))
            vigentes = list(consulta.stream(transaction=transaccion))
            for documento in vigentes:
                transaccion.update(documento.reference, {"vigente": False})
            transaccion.set(
                self._referencia.document(nuevo.id),
                precio_mercado_a_documento(nuevo),
            )

        self._ejecutar(
            lambda: operacion(self._cliente.transaction()),
            contexto=(
                "reemplazar el precio vigente del producto "
                f"'{nuevo.producto_id}'"
            ),
        )

    def obtener_por_id(self, precio_id: str) -> PrecioMercado | None:
        def operacion() -> PrecioMercado | None:
            snapshot = self._referencia.document(precio_id).get()
            encontrado = _documento_individual(
                snapshot,
                contexto=f"precio de mercado '{precio_id}'",
            )
            if encontrado is None:
                return None
            documento_id, datos = encontrado
            return precio_mercado_desde_documento(datos, documento_id=documento_id)

        return self._ejecutar(
            operacion,
            contexto=f"obtener el precio de mercado '{precio_id}'",
        )

    def obtener_vigente(
        self,
        producto_id: str,
        *,
        en_fecha: date | None = None,
    ) -> PrecioMercado | None:
        def operacion() -> PrecioMercado | None:
            # La consulta usa solo filtros de igualdad: Firestore puede
            # resolverla con los índices de un solo campo (index merging). El
            # filtro por fecha y el orden se aplican en memoria porque, por
            # invariante, solo existe un precio vigente por producto.
            consulta = self._referencia.where(
                filter=FieldFilter("producto_id", "==", producto_id)
            ).where(filter=FieldFilter("vigente", "==", True))

            candidatos: list[PrecioMercado] = []
            for documento_id, datos in _documentos(consulta):
                precio = precio_mercado_desde_documento(
                    datos,
                    documento_id=documento_id,
                )
                if en_fecha is None or precio.fecha_registro <= en_fecha:
                    candidatos.append(precio)

            if not candidatos:
                return None
            return max(
                candidatos,
                key=lambda precio: (precio.fecha_registro, precio.id),
            )

        return self._ejecutar(
            operacion,
            contexto=f"obtener el precio vigente del producto '{producto_id}'",
        )

    def listar_por_producto(
        self,
        producto_id: str,
        *,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> list[PrecioMercado]:
        if limite <= 0:
            return []

        def operacion() -> list[PrecioMercado]:
            consulta = (
                self._referencia.where(
                    filter=FieldFilter("producto_id", "==", producto_id)
                )
                .order_by("fecha_registro", direction=Query.DESCENDING)
                .order_by("__name__", direction=Query.DESCENDING)
                .offset(max(0, desplazamiento))
                .limit(limite)
            )
            return [
                precio_mercado_desde_documento(datos, documento_id=documento_id)
                for documento_id, datos in _documentos(consulta)
            ]

        return self._ejecutar(
            operacion,
            contexto=f"listar precios de mercado del producto '{producto_id}'",
        )


class PrecioReportadoRepositorioFirestore(
    _RepositorioFirestore,
    PrecioReportadoRepositorio,
):
    """Implementación del puerto ``PrecioReportadoRepositorio`` sobre Firestore."""

    _coleccion = COLECCION_PRECIOS_REPORTADOS

    def guardar(self, precio: PrecioReportado) -> None:
        self._ejecutar(
            lambda: self._referencia.document(precio.id).set(
                precio_reportado_a_documento(precio)
            ),
            contexto=f"guardar el precio reportado '{precio.id}'",
        )

    def obtener_por_id(self, precio_id: str) -> PrecioReportado | None:
        def operacion() -> PrecioReportado | None:
            snapshot = self._referencia.document(precio_id).get()
            encontrado = _documento_individual(
                snapshot,
                contexto=f"precio reportado '{precio_id}'",
            )
            if encontrado is None:
                return None
            documento_id, datos = encontrado
            return precio_reportado_desde_documento(
                datos,
                documento_id=documento_id,
            )

        return self._ejecutar(
            operacion,
            contexto=f"obtener el precio reportado '{precio_id}'",
        )

    def listar_por_producto(
        self,
        producto_id: str,
        *,
        desde: date | None = None,
        hasta: date | None = None,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> list[PrecioReportado]:
        if limite <= 0:
            return []

        def operacion() -> list[PrecioReportado]:
            consulta = self._consulta_filtrada(
                producto_id=producto_id,
                desde=desde,
                hasta=hasta,
            )
            consulta = (
                consulta.order_by("fecha_reporte", direction=Query.DESCENDING)
                .order_by("__name__", direction=Query.DESCENDING)
                .offset(max(0, desplazamiento))
                .limit(limite)
            )
            return [
                precio_reportado_desde_documento(datos, documento_id=documento_id)
                for documento_id, datos in _documentos(consulta)
            ]

        return self._ejecutar(
            operacion,
            contexto=f"listar precios reportados del producto '{producto_id}'",
        )

    def contar_por_producto(
        self,
        producto_id: str,
        *,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> int:
        def operacion() -> int:
            consulta = self._consulta_filtrada(
                producto_id=producto_id,
                desde=desde,
                hasta=hasta,
            )
            return _contar(consulta)

        return self._ejecutar(
            operacion,
            contexto=f"contar precios reportados del producto '{producto_id}'",
        )

    def _consulta_filtrada(
        self,
        *,
        producto_id: str,
        desde: date | None,
        hasta: date | None,
    ) -> Any:
        consulta = self._referencia.where(
            filter=FieldFilter("producto_id", "==", producto_id)
        )
        if desde is not None:
            consulta = consulta.where(
                filter=FieldFilter("fecha_reporte", ">=", desde.isoformat())
            )
        if hasta is not None:
            consulta = consulta.where(
                filter=FieldFilter("fecha_reporte", "<=", hasta.isoformat())
            )
        return consulta


class EvaluacionPrecioRepositorioFirestore(
    _RepositorioFirestore,
    EvaluacionPrecioRepositorio,
):
    """Implementación del puerto ``EvaluacionPrecioRepositorio`` sobre Firestore."""

    _coleccion = COLECCION_EVALUACIONES

    def guardar(self, evaluacion: EvaluacionPrecio) -> None:
        self._ejecutar(
            lambda: self._referencia.document(evaluacion.id).set(
                evaluacion_a_documento(evaluacion)
            ),
            contexto=f"guardar la evaluación '{evaluacion.id}'",
        )

    def obtener_por_id(self, evaluacion_id: str) -> EvaluacionPrecio | None:
        def operacion() -> EvaluacionPrecio | None:
            snapshot = self._referencia.document(evaluacion_id).get()
            encontrado = _documento_individual(
                snapshot,
                contexto=f"evaluación '{evaluacion_id}'",
            )
            if encontrado is None:
                return None
            documento_id, datos = encontrado
            return evaluacion_desde_documento(datos, documento_id=documento_id)

        return self._ejecutar(
            operacion,
            contexto=f"obtener la evaluación '{evaluacion_id}'",
        )

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
        if limite <= 0:
            return []

        def operacion() -> list[EvaluacionPrecio]:
            consulta = self._consulta_filtrada(
                producto_id=producto_id,
                nivel_riesgo=nivel_riesgo,
                desde=desde,
                hasta=hasta,
            )
            consulta = (
                consulta.order_by("evaluado_en", direction=Query.DESCENDING)
                .order_by("__name__", direction=Query.DESCENDING)
                .offset(max(0, desplazamiento))
                .limit(limite)
            )
            return [
                evaluacion_desde_documento(datos, documento_id=documento_id)
                for documento_id, datos in _documentos(consulta)
            ]

        return self._ejecutar(operacion, contexto="listar evaluaciones")

    def contar(
        self,
        *,
        producto_id: str | None = None,
        nivel_riesgo: NivelRiesgo | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> int:
        def operacion() -> int:
            consulta = self._consulta_filtrada(
                producto_id=producto_id,
                nivel_riesgo=nivel_riesgo,
                desde=desde,
                hasta=hasta,
            )
            return _contar(consulta)

        return self._ejecutar(operacion, contexto="contar evaluaciones")

    def resumen_por_nivel(
        self,
        *,
        producto_id: str | None = None,
    ) -> Mapping[NivelRiesgo, int]:
        def operacion() -> Mapping[NivelRiesgo, int]:
            return {
                nivel: _contar(
                    self._consulta_filtrada(
                        producto_id=producto_id,
                        nivel_riesgo=nivel,
                        desde=None,
                        hasta=None,
                    )
                )
                for nivel in NivelRiesgo
            }

        return self._ejecutar(operacion, contexto="resumir evaluaciones por nivel")

    def _consulta_filtrada(
        self,
        *,
        producto_id: str | None,
        nivel_riesgo: NivelRiesgo | None,
        desde: datetime | None,
        hasta: datetime | None,
    ) -> Any:
        consulta = self._referencia
        if producto_id is not None:
            consulta = consulta.where(
                filter=FieldFilter("producto_id", "==", producto_id)
            )
        if nivel_riesgo is not None:
            consulta = consulta.where(
                filter=FieldFilter(
                    "resultado.nivel_riesgo",
                    "==",
                    nivel_riesgo.value,
                )
            )
        if desde is not None:
            consulta = consulta.where(
                filter=FieldFilter("evaluado_en", ">=", desde)
            )
        if hasta is not None:
            consulta = consulta.where(
                filter=FieldFilter("evaluado_en", "<=", hasta)
            )
        return consulta


@dataclass(frozen=True, slots=True)
class RepositoriosFirestore:
    """Conjunto de repositorios que comparten un mismo cliente de Firestore."""

    productos: ProductoRepositorioFirestore
    precios_mercado: PrecioMercadoRepositorioFirestore
    precios_reportados: PrecioReportadoRepositorioFirestore
    evaluaciones: EvaluacionPrecioRepositorioFirestore

    @classmethod
    def desde_cliente(cls, cliente: firestore.Client) -> RepositoriosFirestore:
        return cls(
            productos=ProductoRepositorioFirestore(cliente),
            precios_mercado=PrecioMercadoRepositorioFirestore(cliente),
            precios_reportados=PrecioReportadoRepositorioFirestore(cliente),
            evaluaciones=EvaluacionPrecioRepositorioFirestore(cliente),
        )


def crear_cliente_firestore(
    *,
    project_id: str | None = None,
    ruta_credenciales: str | Path | None = None,
    credenciales_json: Mapping[str, object] | None = None,
    emulador_host: str | None = None,
    nombre_app: str = "mi-gobierno-transparente",
) -> firestore.Client:
    """Inicializa (una sola vez) la app de Firebase y devuelve el cliente.

    Si ``emulador_host`` está presente, configura ``FIRESTORE_EMULATOR_HOST``
    antes de crear el cliente. En producción se recomienda usar Application
    Default Credentials (``GOOGLE_APPLICATION_CREDENTIALS``) en lugar de una
    ruta explícita.
    """
    if emulador_host:
        os.environ["FIRESTORE_EMULATOR_HOST"] = emulador_host

    opciones: dict[str, object] = {}
    if project_id:
        opciones["projectId"] = project_id

    try:
        app = firebase_admin.get_app(nombre_app)
    except ValueError:
        credencial = None
        if ruta_credenciales is not None:
            credencial = credentials.Certificate(str(ruta_credenciales))
        elif credenciales_json is not None:
            credencial = credentials.Certificate(dict(credenciales_json))
        try:
            app = firebase_admin.initialize_app(
                credencial,
                opciones or None,
                name=nombre_app,
            )
        except (
            FirebaseError,
            OSError,
            ValueError,
            DefaultCredentialsError,
        ) as exc:
            raise ConfiguracionFaltanteError(
                "No se pudo inicializar Firebase. Verifique las credenciales, "
                "el project_id o las variables de entorno."
            ) from exc

    return firestore.client(app=app)


__all__ = [
    "COLECCION_EVALUACIONES",
    "COLECCION_PRECIOS_MERCADO",
    "COLECCION_PRECIOS_REPORTADOS",
    "COLECCION_PRODUCTOS",
    "EvaluacionPrecioRepositorioFirestore",
    "PrecioMercadoRepositorioFirestore",
    "PrecioReportadoRepositorioFirestore",
    "ProductoRepositorioFirestore",
    "RepositoriosFirestore",
    "crear_cliente_firestore",
]

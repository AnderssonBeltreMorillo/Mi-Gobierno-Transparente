"""Conversión pura entre entidades de dominio y documentos de Firestore.

Este módulo no importa ``firebase-admin``: solo describe el esquema de los
documentos y valida lo leído. Así el mapeo puede probarse sin emulador ni
credenciales.

Decisiones de persistencia:

- ``Decimal`` se guarda como texto para no perder precisión (Firestore no tiene
  un tipo decimal nativo).
- ``date`` se guarda como texto ISO ``YYYY-MM-DD`` para que los rangos sean
  ordenables lexicográficamente.
- ``datetime`` se guarda como timestamp nativo de Firestore.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import cast

from ..domain.entities.evaluacion_precio import EvaluacionPrecio
from ..domain.entities.precio_mercado import PrecioMercado
from ..domain.entities.precio_reportado import PrecioReportado
from ..domain.entities.producto import Producto
from ..domain.exceptions import ErrorDeDominio
from ..domain.value_objects.categoria_producto import CategoriaProducto
from ..domain.value_objects.dinero import Dinero
from ..domain.value_objects.nivel_riesgo import NivelRiesgo
from ..domain.value_objects.porcentaje import Porcentaje
from ..domain.value_objects.resultado_evaluacion import ResultadoEvaluacion
from ..domain.value_objects.umbrales_evaluacion import UmbralesEvaluacion
from ..domain.value_objects.unidad_medida import UnidadMedida
from .exceptions import DocumentoInvalidoError

_CAMPO_MONTO = "monto"
_CAMPO_MONEDA = "moneda"


def _texto_requerido(
    datos: Mapping[str, object],
    campo: str,
    *,
    contexto: str,
) -> str:
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise DocumentoInvalidoError(
            f"{contexto}: el campo '{campo}' debe ser un texto no vacío."
        )
    return valor.strip()


def _texto_opcional(
    datos: Mapping[str, object],
    campo: str,
    *,
    contexto: str,
) -> str | None:
    valor = datos.get(campo)
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise DocumentoInvalidoError(
            f"{contexto}: el campo '{campo}' debe ser texto o nulo."
        )
    limpio = valor.strip()
    return limpio or None


def _booleano_requerido(
    datos: Mapping[str, object],
    campo: str,
    *,
    contexto: str,
) -> bool:
    valor = datos.get(campo)
    if not isinstance(valor, bool):
        raise DocumentoInvalidoError(
            f"{contexto}: el campo '{campo}' debe ser booleano."
        )
    return valor


def _mapa_requerido(
    datos: Mapping[str, object],
    campo: str,
    *,
    contexto: str,
) -> Mapping[str, object]:
    valor = datos.get(campo)
    if not isinstance(valor, Mapping):
        raise DocumentoInvalidoError(
            f"{contexto}: el campo '{campo}' debe ser un mapa."
        )
    return cast(Mapping[str, object], valor)


def _fecha_requerida(
    datos: Mapping[str, object],
    campo: str,
    *,
    contexto: str,
) -> date:
    texto = _texto_requerido(datos, campo, contexto=contexto)
    try:
        return date.fromisoformat(texto)
    except ValueError as exc:
        raise DocumentoInvalidoError(
            f"{contexto}: el campo '{campo}' no es una fecha ISO válida."
        ) from exc


def _datetime_requerido(
    datos: Mapping[str, object],
    campo: str,
    *,
    contexto: str,
) -> datetime:
    valor = datos.get(campo)
    if (
        not isinstance(valor, datetime)
        or valor.tzinfo is None
        or valor.utcoffset() is None
    ):
        raise DocumentoInvalidoError(
            f"{contexto}: el campo '{campo}' debe ser un datetime con zona horaria."
        )
    return valor


def _dinero_requerido(
    datos: Mapping[str, object],
    campo: str,
    *,
    contexto: str,
) -> Dinero:
    mapa = _mapa_requerido(datos, campo, contexto=contexto)
    monto_texto = _texto_requerido(
        mapa,
        _CAMPO_MONTO,
        contexto=f"{contexto}.{campo}",
    )
    moneda = _texto_requerido(
        mapa,
        _CAMPO_MONEDA,
        contexto=f"{contexto}.{campo}",
    )
    try:
        return Dinero(Decimal(monto_texto), moneda)
    except (InvalidOperation, ErrorDeDominio) as exc:
        raise DocumentoInvalidoError(
            f"{contexto}: el campo '{campo}' no contiene un importe válido."
        ) from exc


def _porcentaje_requerido(
    datos: Mapping[str, object],
    campo: str,
    *,
    contexto: str,
) -> Porcentaje:
    texto = _texto_requerido(datos, campo, contexto=contexto)
    try:
        return Porcentaje(Decimal(texto))
    except (InvalidOperation, ErrorDeDominio) as exc:
        raise DocumentoInvalidoError(
            f"{contexto}: el campo '{campo}' no contiene un porcentaje válido."
        ) from exc


def dinero_a_documento(dinero: Dinero) -> dict[str, object]:
    """Serializa un importe sin convertir ``Decimal`` a ``float``."""
    return {
        _CAMPO_MONTO: str(dinero.monto),
        _CAMPO_MONEDA: dinero.moneda,
    }


def producto_a_documento(producto: Producto) -> dict[str, object]:
    """Documento de la colección ``productos``."""
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "nombre_normalizado": producto.nombre_normalizado,
        "categoria": producto.categoria.value,
        "unidad_medida": producto.unidad_medida.value,
        "marca": producto.marca,
        "descripcion": producto.descripcion,
        "activo": producto.activo,
    }


def producto_desde_documento(
    datos: Mapping[str, object],
    *,
    documento_id: str | None = None,
) -> Producto:
    """Reconstruye un ``Producto`` validando todas sus invariantes."""
    contexto = "producto"
    identificador = _texto_opcional(datos, "id", contexto=contexto) or documento_id
    if identificador is None:
        raise DocumentoInvalidoError(
            "producto: falta el identificador del documento."
        )

    categoria_texto = _texto_requerido(datos, "categoria", contexto=contexto)
    unidad_texto = _texto_requerido(datos, "unidad_medida", contexto=contexto)

    try:
        return Producto(
            id=identificador,
            nombre=_texto_requerido(datos, "nombre", contexto=contexto),
            categoria=CategoriaProducto.desde_valor(categoria_texto),
            unidad_medida=UnidadMedida(unidad_texto),
            marca=_texto_opcional(datos, "marca", contexto=contexto),
            descripcion=_texto_opcional(datos, "descripcion", contexto=contexto),
            activo=_booleano_requerido(datos, "activo", contexto=contexto),
        )
    except (ErrorDeDominio, ValueError) as exc:
        raise DocumentoInvalidoError(
            f"producto: el documento no cumple las reglas de dominio ({exc})."
        ) from exc


def precio_mercado_a_documento(precio: PrecioMercado) -> dict[str, object]:
    """Documento de la colección ``precios_mercado``."""
    return {
        "id": precio.id,
        "producto_id": precio.producto_id,
        "precio": dinero_a_documento(precio.precio),
        "fuente": precio.fuente,
        "fecha_registro": precio.fecha_registro.isoformat(),
        "vigente": precio.vigente,
    }


def precio_mercado_desde_documento(
    datos: Mapping[str, object],
    *,
    documento_id: str | None = None,
) -> PrecioMercado:
    """Reconstruye un ``PrecioMercado`` validando sus invariantes."""
    contexto = "precio_mercado"
    identificador = _texto_opcional(datos, "id", contexto=contexto) or documento_id
    if identificador is None:
        raise DocumentoInvalidoError(
            "precio_mercado: falta el identificador del documento."
        )

    try:
        return PrecioMercado(
            id=identificador,
            producto_id=_texto_requerido(datos, "producto_id", contexto=contexto),
            precio=_dinero_requerido(datos, "precio", contexto=contexto),
            fuente=_texto_requerido(datos, "fuente", contexto=contexto),
            fecha_registro=_fecha_requerida(
                datos,
                "fecha_registro",
                contexto=contexto,
            ),
            vigente=_booleano_requerido(datos, "vigente", contexto=contexto),
        )
    except ErrorDeDominio as exc:
        raise DocumentoInvalidoError(
            f"precio_mercado: el documento no cumple las reglas de dominio ({exc})."
        ) from exc


def precio_reportado_a_documento(precio: PrecioReportado) -> dict[str, object]:
    """Documento de la colección ``precios_reportados``."""
    return {
        "id": precio.id,
        "producto_id": precio.producto_id,
        "precio": dinero_a_documento(precio.precio),
        "establecimiento": precio.establecimiento,
        "fecha_reporte": precio.fecha_reporte.isoformat(),
        "distrito": precio.distrito,
        "reportado_por": precio.reportado_por,
    }


def precio_reportado_desde_documento(
    datos: Mapping[str, object],
    *,
    documento_id: str | None = None,
) -> PrecioReportado:
    """Reconstruye un ``PrecioReportado`` validando sus invariantes."""
    contexto = "precio_reportado"
    identificador = _texto_opcional(datos, "id", contexto=contexto) or documento_id
    if identificador is None:
        raise DocumentoInvalidoError(
            "precio_reportado: falta el identificador del documento."
        )

    try:
        return PrecioReportado(
            id=identificador,
            producto_id=_texto_requerido(datos, "producto_id", contexto=contexto),
            precio=_dinero_requerido(datos, "precio", contexto=contexto),
            establecimiento=_texto_requerido(
                datos,
                "establecimiento",
                contexto=contexto,
            ),
            fecha_reporte=_fecha_requerida(
                datos,
                "fecha_reporte",
                contexto=contexto,
            ),
            distrito=_texto_opcional(datos, "distrito", contexto=contexto),
            reportado_por=_texto_opcional(datos, "reportado_por", contexto=contexto),
        )
    except ErrorDeDominio as exc:
        raise DocumentoInvalidoError(
            f"precio_reportado: el documento no cumple las reglas de dominio ({exc})."
        ) from exc


def resultado_a_documento(resultado: ResultadoEvaluacion) -> dict[str, object]:
    """Serializa la foto auditable de una evaluación."""
    return {
        "precio_reportado": dinero_a_documento(resultado.precio_reportado),
        "precio_mercado": dinero_a_documento(resultado.precio_mercado),
        "excedente": dinero_a_documento(resultado.excedente),
        "sobreprecio": str(resultado.sobreprecio.fraccion),
        "nivel_riesgo": resultado.nivel_riesgo.value,
        "umbrales": {
            "alerta_amarilla_desde": str(
                resultado.umbrales.alerta_amarilla_desde.fraccion
            ),
            "alto_riesgo_desde": str(resultado.umbrales.alto_riesgo_desde.fraccion),
        },
    }


def resultado_desde_documento(
    datos: Mapping[str, object],
    *,
    contexto: str = "resultado",
) -> ResultadoEvaluacion:
    """Reconstruye y revalida la foto de una evaluación."""
    umbrales_datos = _mapa_requerido(datos, "umbrales", contexto=contexto)
    nivel_texto = _texto_requerido(datos, "nivel_riesgo", contexto=contexto)

    try:
        nivel = NivelRiesgo(nivel_texto)
        umbrales = UmbralesEvaluacion(
            alerta_amarilla_desde=_porcentaje_requerido(
                umbrales_datos,
                "alerta_amarilla_desde",
                contexto=f"{contexto}.umbrales",
            ),
            alto_riesgo_desde=_porcentaje_requerido(
                umbrales_datos,
                "alto_riesgo_desde",
                contexto=f"{contexto}.umbrales",
            ),
        )
        return ResultadoEvaluacion(
            precio_reportado=_dinero_requerido(
                datos,
                "precio_reportado",
                contexto=contexto,
            ),
            precio_mercado=_dinero_requerido(
                datos,
                "precio_mercado",
                contexto=contexto,
            ),
            excedente=_dinero_requerido(datos, "excedente", contexto=contexto),
            sobreprecio=_porcentaje_requerido(
                datos,
                "sobreprecio",
                contexto=contexto,
            ),
            nivel_riesgo=nivel,
            umbrales=umbrales,
        )
    except (ErrorDeDominio, ValueError) as exc:
        raise DocumentoInvalidoError(
            f"{contexto}: el resultado no cumple las reglas de dominio ({exc})."
        ) from exc


def evaluacion_a_documento(evaluacion: EvaluacionPrecio) -> dict[str, object]:
    """Documento de la colección ``evaluaciones``."""
    return {
        "id": evaluacion.id,
        "producto_id": evaluacion.producto_id,
        "precio_reportado_id": evaluacion.precio_reportado_id,
        "precio_mercado_id": evaluacion.precio_mercado_id,
        "resultado": resultado_a_documento(evaluacion.resultado),
        "evaluado_en": evaluacion.evaluado_en,
        "version_regla": evaluacion.version_regla,
        "observacion": evaluacion.observacion,
    }


def evaluacion_desde_documento(
    datos: Mapping[str, object],
    *,
    documento_id: str | None = None,
) -> EvaluacionPrecio:
    """Reconstruye una ``EvaluacionPrecio`` validando la auditoría completa."""
    contexto = "evaluacion"
    identificador = _texto_opcional(datos, "id", contexto=contexto) or documento_id
    if identificador is None:
        raise DocumentoInvalidoError(
            "evaluacion: falta el identificador del documento."
        )

    try:
        return EvaluacionPrecio(
            id=identificador,
            producto_id=_texto_requerido(datos, "producto_id", contexto=contexto),
            precio_reportado_id=_texto_requerido(
                datos,
                "precio_reportado_id",
                contexto=contexto,
            ),
            precio_mercado_id=_texto_requerido(
                datos,
                "precio_mercado_id",
                contexto=contexto,
            ),
            resultado=resultado_desde_documento(
                _mapa_requerido(datos, "resultado", contexto=contexto),
                contexto=f"{contexto}.resultado",
            ),
            evaluado_en=_datetime_requerido(
                datos,
                "evaluado_en",
                contexto=contexto,
            ),
            version_regla=_texto_requerido(
                datos,
                "version_regla",
                contexto=contexto,
            ),
            observacion=_texto_opcional(datos, "observacion", contexto=contexto),
        )
    except ErrorDeDominio as exc:
        raise DocumentoInvalidoError(
            f"evaluacion: el documento no cumple las reglas de dominio ({exc})."
        ) from exc

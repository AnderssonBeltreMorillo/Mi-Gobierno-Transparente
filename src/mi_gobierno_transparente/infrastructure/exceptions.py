"""Errores propios de la capa de infraestructura.

Los adaptadores traducen fallos de Firestore, HTTP o documentos corruptos a
estas excepciones, de modo que la capa de aplicación no dependa de detalles
de proveedores externos.
"""

from __future__ import annotations


class ErrorDeInfraestructura(Exception):
    """Base para los fallos de adaptadores externos."""

    codigo: str = "error_de_infraestructura"

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje

    def __str__(self) -> str:
        return self.mensaje


class ErrorDePersistencia(ErrorDeInfraestructura):
    """No fue posible leer o escribir en el almacenamiento."""

    codigo = "error_de_persistencia"


class DocumentoInvalidoError(ErrorDePersistencia):
    """Un documento almacenado no respeta el esquema esperado."""

    codigo = "documento_invalido"


class ErrorDeExtraccion(ErrorDeInfraestructura):
    """No fue posible extraer información de un portal externo."""

    codigo = "error_de_extraccion"


class ErrorDeBusquedaMercado(ErrorDeInfraestructura):
    """No fue posible consultar el buscador de supermercados."""

    codigo = "error_de_busqueda_mercado"


class ConfiguracionFaltanteError(ErrorDeInfraestructura):
    """Falta una credencial o parámetro obligatorio del adaptador."""

    codigo = "configuracion_faltante"

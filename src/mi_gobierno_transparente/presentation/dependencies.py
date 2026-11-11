"""Composition root de la capa HTTP.

Aquí se construyen los adaptadores reales (Firestore, reloj, UUID) y se
inyectan en los casos de uso. Los proveedores están memoizados para reutilizar
un único cliente de Firestore durante la vida del proceso.

FastAPI resuelve estas funciones mediante ``Depends``; en pruebas se pueden
sustituir con ``app.dependency_overrides``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from firebase_admin import firestore

from ..application.ports.reloj import Reloj
from ..application.use_cases import (
    ListarEvaluaciones,
    ListarProductos,
    ObtenerResumenRiesgo,
)
from ..infrastructure.firebase_repository import (
    RepositoriosFirestore,
    crear_cliente_firestore,
)
from ..infrastructure.generador_uuid import GeneradorUuid4
from ..infrastructure.reloj_sistema import RelojSistema
from .config import ConfiguracionAPI, cargar_configuracion


@lru_cache(maxsize=1)
def obtener_configuracion() -> ConfiguracionAPI:
    """Devuelve la configuración de la API (memoizada)."""
    return cargar_configuracion()


@lru_cache(maxsize=1)
def obtener_cliente_firestore() -> firestore.Client:
    """Crea y reutiliza el cliente Firestore de la aplicación."""
    configuracion = obtener_configuracion()
    return crear_cliente_firestore(
        project_id=configuracion.project_id,
        ruta_credenciales=configuracion.ruta_credenciales,
        credenciales_json=configuracion.credenciales_json,
        emulador_host=configuracion.emulador_host,
    )


@lru_cache(maxsize=1)
def obtener_repositorios() -> RepositoriosFirestore:
    """Crea el bundle de repositorios de Firestore (memoizado)."""
    return RepositoriosFirestore.desde_cliente(obtener_cliente_firestore())


@lru_cache(maxsize=1)
def obtener_reloj() -> Reloj:
    """Devuelve el reloj del sistema (UTC)."""
    return RelojSistema()


@lru_cache(maxsize=1)
def obtener_generador_identificadores() -> GeneradorUuid4:
    """Devuelve el generador de identificadores UUID4."""
    return GeneradorUuid4()


RepositoriosDep = Annotated[RepositoriosFirestore, Depends(obtener_repositorios)]
ClienteFirestoreDep = Annotated[firestore.Client, Depends(obtener_cliente_firestore)]


def obtener_listar_productos(repositorios: RepositoriosDep) -> ListarProductos:
    """Construye el caso de uso ``ListarProductos``."""
    return ListarProductos(repositorios.productos)


def obtener_listar_evaluaciones(
    repositorios: RepositoriosDep,
) -> ListarEvaluaciones:
    """Construye el caso de uso ``ListarEvaluaciones``."""
    return ListarEvaluaciones(repositorios.evaluaciones)


def obtener_obtener_resumen_riesgo(
    repositorios: RepositoriosDep,
) -> ObtenerResumenRiesgo:
    """Construye el caso de uso ``ObtenerResumenRiesgo``."""
    return ObtenerResumenRiesgo(repositorios.evaluaciones)


ListarProductosDep = Annotated[ListarProductos, Depends(obtener_listar_productos)]
ListarEvaluacionesDep = Annotated[
    ListarEvaluaciones,
    Depends(obtener_listar_evaluaciones),
]
ObtenerResumenRiesgoDep = Annotated[
    ObtenerResumenRiesgo,
    Depends(obtener_obtener_resumen_riesgo),
]


__all__ = [
    "ListarEvaluacionesDep",
    "ListarProductosDep",
    "ClienteFirestoreDep",
    "ObtenerResumenRiesgoDep",
    "obtener_configuracion",
    "obtener_cliente_firestore",
    "obtener_generador_identificadores",
    "obtener_listar_evaluaciones",
    "obtener_listar_productos",
    "obtener_obtener_resumen_riesgo",
    "obtener_reloj",
    "obtener_repositorios",
]

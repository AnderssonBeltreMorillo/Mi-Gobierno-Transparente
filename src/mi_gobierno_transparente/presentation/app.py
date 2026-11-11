"""Aplicación FastAPI del backend 'Mi gobierno transparente'.

La app se construye con una factory (``crear_app``) para facilitar pruebas y
despliegues. El objeto ``app`` de nivel de módulo permite arrancar con:

    uvicorn mi_gobierno_transparente.presentation.app:app --reload
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import cargar_configuracion
from .errors import registrar_manejadores
from .routers import evaluaciones, licitaciones, productos, resumen_riesgo

_TITULO = "Mi gobierno transparente API"
_VERSION = "0.1.0"
_LOGGER = logging.getLogger(__name__)
_DESCRIPCION = (
    "API de transparencia de precios para productos de alimentos y aseo. "
    "Compara precios reportados contra el mercado vigente y clasifica el "
    "sobreprecio en precio justo, alerta amarilla o alto riesgo."
)


async def _ciclo_sincronizacion_dgcp() -> None:
    intervalo = 7200  # cada 2 horas
    while True:
        loop = asyncio.get_running_loop()
        inicio = loop.time()
        try:
            await asyncio.to_thread(_ejecutar_sincronizacion_dgcp)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Falló la sincronización automática de licitaciones DGCP.")
        await asyncio.sleep(max(0.0, intervalo - (loop.time() - inicio)))


def _ejecutar_sincronizacion_dgcp() -> int:
    # Import diferido para evitar que infrastructure.dgcp_sync y el paquete
    # presentation se importen recursivamente durante el arranque de la app.
    from ..infrastructure.dgcp_sync import main

    return main()


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    valor = os.getenv("ENABLE_BACKGROUND_SYNC", "false").strip().casefold()
    tarea = (
        asyncio.create_task(_ciclo_sincronizacion_dgcp(), name="sync-licitaciones-dgcp")
        if valor in {"1", "true", "yes", "on"}
        else None
    )
    try:
        yield
    finally:
        if tarea is not None:
            tarea.cancel()
            try:
                await tarea
            except asyncio.CancelledError:
                pass


def crear_app() -> FastAPI:
    """Construye y configura la aplicación FastAPI."""
    configuracion = cargar_configuracion()

    app = FastAPI(
        title=_TITULO,
        version=_VERSION,
        description=_DESCRIPCION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(configuracion.origenes_cors),
        allow_credentials=configuracion.permitir_credenciales,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(productos.router)
    app.include_router(evaluaciones.router)
    app.include_router(resumen_riesgo.router)
    app.include_router(licitaciones.router)

    registrar_manejadores(app)

    @app.get(
        "/health",
        tags=["sistema"],
        summary="Estado del servicio",
        description="Comprobación de liveness; no consulta Firestore.",
    )
    def health() -> dict[str, str]:
        return {"estado": "ok", "version": _VERSION}

    # Render sirve el bundle construido por Vite desde el mismo proceso.
    raiz = Path(__file__).resolve().parents[3]
    dist = raiz / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app


app = crear_app()


__all__ = ["app", "crear_app"]

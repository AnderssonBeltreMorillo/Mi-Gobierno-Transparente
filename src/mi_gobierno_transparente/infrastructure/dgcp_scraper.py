"""Extractor de precios del portal de compras públicas (DGCP).

La estructura HTML de los portales públicos cambia con frecuencia. Por eso los
selectores CSS son configurables y el flujo de extracción está separado del
transporte HTTP: ``extraer_de_html`` permite probar el parseo sin red.

Esta implementación es un punto de partida. Para producción conviene usar la
API oficial del portal, respetar sus términos de uso y aplicar reintentos con
backoff y límites de frecuencia.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from .exceptions import ErrorDeExtraccion
from .html_utils import texto_de_nodo, url_de_nodo
from .parsing import (
    normalizar_moneda,
    parsear_fecha,
    parsear_precio,
    texto_opcional,
)

_AGENTE_USUARIO: Final[str] = "MiGobiernoTransparente/0.1 (+https://example.org)"
_API_DGCP: Final[str] = "https://datosabiertos.dgcp.gob.do/api-dgcp/v1"


@dataclass(frozen=True, slots=True)
class SelectoresDgcp:
    """Selectores CSS para mapear la tabla de resultados del portal.

    Cada selector se evalúa dentro de la fila (``fila``). Los selectores
    opcionales pueden ser ``None`` si el portal no expone esa columna.
    """

    fila: str = "table tbody tr"
    producto: str = "td.producto"
    precio: str = "td.precio"
    moneda: str | None = None
    proveedor: str | None = "td.proveedor"
    fecha: str | None = "td.fecha"
    enlace: str | None = "a"


@dataclass(frozen=True, slots=True)
class PrecioExtraido:
    """Precio crudo obtenido de un portal externo.

    Es un DTO de infraestructura: todavía no es una entidad de dominio porque
    puede faltar la fecha o el producto puede requerir normalización manual.
    """

    producto: str
    monto: Decimal
    moneda: str
    fuente: str
    fecha: date | None = None
    proveedor: str | None = None
    url: str | None = None


class ExtractorPrecios(ABC):
    """Contrato para fuentes de precios externas (DGCP u otras)."""

    @abstractmethod
    def extraer(self, consulta: str, *, limite: int = 50) -> list[PrecioExtraido]:
        """Devuelve los precios encontrados para ``consulta``."""


class DgcpScraper(ExtractorPrecios):
    """Scraper básico del portal de compras públicas.

    Ejemplo de uso::

        scraper = DgcpScraper("https://portal.compras.gob/buscar")
        precios = scraper.extraer("arroz", limite=20)
    """

    def __init__(
        self,
        base_url: str,
        *,
        selectores: SelectoresDgcp | None = None,
        session: requests.Session | None = None,
        timeout: float = 15.0,
        parametro_busqueda: str = "q",
        fuente: str = "DGCP",
        cabeceras: Mapping[str, str] | None = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("La URL base del portal DGCP es obligatoria.")
        if timeout <= 0:
            raise ValueError("El timeout debe ser mayor que cero.")

        self._base_url = base_url.strip()
        self._selectores = selectores or SelectoresDgcp()
        self._session = session or requests.Session()
        self._timeout = timeout
        self._parametro_busqueda = parametro_busqueda
        self._fuente = fuente

        cabeceras_finales: dict[str, str] = {"User-Agent": _AGENTE_USUARIO}
        if cabeceras is not None:
            cabeceras_finales.update(cabeceras)
        self._session.headers.update(cabeceras_finales)

    def extraer(self, consulta: str, *, limite: int = 50) -> list[PrecioExtraido]:
        """Consulta el portal y devuelve hasta ``limite`` precios válidos.

        Raises:
            ValueError: si la consulta está vacía o ``limite`` no es positivo.
            ErrorDeExtraccion: si falla la petición HTTP o el portal responde
                con un código de error.
        """
        consulta_limpia = texto_opcional(consulta)
        if consulta_limpia is None:
            raise ValueError("La consulta de búsqueda no puede estar vacía.")
        if limite <= 0:
            return []

        try:
            respuesta = self._session.get(
                self._base_url,
                params={self._parametro_busqueda: consulta_limpia},
                timeout=self._timeout,
            )
            respuesta.raise_for_status()
        except requests.RequestException as exc:
            raise ErrorDeExtraccion(
                f"No se pudo consultar el portal DGCP ({self._base_url}): {exc}"
            ) from exc

        url_final = respuesta.url or self._base_url
        return self.extraer_de_html(
            respuesta.text,
            base_url=url_final,
            limite=limite,
        )

    def extraer_de_html(
        self,
        html: str,
        *,
        base_url: str | None = None,
        limite: int = 50,
    ) -> list[PrecioExtraido]:
        """Parsea un HTML ya descargado (útil para pruebas y cachés)."""
        if limite <= 0:
            return []
        if not isinstance(html, str) or not html.strip():
            return []

        sopa = BeautifulSoup(html, "html.parser")
        filas = sopa.select(self._selectores.fila)
        extraidos: list[PrecioExtraido] = []
        for fila in filas:
            precio = self._parsear_fila(
                fila,
                base_url=base_url or self._base_url,
            )
            if precio is None:
                continue
            extraidos.append(precio)
            if len(extraidos) >= limite:
                break
        return extraidos

    def _parsear_fila(self, fila: Tag, *, base_url: str) -> PrecioExtraido | None:
        producto = texto_de_nodo(fila, self._selectores.producto)
        precio_texto = texto_de_nodo(fila, self._selectores.precio)
        if producto is None or precio_texto is None:
            return None

        monto, moneda_detectada = parsear_precio(precio_texto)
        if monto is None or monto <= Decimal("0"):
            return None

        moneda_texto = texto_de_nodo(fila, self._selectores.moneda)
        moneda = normalizar_moneda(moneda_texto, por_defecto=moneda_detectada)

        fecha_texto = texto_de_nodo(fila, self._selectores.fecha)
        fecha = parsear_fecha(fecha_texto)
        proveedor = texto_de_nodo(fila, self._selectores.proveedor)
        url = (
            url_de_nodo(fila, self._selectores.enlace, base_url)
            if self._selectores.enlace
            else None
        )

        return PrecioExtraido(
            producto=producto,
            monto=monto,
            moneda=moneda,
            fuente=self._fuente,
            fecha=fecha,
            proveedor=proveedor,
            url=url,
        )


class DgcpOpenDataClient:
    """Cliente de la API oficial de Datos Abiertos de la DGCP.

    ``/procesos`` permite recorrer procesos por fecha de publicación y
    ``/procesos/articulos`` devuelve sus renglones con cantidades y precios
    unitarios estimados. Los límites de páginas hacen acotada cada sincronización.
    """

    def __init__(
        self,
        *,
        base_url: str = _API_DGCP,
        session: requests.Session | None = None,
        timeout: float = 20.0,
        page_size: int = 100,
    ) -> None:
        if not base_url.strip():
            raise ValueError("La URL base de la API DGCP es obligatoria.")
        if timeout <= 0 or page_size <= 0:
            raise ValueError("El timeout y el tamaño de página deben ser positivos.")
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._timeout = timeout
        self._page_size = min(page_size, 1000)
        self._session.headers.update({"User-Agent": _AGENTE_USUARIO, "Accept": "application/json"})

    def buscar_procesos(
        self,
        *,
        desde: date,
        hasta: date,
        max_paginas: int = 10,
        codigo: str | None = None,
    ) -> list[Mapping[str, object]]:
        """Consulta procesos publicados en el periodo, más recientes primero."""
        if max_paginas <= 0:
            return []
        parametros_base: dict[str, str | int] = {
            "startdate": desde.isoformat(),
            "enddate": hasta.isoformat(),
        }
        if codigo:
            parametros_base["proceso"] = codigo
        return self._paginar("procesos", parametros_base, max_paginas=max_paginas)

    def obtener_articulos(
        self,
        codigo_proceso: str,
        *,
        max_paginas: int = 10,
    ) -> list[Mapping[str, object]]:
        """Devuelve todos los renglones disponibles para un código real."""
        codigo = texto_opcional(codigo_proceso)
        if codigo is None:
            raise ValueError("El código de proceso es obligatorio.")
        if max_paginas <= 0:
            return []
        return self._paginar(
            "procesos/articulos",
            {"proceso": codigo},
            max_paginas=max_paginas,
        )

    def _paginar(
        self,
        ruta: str,
        parametros: Mapping[str, str | int],
        *,
        max_paginas: int,
    ) -> list[Mapping[str, object]]:
        registros: list[Mapping[str, object]] = []
        for pagina in range(1, max_paginas + 1):
            query: dict[str, str | int] = {**parametros, "page": pagina, "limit": self._page_size}
            try:
                respuesta = self._session.get(
                    f"{self._base_url}/{ruta}",
                    params=query,
                    timeout=self._timeout,
                )
                respuesta.raise_for_status()
                documento = respuesta.json()
            except requests.RequestException as exc:
                raise ErrorDeExtraccion(f"No se pudo consultar la API DGCP ({ruta}): {exc}") from exc
            except ValueError as exc:
                raise ErrorDeExtraccion("La API DGCP devolvió una respuesta JSON inválida.") from exc

            if not isinstance(documento, Mapping):
                raise ErrorDeExtraccion("La API DGCP devolvió una estructura inesperada.")
            if documento.get("hasError") is True:
                detalle = documento.get("message") or documento.get("payload")
                raise ErrorDeExtraccion(f"La API DGCP reportó un error: {detalle}")
            payload = documento.get("payload")
            contenido = payload.get("content") if isinstance(payload, Mapping) else None
            if not isinstance(contenido, list):
                raise ErrorDeExtraccion("La respuesta DGCP no contiene una lista payload.content.")
            pagina_registros = [
                registro for registro in contenido if isinstance(registro, Mapping)
            ]
            registros.extend(pagina_registros)
            total_paginas = documento.get("pages")
            if not pagina_registros or (
                isinstance(total_paginas, int) and pagina >= total_paginas
            ):
                break
        return registros


__all__ = [
    "DgcpScraper",
    "DgcpOpenDataClient",
    "ExtractorPrecios",
    "PrecioExtraido",
    "SelectoresDgcp",
]

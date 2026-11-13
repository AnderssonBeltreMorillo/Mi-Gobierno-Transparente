"""Buscador de precios de supermercados.

La aplicación no debe depender de un proveedor concreto de búsqueda. Este
módulo define el puerto ``BuscadorSupermercados`` y una implementación basada
en SerpApi (Google Shopping) usando ``requests``.

La clave se lee del argumento ``api_key`` o de la variable de entorno
``SERPAPI_API_KEY``. El parseo está aislado en ``_parsear_item`` para poder
sustituir SerpApi por otro proveedor sin cambiar el contrato.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from threading import Lock
from time import monotonic
from typing import Final, cast
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from .exceptions import ConfiguracionFaltanteError, ErrorDeBusquedaMercado
from .parsing import (
    normalizar_moneda,
    parsear_precio,
    precio_desde_numero,
    texto_opcional,
)

_URL_SERPAPI: Final[str] = "https://serpapi.com/search.json"
_URL_PLAZALAMA: Final[str] = "https://plazalama.com.do/search"
_AGENTE_USUARIO: Final[str] = "MiGobiernoTransparente/0.1 (+https://example.org)"
_AGENTE_USUARIO_NAVEGADOR: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)
_CADENAS_DOMINIOS: Final[dict[str, str]] = {
    "Nacional": "supermercadosnacional.com",
    "La Sirena": "sirena.do",
    "Jumbo": "jumbo.com.do",
    "Plaza Lama": "plazalama.com.do",
}

# Límites del Escenario A. La proporción se calcula como
# ``tamano_licitado / tamano_catalogo``. El margen general es 0.25x–4.0x.
# Los líquidos de limpieza (PINOL) admiten hasta 5.0x porque un galón contra
# una botella de 828 ml (4.57x) sigue siendo una conversión volumétrica
# verificable; presentaciones de 4 oz o cajas de 4 galones quedan fuera.
_ESCALA_MINIMA: Final[Decimal] = Decimal("0.25")
_ESCALA_MAXIMA: Final[Decimal] = Decimal("4.0")
_ESCALA_MAXIMA_LIQUIDOS: Final[Decimal] = Decimal("5.0")
_GALON_ML: Final[Decimal] = Decimal("3785.41")
_ONZA_FLUIDA_ML: Final[Decimal] = Decimal("29.5735295625")
_LIBRA_G: Final[Decimal] = Decimal("453.59237")
_ONZA_G: Final[Decimal] = Decimal("28.349523125")

# Peso promedio estándar por unidad para el Escenario C cuando el catálogo
# vende por libra sin declarar el peso aproximado del ejemplar.
_PESO_PROMEDIO_LB: Final[dict[str, Decimal]] = {
    "sandia": Decimal("10"),
    "melon": Decimal("5"),
    "pina": Decimal("2"),
    "auyama": Decimal("5"),
    "repollo": Decimal("4"),
}

# Diccionario de exclusiones semánticas (Filtro Negativo para Falsos Positivos)
_PALABRAS_PROHIBIDAS: Final[list[str]] = [
    "pechuga", "pollo", "carne", "cerdo", "res", "tiras", "filete", "muslo", 
    "chicle", "caramelo", "dulce", "trident", "refresco", "jugo", "bebida",
    "adobo", "sazon", "sazonador", "caldo", "sopita",
    "galleta", "bizcocho", "cupcake", "ponque", "helado", "postre", "cepa"
]


@dataclass(frozen=True, slots=True)
class OfertaSupermercado:
    """Oferta encontrada en un buscador de supermercados."""

    producto: str
    establecimiento: str
    monto: Decimal
    moneda: str = "PEN"
    url: str | None = None
    fuente: str = "serpapi"
    equivalencia: str | None = None


class BuscadorSupermercados(ABC):
    """Contrato para buscar precios en supermercados."""

    @abstractmethod
    def buscar(
        self,
        consulta: str,
        *,
        limite: int = 20,
    ) -> list[OfertaSupermercado]:
        """Devuelve ofertas ordenadas según el proveedor consultado."""


def seleccionar_oferta_minima(ofertas: list[OfertaSupermercado]) -> OfertaSupermercado:
    """Devuelve la oferta más barata entre las cadenas verificadas."""
    if not ofertas:
        raise ValueError("Se requiere al menos una oferta de supermercado.")
    return min(ofertas, key=lambda oferta: oferta.monto)


class SerpApiBuscadorSupermercados(BuscadorSupermercados):
    """Buscador de supermercados basado en SerpApi (Google Shopping).

    Para integrar otro proveedor basta con crear otra subclase de
    ``BuscadorSupermercados`` y reutilizar los DTOs y el parseo de precios.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        session: requests.Session | None = None,
        timeout: float = 15.0,
        pais: str = "pe",
        idioma: str = "es",
        moneda: str = "PEN",
        motor: str = "google_shopping",
        url_base: str = _URL_SERPAPI,
    ) -> None:
        if timeout <= 0:
            raise ValueError("El timeout debe ser mayor que cero.")
        if not url_base.strip():
            raise ValueError("La URL base del buscador es obligatoria.")

        clave = api_key if api_key is not None else os.environ.get("SERPAPI_API_KEY", "")
        self._api_key = clave.strip()
        self._session = session or requests.Session()
        self._session.headers.update({"User-Agent": _AGENTE_USUARIO})
        self._timeout = timeout
        self._pais = pais
        self._idioma = idioma
        self._moneda = normalizar_moneda(moneda)
        self._motor = motor
        self._url_base = url_base.strip()

    def buscar(
        self,
        consulta: str,
        *,
        limite: int = 20,
    ) -> list[OfertaSupermercado]:
        """Consulta SerpApi y normaliza los resultados.

        Raises:
            ValueError: si la consulta está vacía o ``limite`` no es positivo.
            ConfiguracionFaltanteError: si no hay ``SERPAPI_API_KEY``.
            ErrorDeBusquedaMercado: si la petición o la respuesta fallan.
        """
        consulta_limpia = texto_opcional(consulta)
        if consulta_limpia is None:
            raise ValueError("La consulta de búsqueda no puede estar vacía.")
        if limite <= 0:
            return []
        if not self._api_key:
            raise ConfiguracionFaltanteError(
                "Falta la clave de SerpApi. Defina SERPAPI_API_KEY o pase api_key."
            )

        parametros: dict[str, str] = {
            "engine": self._motor,
            "q": consulta_limpia,
            "api_key": self._api_key,
            "gl": self._pais,
            "hl": self._idioma,
            "currency": self._moneda,
        }

        try:
            respuesta = self._session.get(
                self._url_base,
                params=parametros,
                timeout=self._timeout,
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
        except requests.RequestException as exc:
            raise ErrorDeBusquedaMercado(
                f"No se pudo consultar el buscador de supermercados: {exc}"
            ) from exc
        except ValueError as exc:
            raise ErrorDeBusquedaMercado(
                "El buscador devolvió una respuesta que no es JSON válido."
            ) from exc

        if not isinstance(datos, dict):
            raise ErrorDeBusquedaMercado(
                "El buscador devolvió una respuesta con un formato inesperado."
            )

        resultados = datos.get("shopping_results") or datos.get("organic_results") or []
        if not isinstance(resultados, list):
            raise ErrorDeBusquedaMercado(
                "El buscador devolvió resultados con un formato inesperado."
            )

        ofertas: list[OfertaSupermercado] = []
        for resultado in resultados:
            if not isinstance(resultado, dict):
                continue
            oferta = self._parsear_item(cast(Mapping[str, object], resultado))
            if oferta is None:
                continue
            ofertas.append(oferta)
            if len(ofertas) >= limite:
                break
        return ofertas

    def buscar_ofertas_cadenas_verificadas(
        self,
        consulta: str,
        *,
        limite: int = 60,
    ) -> list[OfertaSupermercado]:
        """Conserva únicamente ofertas con enlace directo a las cuatro cadenas.

        SerpApi actúa como buscador de páginas; el precio se acepta solo cuando
        la moneda es DOP y el enlace de producto pertenece a uno de los dominios
        comerciales permitidos.
        """
        dominios = " OR ".join(f"site:{dominio}" for dominio in _CADENAS_DOMINIOS.values())
        ofertas = self.buscar(f"{consulta} ({dominios})", limite=limite)
        mejores: dict[str, OfertaSupermercado] = {}
        for oferta in ofertas:
            if oferta.moneda != "DOP" or not oferta.url:
                continue
            host = urlparse(oferta.url).hostname or ""
            cadena = next(
                (
                    nombre
                    for nombre, dominio in _CADENAS_DOMINIOS.items()
                    if host == dominio or host.endswith(f".{dominio}")
                ),
                None,
            )
            if cadena is None:
                continue
            oferta_verificada = OfertaSupermercado(
                producto=oferta.producto,
                establecimiento=cadena,
                monto=oferta.monto,
                moneda=oferta.moneda,
                url=oferta.url,
                fuente=oferta.fuente,
            )
            existente = mejores.get(cadena)
            if existente is None or oferta_verificada.monto < existente.monto:
                mejores[cadena] = oferta_verificada
        return sorted(mejores.values(), key=lambda oferta: (oferta.monto, oferta.establecimiento))

    def _parsear_item(
        self,
        item: Mapping[str, object],
    ) -> OfertaSupermercado | None:
        producto = texto_opcional(item.get("title")) or texto_opcional(item.get("name"))
        if producto is None:
            return None

        monto = precio_desde_numero(item.get("extracted_price"))
        if monto is None:
            monto = precio_desde_numero(item.get("price"))
        if monto is None or monto <= Decimal("0"):
            return None

        establecimiento = (
            texto_opcional(item.get("source"))
            or texto_opcional(item.get("merchant"))
            or texto_opcional(item.get("seller"))
            or "No identificado"
        )
        moneda = normalizar_moneda(
            texto_opcional(item.get("currency")),
            por_defecto=self._moneda,
        )
        url = texto_opcional(item.get("link")) or texto_opcional(
            item.get("product_link")
        )

        return OfertaSupermercado(
            producto=producto,
            establecimiento=establecimiento,
            monto=monto,
            moneda=moneda,
            url=url,
            fuente="serpapi",
        )


class BuscadorPlazaLama(BuscadorSupermercados):
    """Scraper del buscador público de Plaza Lama.

    Consulta ``https://plazalama.com.do/search?name={consulta}`` con
    ``requests`` y extrae nombre, precio y enlace directo de cada producto con
    ``BeautifulSoup``. Plaza Lama sirve los resultados desde el buscador de su
    tienda Next.js, por lo que primero se lee el payload serializado del HTML y,
    como respaldo, se recorren las tarjetas de producto renderizadas.
    """

    _PATRON_PRODUCTO_FLIGHT: Final[re.Pattern[str]] = re.compile(
        r'"name":"((?:[^"\\]|\\.)*)","price":(-?\d+(?:\.\d+)?)'
        r'[^{}]*?"slug":"((?:[^"\\]|\\.)*)"'
    )
    _SELECTORES_TARJETA: Final[tuple[str, ...]] = (
        "[data-testid$='-productCard']",
        "[data-testid*='productCard']",
        "div.card-product-vertical",
        "div.card-product",
        "article.product",
        "li.product-item",
        "div.product-item",
        "div[class*='product-card']",
        "div[class*='productCard']",
        "div[class*='ProductCard']",
    )

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout: float = 15.0,
        url_busqueda: str = _URL_PLAZALAMA,
    ) -> None:
        if timeout <= 0:
            raise ValueError("El timeout debe ser mayor que cero.")
        if not url_busqueda.strip():
            raise ValueError("La URL de búsqueda de Plaza Lama es obligatoria.")
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "User-Agent": _AGENTE_USUARIO_NAVEGADOR,
                "Accept-Language": "es-DO,es;q=0.9,en;q=0.7",
            }
        )
        self._timeout = timeout
        self._url_busqueda = url_busqueda.strip()

    def buscar(
        self,
        consulta: str,
        *,
        limite: int = 20,
    ) -> list[OfertaSupermercado]:
        """Devuelve los productos de Plaza Lama para ``consulta``.

        Raises:
            ValueError: si la consulta está vacía.
            ErrorDeBusquedaMercado: si la petición HTTP falla.
        """
        consulta_limpia = texto_opcional(consulta)
        if consulta_limpia is None:
            raise ValueError("La consulta de búsqueda no puede estar vacía.")
        if limite <= 0:
            return []

        separador = "&" if "?" in self._url_busqueda else "?"
        url = f"{self._url_busqueda}{separador}name={quote_plus(consulta_limpia)}"
        try:
            respuesta = self._session.get(url, timeout=self._timeout)
            respuesta.raise_for_status()
        except requests.RequestException as exc:
            raise ErrorDeBusquedaMercado(
                f"No se pudo consultar el buscador de Plaza Lama: {exc}"
            ) from exc

        ofertas = self._extraer_ofertas(respuesta.text)
        return ofertas[:limite]

    def close(self) -> None:
        """Cierra la sesión HTTP usada por el buscador."""
        cerrar = getattr(self._session, "close", None)
        if callable(cerrar):
            cerrar()

    def _extraer_ofertas(self, html: str) -> list[OfertaSupermercado]:
        sopa = BeautifulSoup(html, "html.parser")
        ofertas = self._extraer_del_payload(sopa)
        if not ofertas:
            ofertas = self._extraer_de_tarjetas(sopa)
        return self._deduplicar(ofertas)

    def _extraer_del_payload(self, sopa: BeautifulSoup) -> list[OfertaSupermercado]:
        """Lee los productos serializados en los scripts de Next.js."""
        fragmentos: list[str] = []
        for script in sopa.find_all("script"):
            contenido = script.string or script.get_text()
            if not contenido or "__next_f" not in contenido:
                continue
            for coincidencia in re.finditer(
                r'self\.__next_f\.push\(\[[^,]*,\s*("(?:[^"\\]|\\.)*")\]\)',
                contenido,
                re.DOTALL,
            ):
                try:
                    carga = json.loads(coincidencia.group(1))
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(carga, str):
                    fragmentos.append(carga)
        payload = "\n".join(fragmentos)
        if not payload:
            return []

        ofertas: list[OfertaSupermercado] = []
        for coincidencia in self._PATRON_PRODUCTO_FLIGHT.finditer(payload):
            nombre = self._desescapar(coincidencia.group(1))
            monto = precio_desde_numero(coincidencia.group(2))
            slug = self._desescapar(coincidencia.group(3)).strip("/")
            if not nombre or monto is None or monto <= Decimal("0") or not slug:
                continue
            ofertas.append(
                OfertaSupermercado(
                    producto=nombre,
                    establecimiento="Plaza Lama",
                    monto=monto,
                    moneda="DOP",
                    url=f"https://plazalama.com.do/{slug}",
                    fuente="catalogo_directo",
                )
            )
        return ofertas

    def _extraer_de_tarjetas(self, sopa: BeautifulSoup) -> list[OfertaSupermercado]:
        """Respaldo para variantes del HTML que sí renderizan las tarjetas."""
        ofertas: list[OfertaSupermercado] = []
        vistos: set[int] = set()
        for selector in self._SELECTORES_TARJETA:
            for tarjeta in sopa.select(selector):
                if id(tarjeta) in vistos:
                    continue
                vistos.add(id(tarjeta))
                enlace = tarjeta.select_one("a[href]")
                if enlace is None:
                    continue
                nombre = self._nombre_de_tarjeta(tarjeta, enlace)
                monto = self._precio_de_tarjeta(tarjeta)
                href = texto_opcional(enlace.get("href"))
                if not nombre or monto is None or monto <= Decimal("0") or not href:
                    continue
                ofertas.append(
                    OfertaSupermercado(
                        producto=nombre,
                        establecimiento="Plaza Lama",
                        monto=monto,
                        moneda="DOP",
                        url=urljoin("https://plazalama.com.do/", href),
                        fuente="catalogo_directo",
                    )
                )
        return ofertas

    @classmethod
    def _nombre_de_tarjeta(cls, tarjeta: Tag, enlace: Tag) -> str | None:
        for selector in (
            "[itemprop='name']",
            "h1",
            "h2",
            "h3",
            "h4",
            "[class*='name']",
            "[class*='Name']",
            "[class*='title']",
            "[class*='Title']",
        ):
            nodo = tarjeta.select_one(selector)
            if nodo is not None:
                nombre = texto_opcional(nodo.get_text(" ", strip=True))
                if nombre:
                    return nombre
        nombre = texto_opcional(enlace.get_text(" ", strip=True))
        if nombre:
            return nombre
        imagen = tarjeta.select_one("img[alt]")
        return texto_opcional(imagen.get("alt")) if imagen is not None else None

    @classmethod
    def _precio_de_tarjeta(cls, tarjeta: Tag) -> Decimal | None:
        for selector in (
            "[itemprop='price']",
            "[data-price-type]",
            "[class*='price']",
            "[class*='Price']",
        ):
            for nodo in tarjeta.select(selector):
                texto = nodo.get("content") or nodo.get_text(" ", strip=True)
                monto = cls._monto_desde_texto(str(texto))
                if monto is not None:
                    return monto
        texto = tarjeta.get_text(" ", strip=True)
        coincidencia = re.search(r"(?:RD\$|US\$|\$)\s*\d[\d.,]*", texto)
        return cls._monto_desde_texto(coincidencia.group(0)) if coincidencia else None

    @staticmethod
    def _monto_desde_texto(texto: str | None) -> Decimal | None:
        """Convierte un precio con ``$``/``RD$`` en ``Decimal`` en DOP."""
        limpio = texto_opcional(texto)
        if limpio is None:
            return None
        limpio = re.sub(r"(?:RD|US)\$|\$", " ", limpio, flags=re.IGNORECASE)
        monto, _ = parsear_precio(limpio, moneda_por_defecto="DOP")
        return monto if monto is not None and monto > Decimal("0") else None

    @staticmethod
    def _desescapar(texto: str) -> str:
        try:
            valor = json.loads(f'"{texto}"')
        except (json.JSONDecodeError, TypeError):
            valor = texto
        return (texto_opcional(valor) or "") if isinstance(valor, str) else ""

    @staticmethod
    def _deduplicar(ofertas: list[OfertaSupermercado]) -> list[OfertaSupermercado]:
        unicas: dict[str, OfertaSupermercado] = {}
        for oferta in ofertas:
            clave = oferta.url or f"{oferta.producto}|{oferta.monto}"
            unicas.setdefault(clave, oferta)
        return list(unicas.values())


class CatalogoDirectoSupermercados:
    """Consulta los catálogos públicos de las cuatro cadenas sin API de pago.

    Nacional y Jumbo exponen resultados Magento; Sirena expone el catálogo
    público VTEX y Plaza Lama publica los resultados en su buscador Next.js. Se
    aceptan solo coincidencias de nombre y presentación verificables en el
    contenido oficial.
    """

    _URLS: Final[dict[str, str]] = {
        "Nacional": "https://supermercadosnacional.com/catalogsearch/result/",
        "La Sirena": "https://nuevo.sirena.do/api/catalog_system/pub/products/search",
        "Jumbo": "https://jumbo.com.do/catalogsearch/result/",
        "Plaza Lama": _URL_PLAZALAMA,
    }
    _UNIDADES: Final[dict[str, tuple[str, Decimal]]] = {
        "g": ("masa", Decimal("1")), "gr": ("masa", Decimal("1")),
        "gramo": ("masa", Decimal("1")), "gramos": ("masa", Decimal("1")),
        "kg": ("masa", Decimal("1000")), "kilo": ("masa", Decimal("1000")),
        "kilos": ("masa", Decimal("1000")), "kilogramo": ("masa", Decimal("1000")),
        "kilogramos": ("masa", Decimal("1000")),
        "lb": ("masa", _LIBRA_G), "lbs": ("masa", _LIBRA_G),
        "libra": ("masa", _LIBRA_G), "libras": ("masa", _LIBRA_G),
        "oz": ("masa", _ONZA_G), "onz": ("masa", _ONZA_G),
        "onza": ("masa", _ONZA_G), "onzas": ("masa", _ONZA_G),
        "ml": ("volumen", Decimal("1")), "cc": ("volumen", Decimal("1")),
        "mililitro": ("volumen", Decimal("1")), "mililitros": ("volumen", Decimal("1")),
        "l": ("volumen", Decimal("1000")), "lt": ("volumen", Decimal("1000")),
        "litro": ("volumen", Decimal("1000")), "litros": ("volumen", Decimal("1000")),
        "gal": ("volumen", _GALON_ML), "galon": ("volumen", _GALON_ML),
        "galones": ("volumen", _GALON_ML),
        "oz fl": ("volumen", _ONZA_FLUIDA_ML),
        "ozfl": ("volumen", _ONZA_FLUIDA_ML),
        "fl oz": ("volumen", _ONZA_FLUIDA_ML),
        "onza fluida": ("volumen", _ONZA_FLUIDA_ML),
        "onzas fluidas": ("volumen", _ONZA_FLUIDA_ML),
    }
    _PATRON_UNIDADES: Final[str] = "|".join(
        re.escape(unidad)
        for unidad in sorted(_UNIDADES, key=len, reverse=True)
    )
    _PARADA: Final[frozenset[str]] = frozenset({
        "de", "del", "la", "el", "y", "con", "para", "calidad", "tipo",
        "sobre", "fundas", "funda", "lata", "latas", "caja", "cajas", "caj",
        "cajita", "cajitas", "paq", "pq", "paquete", "paquetes",
        "fardo", "fardos", "faldo", "faldos", "bulto", "bultos", "saco", "sacos",
        "bolsa", "bolsas", "display", "six", "pack",
        "unidad", "unidades", "und", "uds",
        "pie", "piezas", "lb", "lbs", "libra", "libras", "oz", "onza",
        "onzas", "onz", "g", "gr", "gramo", "gramos", "kg", "ml", "cc", "l", "lt",
        "litro", "litros", "gal", "galon", "galones", "fl", "fluida", "fluidas",
        "x", "un", "las", "los",
    })
    _MODIFICADORES_CONFLICTO: Final[frozenset[str]] = frozenset({
        "molida", "polvo", "instantaneo", "instantanea", "condensada",
        "evaporada", "coco", "blanca", "negra", "morena", "rosada",
        "organica", "deslactosada", "vegetal", "liquida", "integral",
        "harina", "fideo", "fideos", "pasta", "crema", "cereal", "pastel",
        "ambientador", "proteina", "saborizada", "mezcla", "caldo", "sopa",
        "bebida", "jugo", "primavera", "maiz", "adobo", "aromatizada",
    })

    def __init__(
        self,
        *,
        timeout: float = 12.0,
        cache_ttl_segundos: float = 300.0,
        cliente: httpx.Client | None = None,
        buscador_plaza_lama: BuscadorPlazaLama | None = None,
    ) -> None:
        if timeout <= 0 or cache_ttl_segundos <= 0:
            raise ValueError("El timeout y el TTL de catálogos deben ser positivos.")
        self._timeout = timeout
        self._ttl = cache_ttl_segundos
        self._plaza_lama = buscador_plaza_lama or BuscadorPlazaLama(timeout=timeout)
        self._cliente = cliente or httpx.Client(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
                ),
                "Accept-Language": "es-DO,es;q=0.9,en;q=0.7",
            },
        )
        self._cache: dict[tuple[str, str], tuple[float, list[OfertaSupermercado]]] = {}
        self._lock = Lock()
        self._solicitudes_por_host: dict[str, float] = {}

    @staticmethod
    def _normalizar(texto: str) -> str:
        # Pre-procesar "1/2" a "0.5" ANTES de quitar la barra y la puntuación
        texto = texto.replace("1/2", "0.5")
        descompuesto = unicodedata.normalize("NFD", texto.casefold())
        sin_tildes = "".join(
            caracter for caracter in descompuesto
            if unicodedata.category(caracter) != "Mn"
        )
        return " ".join(re.findall(r"[a-z]+|\d+(?:[.,]\d+)?", sin_tildes))

    @classmethod
    def _tokens_producto(cls, texto: str) -> set[str]:
        tokens: set[str] = set()
        for token in cls._normalizar(texto).split():
            if token in cls._PARADA or token.replace(".", "", 1).replace(",", "", 1).isdigit():
                continue
            tokens.add(token[:-1] if len(token) > 4 and token.endswith("s") else token)
        return tokens

    @classmethod
    def _medidas(cls, texto: str) -> list[tuple[str, Decimal]]:
        """Normaliza peso a gramos y volumen a mililitros.

        Acepta tanto ``20 oz`` como unidades sueltas (``GALON``, ``LB``), que
        se interpretan como una unidad de esa medida.
        """
        normalizado = cls._normalizar(texto)
        expresion = re.compile(
            rf"(?<![a-z0-9])(\d+(?:[.,]\d+)?)\s*({cls._PATRON_UNIDADES})\b"
        )
        medidas: list[tuple[str, Decimal]] = []
        spans: list[tuple[int, int]] = []
        for match in expresion.finditer(normalizado):
            numero = match.group(1)
            unidad = match.group(2)
            dato = cls._UNIDADES.get(unidad)
            if dato is None:
                continue
            dimension, factor = dato
            if "aceite" in normalizado and unidad in {"oz", "onz", "onza", "onzas"}:
                # En los aceites las onzas de etiqueta suelen ser fluidas;
                # no se equiparan por masa con una libra.
                dimension, factor = "volumen", _ONZA_FLUIDA_ML
            valor = Decimal(numero.replace(",", ".")) * factor
            if (dimension, valor) not in medidas:
                medidas.append((dimension, valor))
            spans.append(match.span())

        # Unidades sueltas: ``PINOL GALON``, ``ARROZ LB``, ``LECHE LT``.
        suelta = re.compile(rf"(?<![a-z0-9])({cls._PATRON_UNIDADES})\b")
        for match in suelta.finditer(normalizado):
            if any(inicio <= match.start() and match.end() <= fin for inicio, fin in spans):
                continue
            antes = normalizado[: match.start()].rstrip()
            if antes and (antes[-1].isdigit() or antes[-1] == ","):
                continue
            unidad = match.group(1)
            dato = cls._UNIDADES.get(unidad)
            if dato is None:
                continue
            dimension, factor = dato
            if "aceite" in normalizado and unidad in {"oz", "onz", "onza", "onzas"}:
                dimension, factor = "volumen", _ONZA_FLUIDA_ML
            if (dimension, factor) not in medidas:
                medidas.append((dimension, factor))
        return medidas

    @staticmethod
    def _normalizar_empaque(texto: str) -> str:
        """Normaliza conservando la barra de ``CAJA/48`` y ``FARDO/24``."""
        texto = texto.replace("1/2", "0.5")
        descompuesto = unicodedata.normalize("NFD", texto.casefold())
        sin_tildes = "".join(
            caracter for caracter in descompuesto
            if unicodedata.category(caracter) != "Mn"
        )
        return " ".join(re.findall(r"[a-z]+|\d+(?:[.,]\d+)?|/", sin_tildes))

    @classmethod
    def _cantidad_en_pack(cls, texto: str) -> int | None:
        normalizado = cls._normalizar_empaque(texto)

        # Señales explícitas de lote: ``CAJA/48``, ``FARDO DE 24``, ``BULTO 12``,
        # ``FALDO DE 6``, ``BOLSA DE 12``, ``SIX PACK`` o una fracción ``1/2``.
        autoritativos: list[tuple[int, int, int]] = []
        for match in re.finditer(
            r"\b(?:caja|caj|cajita|faldo|fardo|bulto|paquete|paq|pq|pack|saco|"
            r"bolsa|funda|sobre|display)s?\s*(?:/\s*)?(?:de\s*)?(\d+)(?!\d)",
            normalizado,
        ):
            resto = normalizado[match.end():]
            if re.match(
                r"\s*(?:oz|onz|onzas?|ml|mililitros?|cc|l|lt|litros?|gal|galon|"
                r"galones|lbs?|libras?|kilos?|kg|gramos?|gr|g)\b",
                resto,
            ):
                # ``CAJA DE 4 OZ`` describe la presentación, no cuatro cajas.
                continue
            autoritativos.append((int(match.group(1)), match.start(1), match.end(1)))

        # ``SIX PACK`` equivale a 6 unidades si no declara otra cantidad interna.
        for match in re.finditer(r"\bsix\s*pack\b", normalizado):
            resto = normalizado[match.end():]
            if not re.match(r"\s*(?:/\s*)?(?:de\s*)?\d+", resto):
                autoritativos.append((6, match.start(), match.end()))

        for match in re.finditer(r"(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)", normalizado):
            autoritativos.append((int(match.group(1)), match.start(1), match.end(1)))

        # ``N UND`` sin palabra de empaque solo se acepta como lote cuando el
        # número es un tamaño de empaque razonable. Así una unidad suelta como
        # ``ARROZ LB 8,250 UND`` (cantidad total comprada) se compara 1 a 1 y no
        # se multiplica por 8,250.
        respaldo: list[tuple[int, int, int]] = [
            (int(match.group(1)), match.start(1), match.end(1))
            for match in re.finditer(
                r"(?<!\d)(\d+)\s*(?:und|uds|unidades|unidad|piezas|paq|paquetes)\b",
                normalizado,
            )
        ]
        matches = autoritativos or [
            match for match in respaldo if 1 < match[0] <= 100
        ]

        conteos: list[int] = []
        spans: list[tuple[int, int]] = []
        for cantidad, inicio, fin in sorted(matches, key=lambda item: item[1]):
            if any(
                cantidad == previo and abs(inicio - otro_inicio) <= 8
                for previo, (otro_inicio, _) in zip(conteos, spans)
            ):
                continue
            conteos.append(cantidad)
            spans.append((inicio, fin))
        if not conteos:
            return None
        total = 1
        for cantidad in conteos:
            total *= cantidad
        return total

    @staticmethod
    def _formatear_medida(dimension: str, valor: Decimal) -> str:
        """Presenta una medida interna en la unidad más natural."""
        if dimension == "masa":
            if valor >= Decimal("1000"):
                return f"{valor / Decimal('1000'):.2f}".rstrip("0").rstrip(".") + " kg"
            return f"{valor:.2f}".rstrip("0").rstrip(".") + " g"
        if valor >= Decimal("1000"):
            return f"{valor / Decimal('1000'):.2f}".rstrip("0").rstrip(".") + " L"
        return f"{valor:.2f}".rstrip("0").rstrip(".") + " mL"

    @staticmethod
    def _es_unidad_suelta(unidad: str) -> bool:
        return unidad in {
            "unidad", "unidades", "ud", "uds", "un", "pieza", "piezas",
            "c u", "c/u", "cada",
        }

    @staticmethod
    def _categoria_prohibida_al_inicio(
        normalizado_catalogo: str,
        tokens_requeridos: set[str],
    ) -> bool:
        """Aplica la regla general de prefijos de producto procesado."""
        partes = normalizado_catalogo.split()
        if not partes:
            return False
        primero = partes[0]
        singular = primero[:-1] if len(primero) > 4 and primero.endswith("s") else primero
        if singular in {"chicle", "cupcake", "galleta", "jugo", "refresco", "adobo"}:
            return singular not in tokens_requeridos
        if normalizado_catalogo.startswith(("sabor a ", "con sabor ")):
            return not ({"sabor", "saborizado"} & tokens_requeridos)
        return False

    @classmethod
    def _producto_compatible(cls, nombre_requerido: str, nombre_catalogo: str) -> bool:
        """Verifica que el núcleo sustantivo y la categoría sean compatibles."""
        
        # Validación de Falsos Positivos Severos
        nombre_req_baja = nombre_requerido.lower()
        nombre_cat_baja = nombre_catalogo.lower()
        
        # Si el producto requerido NO tiene ninguna de estas palabras procesadas/carnes
        if not any(p in nombre_req_baja for p in _PALABRAS_PROHIBIDAS):
            # Y el catálogo SÍ las tiene, se descarta el producto inmediatamente.
            if any(p in nombre_cat_baja for p in _PALABRAS_PROHIBIDAS):
                return False
                
        # Validación Institucional de Volumen (Para evitar Galones vs Onzas Pequeñas)
        es_institucional_licitado = any(palabra in nombre_req_baja for palabra in ["galon", "galones", "saco", "cubeta", "lata grande", "tanque", "caja/4", "caj/4"])
        es_pequeno_mercado = any(palabra in nombre_cat_baja for palabra in [" oz", "onz", " gr ", " ml ", "gramo", "gramos"])
        if es_institucional_licitado and es_pequeno_mercado:
            return False

        tokens = cls._tokens_producto(nombre_requerido)
        if not tokens:
            return False
        tokens_catalogo = cls._tokens_producto(nombre_catalogo)
        normalizado_catalogo = cls._normalizar(nombre_catalogo)

        if cls._categoria_prohibida_al_inicio(normalizado_catalogo, tokens):
            return False

        # SANDIA (fruta) no puede sustituirse por dulces, chicles o bebidas.
        if "sandia" in tokens and tokens_catalogo & {
            "chicle", "goma", "mascar", "trident", "jugo", "bebida",
            "refresco", "gelatina", "caramelo", "dulce",
        }:
            return False

        # PASAS / UVAS PASAS deben ser pasas reales, no repostería o cereales.
        if "pasa" in tokens and tokens_catalogo & {
            "cupcake", "ponque", "bizcocho", "pan", "galleta", "avena",
            "cereal", "helado",
        }:
            return False

        # APIO en rama no es CEPA DE APIO; CELERY es un sinónimo válido.
        if "apio" in tokens:
            if "cepa" in tokens_catalogo or "cepa de apio" in normalizado_catalogo:
                return False
            if "celery" in tokens_catalogo:
                tokens_catalogo.add("apio")

        # PALO DE ESCOBA no es ESCOBA CON PALO (producto terminado).
        if "palo" in tokens and "escoba" in tokens:
            if (
                normalizado_catalogo.startswith("escoba")
                or "escoba con palo" in normalizado_catalogo
            ):
                return False
            if "escoba" in tokens_catalogo and "palo" not in tokens_catalogo:
                return False

        # Coincidencia exacta de producto: un adobo, sal o sazón no sustituye
        # una pimienta; una harina de maíz no sustituye una harina blanca.
        if "pimienta" in tokens and not ({"adobo", "sal", "sazon"} & tokens):
            if tokens_catalogo & {"adobo", "sal", "sazon"}:
                return False
        if "harina" in tokens and "blanca" in tokens:
            if "maiz" in tokens_catalogo or "pan" in tokens_catalogo:
                return False

        tokens_requeridos = tokens
        if "harina" in tokens and "blanca" in tokens and "trigo" in tokens_catalogo:
            # "Harina blanca" es harina de trigo; el catálogo puede omitir el
            # adjetivo y publicarla simplemente como harina de trigo.
            tokens_requeridos = tokens - {"blanca"}
        if not tokens_requeridos.issubset(tokens_catalogo):
            return False
        if any(
            modificador in tokens_catalogo and modificador not in tokens
            for modificador in cls._MODIFICADORES_CONFLICTO
        ):
            return False
        return True

    @staticmethod
    def _es_liquido(nombre: str) -> bool:
        return bool(
            CatalogoDirectoSupermercados._tokens_producto(nombre)
            & {
                "aceite", "pinol", "vainilla", "extracto", "leche", "jugo",
                "bebida", "refresco", "agua", "vinagre", "salsa", "cloro",
                "detergente", "limpiador", "shampoo", "acondicionador",
                "alcohol", "lotion", "locion", "gel",
            }
        )

    @classmethod
    def _ratio_permitido(
        cls,
        ratio: Decimal,
        dimension: str,
        nombre_requerido: str,
        unidades_lote: int,
    ) -> bool:
        if ratio <= 0:
            return False
        if _ESCALA_MINIMA <= ratio <= _ESCALA_MAXIMA:
            return True
        # Excepción documentada para PINOL: un galón contra 828 ml es 4.57x.
        # Solo aplica a una unidad líquida suelta, nunca a una caja de 4 galones.
        return (
            dimension == "volumen"
            and unidades_lote == 1
            and _ESCALA_MINIMA <= ratio <= _ESCALA_MAXIMA_LIQUIDOS
            and cls._es_liquido(nombre_requerido)
        )

    @classmethod
    def _tolerancia_equivalencia(
        cls,
        nombre: str,
        dimension: str,
        valor_requerido: Decimal,
    ) -> Decimal:
        if (
            dimension == "masa"
            and "canela" in cls._tokens_producto(nombre)
            and abs(valor_requerido - Decimal("56.69904625")) < Decimal("0.01")
        ):
            # La ficha local trata el sobre de canela 2 oz y el catálogo
            # presenta ese mismo sobre en 60 g.
            return Decimal("0.07")
        return Decimal("0.03")

    @staticmethod
    def _medida_comparable(
        medidas_requeridas: list[tuple[str, Decimal]],
        medidas_catalogo: list[tuple[str, Decimal]],
    ) -> tuple[str, Decimal, Decimal] | None:
        for dimension, valor_requerido in medidas_requeridas:
            comparables = [
                valor for otra_dimension, valor in medidas_catalogo
                if otra_dimension == dimension and valor > 0
            ]
            if comparables:
                valor_catalogo = min(
                    comparables, key=lambda valor: abs(valor - valor_requerido)
                )
                return dimension, valor_requerido, valor_catalogo
        return None

    @staticmethod
    def _peso_aproximado_lb(nombre_catalogo: str) -> Decimal | None:
        normalizado = CatalogoDirectoSupermercados._normalizar(nombre_catalogo)
        coincidencia = re.search(
            r"peso\s+aprox(?:imado)?\.?\s*(?:de\s*)?"
            r"(\d+(?:[.,]\d+)?)\s*(?:libras?|lbs?)",
            normalizado,
        )
        if coincidencia is None:
            return None
        return Decimal(coincidencia.group(1).replace(",", "."))

    @classmethod
    def _precio_unidad_agricola(
        cls,
        nombre_requerido: str,
        nombre_catalogo: str,
        medidas_catalogo: list[tuple[str, Decimal]],
        precio_unitario_catalogo: Decimal,
    ) -> tuple[Decimal, str] | None:
        """Escenario C: convierte un precio por libra al precio por unidad."""
        masas = [
            valor for dimension, valor in medidas_catalogo
            if dimension == "masa" and valor > 0
        ]
        if not masas:
            return None
        libra = next(
            (valor for valor in masas if abs(valor - _LIBRA_G) < Decimal("1")),
            None,
        )
        aproximado = cls._peso_aproximado_lb(nombre_catalogo)
        tokens = cls._tokens_producto(nombre_requerido)
        promedio = next(
            (peso for producto, peso in _PESO_PROMEDIO_LB.items() if producto in tokens),
            None,
        )
        if aproximado is not None:
            peso_unidad = aproximado * _LIBRA_G
            base = libra if libra is not None else peso_unidad
        elif promedio is not None:
            peso_unidad = promedio * _LIBRA_G
            if libra is not None:
                base = libra
            else:
                base = min(masas)
                if base > Decimal("680"):
                    # El catálogo ya vende el ejemplar completo; no se reescala.
                    return (
                        precio_unitario_catalogo,
                        f"Unidad suelta comparada 1 a 1; presentación de "
                        f"{cls._formatear_medida('masa', base)}",
                    )
        else:
            return None
        factor = peso_unidad / base
        # Si el catálogo vende por libra, multiplicar por el peso estándar del
        # ejemplar (Sandía 10 lb) es una conversión por unidad, no un escalado
        # de presentación: no se limita a 4x. Cuando el catálogo trae un
        # empaque medido distinto, sí se exige la proporción comercial.
        if libra is None and not cls._ratio_permitido(
            factor, "masa", nombre_requerido, 1
        ):
            return None
        precio = precio_unitario_catalogo * factor
        libras = peso_unidad / _LIBRA_G
        return (
            precio,
            f"Precio por libra ajustado a unidad: {libras:.2f} lb "
            f"(peso aprox.) × RD$ {precio_unitario_catalogo:.2f} = "
            f"RD$ {precio:.2f}",
        )

    @classmethod
    def _evaluar_presentacion(
        cls,
        articulo: Mapping[str, object],
        oferta: OfertaSupermercado,
    ) -> tuple[Decimal | None, str]:
        """Aplica los escenarios A, B y C y devuelve precio y explicación."""
        nombre = str(
            articulo.get("descripcion_usuario")
            or articulo.get("descripcion_articulo")
            or ""
        )
        if not cls._producto_compatible(nombre, oferta.producto):
            return None, ""

        unidad = cls._normalizar(str(articulo.get("unidad_medida") or "Unidad"))
        unidades_lote = cls._cantidad_en_pack(nombre) or 1
        unidades_catalogo = cls._cantidad_en_pack(oferta.producto) or 1
        medidas_requeridas = cls._medidas(nombre)
        medidas_catalogo = cls._medidas(oferta.producto)
        precio_unitario = oferta.monto / Decimal(unidades_catalogo)

        # Renglón medido por libra: el catálogo se normaliza a esa unidad.
        if unidad in {"libra", "libras", "lb", "lbs"}:
            masas = [
                valor for dimension, valor in medidas_catalogo
                if dimension == "masa" and valor > 0
            ]
            if not masas:
                return None, ""
            base = min(masas)
            precio_libra = precio_unitario / (base / _LIBRA_G)
            return (
                precio_libra,
                f"Comparación por libra: presentación de "
                f"{cls._formatear_medida('masa', base)} "
                f"({base / _LIBRA_G:.2f} lb); precio normalizado a 1 lb",
            )

        # Escenario C: renglón por UNIDAD y catálogo por libra.
        if cls._es_unidad_suelta(unidad) and not medidas_requeridas and medidas_catalogo:
            agricola = cls._precio_unidad_agricola(
                nombre, oferta.producto, medidas_catalogo, precio_unitario
            )
            if agricola is not None:
                precio, descripcion = agricola
                if unidades_lote > 1:
                    return (
                        precio * Decimal(unidades_lote),
                        f"Lote de {unidades_lote} unidades; {descripcion}; "
                        f"total lote vs. total lote",
                    )
                return precio, descripcion
            # Sin peso agrícola conocido: se asume que el empaque del catálogo
            # es la unidad solicitada (comparación 1 a 1 del paquete).
            if unidades_lote > 1:
                detalle = (
                    f"catálogo en pack de {unidades_catalogo} unidades; "
                    if unidades_catalogo > 1
                    else ""
                )
                return (
                    precio_unitario * Decimal(unidades_lote),
                    f"Lote de {unidades_lote} unidades; {detalle}"
                    f"precio unitario ×{unidades_lote} "
                    f"(total lote vs. total lote)",
                )
            if unidades_catalogo > 1:
                return (
                    precio_unitario,
                    f"Unidad suelta comparada 1 a 1; catálogo en pack de "
                    f"{unidades_catalogo} unidades, precio unitario",
                )
            return (
                precio_unitario,
                f"Unidad suelta comparada 1 a 1 ({unidad or 'Unidad'})",
            )

        # Escenarios A y B: proporción de tamaño/peso/volumen y empaques.
        if medidas_requeridas:
            comparable = cls._medida_comparable(medidas_requeridas, medidas_catalogo)
            if comparable is None:
                return None, ""
            dimension, requerido, catalogo = comparable
            ratio = requerido / catalogo
            tolerancia = cls._tolerancia_equivalencia(nombre, dimension, requerido)
            if abs(ratio - 1) <= tolerancia:
                descripcion = (
                    f"Unidad suelta comparada 1 a 1; presentación equivalente "
                    f"{cls._formatear_medida(dimension, requerido)} ≈ "
                    f"{cls._formatear_medida(dimension, catalogo)}"
                )
                if unidades_lote > 1:
                    return (
                        precio_unitario * Decimal(unidades_lote),
                        f"Lote de {unidades_lote} unidades; {descripcion}; "
                        f"total lote vs. total lote",
                    )
                return precio_unitario, descripcion
            if not cls._ratio_permitido(
                ratio, dimension, nombre, unidades_lote
            ):
                return None, ""
            ajustado = precio_unitario * ratio
            descripcion = (
                f"Presentación ajustada: "
                f"{cls._formatear_medida(dimension, requerido)} solicitado vs "
                f"{cls._formatear_medida(dimension, catalogo)} catálogo "
                f"(factor {ratio:.2f}); precio ajustado RD$ {ajustado:.2f}"
            )
            if unidades_lote > 1:
                return (
                    ajustado * Decimal(unidades_lote),
                    f"Lote de {unidades_lote} unidades; {descripcion}; "
                    f"total lote vs. total lote",
                )
            return ajustado, descripcion

        # Sin medida en el renglón: se respeta el empaque del catálogo.
        if unidades_lote > 1:
            detalle = (
                f"catálogo en pack de {unidades_catalogo} unidades; "
                if unidades_catalogo > 1
                else ""
            )
            return (
                precio_unitario * Decimal(unidades_lote),
                f"Lote de {unidades_lote} unidades; {detalle}"
                f"precio unitario ×{unidades_lote} (total lote vs. total lote)",
            )
        if unidades_catalogo > 1:
            return (
                precio_unitario,
                f"Unidad suelta comparada 1 a 1; catálogo en pack de "
                f"{unidades_catalogo} unidades, precio unitario",
            )
        return (
            precio_unitario,
            f"Unidad suelta comparada 1 a 1 ({unidad or 'Unidad'})",
        )

    @classmethod
    def describir_equivalencia(
        cls,
        articulo: Mapping[str, object],
        oferta: OfertaSupermercado,
    ) -> str:
        """Explica en lenguaje ciudadano cómo se normalizó la comparación."""
        _, descripcion = cls._evaluar_presentacion(articulo, oferta)
        return descripcion or "Unidad suelta comparada 1 a 1"

    @classmethod
    def _precio_equivalente(
        cls,
        articulo: Mapping[str, object],
        oferta: OfertaSupermercado,
    ) -> Decimal | None:
        """Devuelve el precio normalizado del lote solicitado o ``None``."""
        precio, _ = cls._evaluar_presentacion(articulo, oferta)
        return precio

    def buscar_para_renglon(
        self,
        articulo: Mapping[str, object],
    ) -> list[OfertaSupermercado]:
        """Busca y normaliza el precio de góndola comparable en cada cadena."""
        nombre = str(
            articulo.get("descripcion_usuario")
            or articulo.get("descripcion_articulo")
            or ""
        ).strip()
        consulta = " ".join(
            token for token in self._normalizar(nombre).split()
            if token not in self._PARADA and not token.replace(".", "", 1).isdigit()
        )
        if not consulta:
            return []

        mejores: dict[str, OfertaSupermercado] = {}
        for cadena in _CADENAS_DOMINIOS:
            for oferta in self._buscar_cadena(cadena, consulta):
                precio = self._precio_equivalente(articulo, oferta)
                if precio is None or precio <= 0:
                    continue
                verificada = OfertaSupermercado(
                    producto=oferta.producto,
                    establecimiento=cadena,
                    monto=precio,
                    moneda="DOP",
                    url=oferta.url,
                    fuente="catalogo_directo",
                    equivalencia=self.describir_equivalencia(articulo, oferta),
                )
                existente = mejores.get(cadena)
                if existente is None or verificada.monto < existente.monto:
                    mejores[cadena] = verificada
        return sorted(mejores.values(), key=lambda oferta: (oferta.monto, oferta.establecimiento))

    def buscar_ofertas_cadenas_verificadas(
        self,
        consulta: str,
        *,
        limite: int = 60,
    ) -> list[OfertaSupermercado]:
        """Busca una frase en las cadenas (API común compatible con SerpApi)."""
        if limite <= 0:
            return []
        articulo = {"descripcion_usuario": consulta, "unidad_medida": "Unidad"}
        return self.buscar_para_renglon(articulo)[:limite]

    def _buscar_cadena(self, cadena: str, consulta: str) -> list[OfertaSupermercado]:
        clave = (cadena, self._normalizar(consulta))
        ahora = monotonic()
        with self._lock:
            cacheada = self._cache.get(clave)
            if cacheada and ahora - cacheada[0] < self._ttl:
                return cacheada[1]
        try:
            if cadena == "La Sirena":
                ofertas = self._buscar_sirena(consulta)
            elif cadena == "Plaza Lama":
                ofertas = self._buscar_plaza_lama(consulta)
            else:
                ofertas = self._buscar_magento(cadena, consulta)
        except (httpx.HTTPError, ErrorDeBusquedaMercado, ValueError, TypeError):
            ofertas = []
        with self._lock:
            self._cache[clave] = (monotonic(), ofertas)
        return ofertas

    def _solicitar(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
    ) -> httpx.Response:
        host = urlparse(url).hostname or ""
        with self._lock:
            ultima = self._solicitudes_por_host.get(host, 0.0)
            espera = 0.25 - (monotonic() - ultima)
            if espera > 0:
                time.sleep(espera)
            self._solicitudes_por_host[host] = monotonic()
        respuesta = self._cliente.get(url, params=params)
        respuesta.raise_for_status()
        return respuesta

    @staticmethod
    def _monto(texto: str | None) -> Decimal | None:
        monto, _ = parsear_precio(texto, moneda_por_defecto="DOP")
        return monto if monto is not None and monto > 0 else None

    def _buscar_magento(self, cadena: str, consulta: str) -> list[OfertaSupermercado]:
        url_busqueda = self._URLS[cadena]
        respuesta = self._solicitar(url_busqueda, params={"q": consulta})
        sopa = BeautifulSoup(respuesta.text, "html.parser")
        ofertas: list[OfertaSupermercado] = []
        for producto in sopa.select("li.product-item"):
            enlace = producto.select_one("a.product-item-link")
            if enlace is None:
                continue
            nombre = texto_opcional(enlace.get_text(" ", strip=True))
            href = texto_opcional(enlace.get("href"))
            url = urljoin(url_busqueda, href) if href else None
            precio_nodo = (
                producto.select_one('[data-price-type="finalPrice"] .price')
                or producto.select_one(".price-box .price")
                or producto.select_one("span.price")
            )
            precio = self._monto(precio_nodo.get_text(" ", strip=True) if precio_nodo else None)
            if nombre and url and precio is not None:
                ofertas.append(OfertaSupermercado(nombre, cadena, precio, "DOP", url, "catalogo_directo"))
        return ofertas

    def _buscar_sirena(self, consulta: str) -> list[OfertaSupermercado]:
        respuesta = self._solicitar(
            self._URLS["La Sirena"],
            params={"ft": consulta, "_from": 0, "_to": 49},
        )
        productos = respuesta.json()
        if not isinstance(productos, list):
            return []
        ofertas: list[OfertaSupermercado] = []
        for producto in productos:
            if not isinstance(producto, dict):
                continue
            nombre = texto_opcional(producto.get("productName"))
            link_text = texto_opcional(producto.get("linkText"))
            if not nombre or not link_text:
                continue
            url = f"https://nuevo.sirena.do/{link_text}/p"
            items = producto.get("items")
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                sellers = item.get("sellers")
                for vendedor in sellers if isinstance(sellers, list) else []:
                    if not isinstance(vendedor, dict):
                        continue
                    oferta = vendedor.get("commertialOffer")
                    if not isinstance(oferta, dict):
                        continue
                    disponibilidad = oferta.get("AvailableQuantity")
                    if isinstance(disponibilidad, (int, float)) and disponibilidad <= 0:
                        continue
                    precio = precio_desde_numero(oferta.get("Price"))
                    if precio is not None and precio > 0:
                        ofertas.append(OfertaSupermercado(nombre, "La Sirena", precio, "DOP", url, "catalogo_directo"))
        return ofertas

    def _buscar_plaza_lama(self, consulta: str) -> list[OfertaSupermercado]:
        return self._plaza_lama.buscar(consulta, limite=50)

    def close(self) -> None:
        self._plaza_lama.close()
        self._cliente.close()

    def __enter__(self) -> CatalogoDirectoSupermercados:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


__all__ = [
    "BuscadorPlazaLama",
    "BuscadorSupermercados",
    "CatalogoDirectoSupermercados",
    "OfertaSupermercado",
    "SerpApiBuscadorSupermercados",
    "seleccionar_oferta_minima",
    "_CADENAS_DOMINIOS",
]
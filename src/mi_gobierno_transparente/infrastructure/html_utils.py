"""Helpers de extracción HTML basados en BeautifulSoup."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4.element import Tag

from .parsing import texto_opcional


def texto_de_nodo(nodo: Tag, selector: str | None) -> str | None:
    """Devuelve el texto normalizado del primer nodo que coincide con el selector."""
    if not selector:
        return None
    elemento = nodo.select_one(selector)
    if elemento is None:
        return None
    return texto_opcional(elemento.get_text(" ", strip=True))


def url_de_nodo(nodo: Tag, selector: str, base_url: str) -> str | None:
    """Resuelve el ``href`` del primer enlace que coincide con el selector."""
    enlace = nodo.select_one(selector)
    if enlace is None:
        return None
    href = enlace.get("href")
    if not isinstance(href, str) or not href.strip():
        return None
    return urljoin(base_url, href.strip())

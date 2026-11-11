"""Utilidades de parseo compartidas por los adaptadores de extracción."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

_FORMATOS_FECHA = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y")


def texto_opcional(valor: object) -> str | None:
    """Normaliza un texto de scraping/JSON; devuelve ``None`` si está vacío."""
    if not isinstance(valor, str):
        return None
    limpio = " ".join(valor.split())
    return limpio or None


def parsear_precio(
    texto: str | None,
    moneda_por_defecto: str = "PEN",
) -> tuple[Decimal | None, str]:
    """Convierte un precio textual (``"S/ 1,234.50"``) en ``Decimal`` y moneda.

    Soporta separadores de miles anglosajones y europeos. Si el texto no es
    interpretable devuelve ``(None, moneda_por_defecto)``.
    """
    limpio = texto_opcional(texto)
    if limpio is None:
        return None, moneda_por_defecto

    moneda = moneda_por_defecto.upper()
    mayusculas = limpio.upper()
    if "US$" in mayusculas or "USD" in mayusculas or "$" in limpio:
        moneda = "USD"
    elif "S/" in limpio or "PEN" in mayusculas:
        moneda = "PEN"
    elif "EUR" in mayusculas or "€" in limpio:
        moneda = "EUR"

    numero = re.sub(r"[^\d.,-]", "", limpio)
    if not numero:
        return None, moneda

    if "," in numero and "." in numero:
        if numero.rfind(",") > numero.rfind("."):
            numero = numero.replace(".", "").replace(",", ".")
        else:
            numero = numero.replace(",", "")
    elif "," in numero:
        parte_decimal = numero.rsplit(",", maxsplit=1)[-1]
        numero = numero.replace(",", ".") if len(parte_decimal) == 2 else numero.replace(",", "")

    try:
        monto = Decimal(numero)
    except InvalidOperation:
        return None, moneda

    if not monto.is_finite() or monto < Decimal("0"):
        return None, moneda
    return monto, moneda


def precio_desde_numero(valor: object) -> Decimal | None:
    """Convierte un número de JSON (``25.9``) en ``Decimal`` sin usar ``float`` puro."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        return Decimal(str(valor))
    if isinstance(valor, str):
        return parsear_precio(valor)[0]
    return None


def normalizar_moneda(texto: str | None, por_defecto: str = "PEN") -> str:
    """Convierte un símbolo o código de moneda en un código ISO 4217.

    Reconoce ``S/``, ``PEN``, ``US$``, ``USD``, ``EUR`` y ``€``. Si no puede
    interpretar el texto, devuelve ``por_defecto`` en mayúsculas.
    """
    limpio = texto_opcional(texto)
    if limpio is None:
        return por_defecto.upper()

    mayusculas = limpio.upper()
    if "US$" in mayusculas or "USD" in mayusculas or "$" in limpio:
        return "USD"
    if "S/" in limpio or "PEN" in mayusculas or "SOL" in mayusculas:
        return "PEN"
    if "EUR" in mayusculas or "€" in limpio:
        return "EUR"
    if len(mayusculas) == 3 and mayusculas.isalpha():
        return mayusculas
    return por_defecto.upper()


def parsear_fecha(texto: str | None) -> date | None:
    """Interpreta fechas habituales de portales públicos."""
    limpio = texto_opcional(texto)
    if limpio is None:
        return None

    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(limpio, formato).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(limpio).date()
    except ValueError:
        return None

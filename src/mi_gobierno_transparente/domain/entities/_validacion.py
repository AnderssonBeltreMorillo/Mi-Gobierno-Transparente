"""Helpers internos de validación para entidades.

Evitan duplicar la misma lógica de normalización en cada entidad y permiten
que cada una lance su excepción de dominio específica.
"""

from __future__ import annotations

from datetime import date, datetime

from ..exceptions import ErrorDeDominio


def exigir_identificador(
    valor: object,
    *,
    campo: str = "id",
    error: type[ErrorDeDominio],
) -> str:
    """Valida y normaliza un identificador (sin espacios, 1 a 128 caracteres)."""
    if not isinstance(valor, str):
        raise error(f"El campo '{campo}' debe ser texto.")
    limpio = valor.strip()
    if not limpio or len(limpio) > 128 or any(caracter.isspace() for caracter in limpio):
        raise error(f"El campo '{campo}' debe ser un identificador válido.")
    return limpio


def exigir_texto(
    valor: object,
    *,
    campo: str,
    minimo: int,
    maximo: int,
    error: type[ErrorDeDominio],
) -> str:
    """Valida un texto obligatorio, colapsando espacios repetidos."""
    if not isinstance(valor, str):
        raise error(f"El campo '{campo}' debe ser texto.")
    limpio = " ".join(valor.split())
    if len(limpio) < minimo or len(limpio) > maximo:
        raise error(f"El campo '{campo}' debe tener entre {minimo} y {maximo} caracteres.")
    return limpio


def limpiar_texto_opcional(
    valor: object,
    *,
    campo: str,
    maximo: int,
    error: type[ErrorDeDominio],
) -> str | None:
    """Normaliza un texto opcional; un texto vacío se convierte en ``None``."""
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise error(f"El campo '{campo}' debe ser texto o nulo.")
    limpio = " ".join(valor.split())
    if not limpio:
        return None
    if len(limpio) > maximo:
        raise error(f"El campo '{campo}' no puede superar los {maximo} caracteres.")
    return limpio


def exigir_fecha(valor: object, *, campo: str, error: type[ErrorDeDominio]) -> date:
    """Valida una fecha sin hora (rechaza ``datetime``)."""
    if not isinstance(valor, date) or isinstance(valor, datetime):
        raise error(f"El campo '{campo}' debe ser una fecha válida.")
    return valor


def exigir_booleano(valor: object, *, campo: str, error: type[ErrorDeDominio]) -> bool:
    """Valida un booleano estricto (rechaza ``0``, ``1``, ``"true"``, etc.)."""
    if not isinstance(valor, bool):
        raise error(f"El campo '{campo}' debe ser booleano.")
    return valor

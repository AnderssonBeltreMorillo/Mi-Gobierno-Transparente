"""Unidades de medida soportadas para comparar precios homogéneos."""

from __future__ import annotations

from enum import StrEnum


class UnidadMedida(StrEnum):
    """Unidad en la que se expresa el precio de un producto."""

    UNIDAD = "unidad"
    KILOGRAMO = "kilogramo"
    GRAMO = "gramo"
    LITRO = "litro"
    MILILITRO = "mililitro"
    PAQUETE = "paquete"
    CAJA = "caja"

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS[self]

    @property
    def simbolo(self) -> str:
        return _SIMBOLOS[self]

    def __str__(self) -> str:
        return self.value


_ETIQUETAS: dict[UnidadMedida, str] = {
    UnidadMedida.UNIDAD: "Unidad",
    UnidadMedida.KILOGRAMO: "Kilogramo",
    UnidadMedida.GRAMO: "Gramo",
    UnidadMedida.LITRO: "Litro",
    UnidadMedida.MILILITRO: "Mililitro",
    UnidadMedida.PAQUETE: "Paquete",
    UnidadMedida.CAJA: "Caja",
}

_SIMBOLOS: dict[UnidadMedida, str] = {
    UnidadMedida.UNIDAD: "und",
    UnidadMedida.KILOGRAMO: "kg",
    UnidadMedida.GRAMO: "g",
    UnidadMedida.LITRO: "L",
    UnidadMedida.MILILITRO: "ml",
    UnidadMedida.PAQUETE: "paq",
    UnidadMedida.CAJA: "caja",
}

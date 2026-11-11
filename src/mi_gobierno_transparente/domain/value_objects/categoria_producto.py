"""Categorías de producto y regla de negocio asociada.

Regla: solo se procesan productos de **alimentos** y **aseo**.
"""

from __future__ import annotations

from enum import StrEnum

from ..exceptions import CategoriaNoPermitidaError


class CategoriaProducto(StrEnum):
    """Categorías reconocidas por el sistema.

    Las categorías distintas de alimentos y aseo existen para poder rechazarlas
    explícitamente y para mapear datos históricos, pero nunca se procesan.
    """

    ALIMENTOS = "alimentos"
    ASEO = "aseo"
    ELECTRONICA = "electronica"
    ROPA_Y_CALZADO = "ropa_y_calzado"
    HOGAR = "hogar"
    JUGUETES = "juguetes"
    FERRETERIA = "ferreteria"
    OTROS = "otros"

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS[self]

    def es_permitida(self) -> bool:
        """Indica si la categoría puede procesarse en el demo."""
        return self in _CATEGORIAS_PERMITIDAS

    @classmethod
    def permitidas(cls) -> frozenset[CategoriaProducto]:
        """Categorías aceptadas por el negocio."""
        return _CATEGORIAS_PERMITIDAS

    @classmethod
    def validar_permitida(cls, categoria: CategoriaProducto) -> None:
        """Lanza ``CategoriaNoPermitidaError`` si la categoría no es procesable."""
        if not isinstance(categoria, CategoriaProducto):
            raise CategoriaNoPermitidaError("La categoría debe ser un valor de CategoriaProducto.")
        if not categoria.es_permitida():
            permitidas = ", ".join(sorted(c.value for c in _CATEGORIAS_PERMITIDAS))
            raise CategoriaNoPermitidaError(
                f"La categoría '{categoria.value}' no está permitida. "
                f"Solo se procesan productos de alimentos y aseo ({permitidas})."
            )

    @classmethod
    def desde_valor(cls, valor: str) -> CategoriaProducto:
        """Convierte un texto en categoría; falla si no existe."""
        try:
            return cls(valor.strip().lower())
        except (AttributeError, ValueError) as exc:
            raise CategoriaNoPermitidaError(f"'{valor}' no es una categoría válida.") from exc

    def __str__(self) -> str:
        return self.value


_CATEGORIAS_PERMITIDAS: frozenset[CategoriaProducto] = frozenset(
    {CategoriaProducto.ALIMENTOS, CategoriaProducto.ASEO}
)

_ETIQUETAS: dict[CategoriaProducto, str] = {
    CategoriaProducto.ALIMENTOS: "Alimentos",
    CategoriaProducto.ASEO: "Aseo",
    CategoriaProducto.ELECTRONICA: "Electrónica",
    CategoriaProducto.ROPA_Y_CALZADO: "Ropa y calzado",
    CategoriaProducto.HOGAR: "Hogar",
    CategoriaProducto.JUGUETES: "Juguetes",
    CategoriaProducto.FERRETERIA: "Ferretería",
    CategoriaProducto.OTROS: "Otros",
}

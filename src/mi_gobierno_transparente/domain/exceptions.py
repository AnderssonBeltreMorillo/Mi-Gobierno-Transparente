"""Excepciones propias del dominio.

No dependen de HTTP, Firestore ni de ningún framework. La capa de aplicación
y los adaptadores de entrada se encargan de traducirlas a sus propios errores.
"""

from __future__ import annotations


class ErrorDeDominio(Exception):
    """Base para toda violación de una regla de negocio."""

    codigo: str = "error_de_dominio"

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje

    def __str__(self) -> str:
        return self.mensaje


class CategoriaNoPermitidaError(ErrorDeDominio):
    """La categoría no existe o no forma parte de las categorías procesables."""

    codigo = "categoria_no_permitida"


class PrecioInvalidoError(ErrorDeDominio):
    """Un importe o una fecha de precio no cumplen las invariantes."""

    codigo = "precio_invalido"


class MonedaIncompatibleError(ErrorDeDominio):
    """Se intentaron operar importes expresados en monedas distintas."""

    codigo = "moneda_incompatible"


class PorcentajeInvalidoError(ErrorDeDominio):
    """El porcentaje no es un valor decimal válido."""

    codigo = "porcentaje_invalido"


class UmbralesInvalidosError(ErrorDeDominio):
    """Los umbrales de evaluación son inconsistentes."""

    codigo = "umbrales_invalidos"


class ProductoInvalidoError(ErrorDeDominio):
    """El producto no cumple las invariantes de la entidad."""

    codigo = "producto_invalido"


class EvaluacionInvalidaError(ErrorDeDominio):
    """Una evaluación o su resultado son internamente inconsistentes."""

    codigo = "evaluacion_invalida"

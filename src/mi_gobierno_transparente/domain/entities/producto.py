"""Entidad Producto: solo alimentos y aseo son procesables."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..exceptions import ProductoInvalidoError
from ..value_objects.categoria_producto import CategoriaProducto
from ..value_objects.unidad_medida import UnidadMedida
from ._validacion import (
    exigir_booleano,
    exigir_identificador,
    exigir_texto,
    limpiar_texto_opcional,
)


@dataclass(frozen=True, slots=True)
class Producto:
    """Producto sujeto a seguimiento de precios.

    Es inmutable: los cambios de estado devuelven una nueva instancia, lo que
    facilita razonar sobre el histórico y evita mutaciones accidentales.
    """

    id: str
    nombre: str
    categoria: CategoriaProducto
    unidad_medida: UnidadMedida
    marca: str | None = None
    descripcion: str | None = None
    activo: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            exigir_identificador(self.id, campo="id", error=ProductoInvalidoError),
        )
        object.__setattr__(
            self,
            "nombre",
            exigir_texto(
                self.nombre,
                campo="nombre",
                minimo=2,
                maximo=120,
                error=ProductoInvalidoError,
            ),
        )
        if not isinstance(self.categoria, CategoriaProducto):
            raise ProductoInvalidoError("La categoría debe ser un valor de CategoriaProducto.")
        CategoriaProducto.validar_permitida(self.categoria)
        if not isinstance(self.unidad_medida, UnidadMedida):
            raise ProductoInvalidoError("La unidad de medida debe ser un valor de UnidadMedida.")
        object.__setattr__(
            self,
            "marca",
            limpiar_texto_opcional(
                self.marca,
                campo="marca",
                maximo=80,
                error=ProductoInvalidoError,
            ),
        )
        object.__setattr__(
            self,
            "descripcion",
            limpiar_texto_opcional(
                self.descripcion,
                campo="descripción",
                maximo=500,
                error=ProductoInvalidoError,
            ),
        )
        object.__setattr__(
            self,
            "activo",
            exigir_booleano(self.activo, campo="activo", error=ProductoInvalidoError),
        )

    @property
    def nombre_normalizado(self) -> str:
        """Nombre en minúsculas y sin espacios repetidos, para detectar duplicados."""
        return self.nombre.casefold()

    def pertenece_a_categoria_permitida(self) -> bool:
        """Reafirma la regla de negocio principal."""
        return self.categoria.es_permitida()

    def desactivar(self) -> Producto:
        """Devuelve una copia inactiva del producto."""
        return replace(self, activo=False)

    def activar(self) -> Producto:
        """Devuelve una copia activa del producto."""
        return replace(self, activo=True)

    def __str__(self) -> str:
        return f"{self.nombre} ({self.categoria.etiqueta}, {self.unidad_medida.simbolo})"

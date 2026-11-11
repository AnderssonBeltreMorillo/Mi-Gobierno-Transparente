"""DTO de salida para productos."""

from __future__ import annotations

from dataclasses import dataclass

from ...domain.value_objects.categoria_producto import CategoriaProducto
from ...domain.value_objects.unidad_medida import UnidadMedida


@dataclass(frozen=True, slots=True)
class ProductoDTO:
    """Representación de un producto lista para la capa de entrada."""

    id: str
    nombre: str
    categoria: CategoriaProducto
    unidad_medida: UnidadMedida
    marca: str | None
    descripcion: str | None
    activo: bool

    def to_dict(self) -> dict[str, object]:
        """Serializa a primitivas JSON-friendly."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "categoria": self.categoria.value,
            "unidad_medida": self.unidad_medida.value,
            "marca": self.marca,
            "descripcion": self.descripcion,
            "activo": self.activo,
        }

"""Puerto generador de identificadores."""

from __future__ import annotations

from abc import ABC, abstractmethod


class GeneradorIdentificadores(ABC):
    """Abstracción para crear identificadores únicos.

    La infraestructura puede usar UUIDs, ULIDs o los IDs autogenerados por
    Firestore. La aplicación no debe depender de esa decisión.
    """

    @abstractmethod
    def nuevo(self) -> str:
        """Devuelve un identificador único no vacío."""

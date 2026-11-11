"""Adaptador de identificadores basado en UUID versión 4."""

from __future__ import annotations

from uuid import uuid4

from ..application.ports.generador_identificadores import GeneradorIdentificadores


class GeneradorUuid4(GeneradorIdentificadores):
    """Genera identificadores únicos con ``uuid4``.

    El UUID se devuelve como texto con guiones (36 caracteres), que cumple las
    invariantes de identificador del dominio y es seguro para usarlo como ID de
    documento en Firestore.
    """

    def nuevo(self) -> str:
        """Devuelve un UUID4 nuevo en formato canónico."""
        return str(uuid4())


__all__ = ["GeneradorUuid4"]

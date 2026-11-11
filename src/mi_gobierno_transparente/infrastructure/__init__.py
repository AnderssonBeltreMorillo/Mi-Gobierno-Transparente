"""Capa de infraestructura: adaptadores concretos para servicios externos.

Los adaptadores que dependen de SDKs opcionales (``firebase-admin``,
``requests``, ``beautifulsoup4``) no se reexportan aquí para no cargarlos al
importar el paquete. Importe el módulo concreto que necesite. Los adaptadores
ligeros de reloj e identificadores sí se exponen porque no tienen dependencias
externas.
"""

from .generador_uuid import GeneradorUuid4
from .reloj_sistema import RelojSistema

__all__ = ["GeneradorUuid4", "RelojSistema"]

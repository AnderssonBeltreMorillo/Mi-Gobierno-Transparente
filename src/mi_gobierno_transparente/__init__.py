"""Backend del demo 'Mi gobierno transparente'.

Arquitectura Onion:

- ``domain``: entidades, objetos de valor, servicios y reglas de negocio puras.
- ``application``: casos de uso, DTOs y puertos (interfaces abstractas).
- ``infrastructure``: adaptadores concretos (Firestore, API, etc.). Pendiente.
"""

__version__ = "0.1.0"

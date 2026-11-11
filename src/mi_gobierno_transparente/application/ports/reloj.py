"""Puerto de reloj para que los casos de uso sean deterministas en pruebas."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime


class Reloj(ABC):
    """Fuente de tiempo inyectable.

    Las implementaciones deben devolver ``datetime`` con zona horaria (UTC es
    la recomendación) para que las evaluaciones sean auditables.
    """

    @abstractmethod
    def ahora(self) -> datetime:
        """Devuelve el instante actual con zona horaria."""

    def hoy(self) -> date:
        """Devuelve la fecha actual en la zona horaria del reloj."""
        return self.ahora().date()

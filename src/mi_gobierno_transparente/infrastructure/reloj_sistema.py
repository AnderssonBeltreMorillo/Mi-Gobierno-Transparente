"""Adaptador de reloj basado en el reloj del sistema."""

from __future__ import annotations

from datetime import datetime, timezone

from ..application.ports.reloj import Reloj


class RelojSistema(Reloj):
    """Reloj real que devuelve instantes en UTC.

    Se mantiene deliberadamente simple: la zona horaria UTC evita ambigüedades
    en las evaluaciones y hace que los documentos de Firestore sean comparables
    entre despliegues.
    """

    def ahora(self) -> datetime:
        """Devuelve el instante actual con zona horaria UTC."""
        # Se usa ``timezone.utc`` de forma explícita por requisito del proyecto.
        return datetime.now(timezone.utc)  # noqa: UP017


__all__ = ["RelojSistema"]

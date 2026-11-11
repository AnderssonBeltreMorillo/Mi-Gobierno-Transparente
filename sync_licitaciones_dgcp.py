"""Punto de entrada ejecutable para la sincronización automática de DGCP."""

from mi_gobierno_transparente.infrastructure.dgcp_sync import evaluar_renglones, main

__all__ = ["evaluar_renglones", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

"""Recalcula los renglones de licitaciones ya guardadas en Firestore.

Uso::

    python recalcular_existentes.py
    python recalcular_existentes.py --dry-run

No descubre ni descarga procesos nuevos de la DGCP. Solo lee los expedientes
indicados, vuelve a consultar los catálogos de supermercados y actualiza los
montos, estados y equivalencias con el motor vigente.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from mi_gobierno_transparente.infrastructure.dgcp_sync import recalcular_documento
from mi_gobierno_transparente.infrastructure.firebase_repository import (
    crear_cliente_firestore,
)
from mi_gobierno_transparente.infrastructure.market_search_adapter import (
    CatalogoDirectoSupermercados,
)
from mi_gobierno_transparente.presentation.config import cargar_configuracion

CODIGOS: tuple[str, ...] = (
    "DASAC-CCC-LPA-2026-0011",
    "HFMP-DAF-CM-2026-0148",
    "HPMINSA-DAF-CD-2026-0132",
    "Hosp. Juan Bosch-DAF-CM-2026-0194",
)


def _argumentos(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Recalcula licitaciones existentes con el motor de unidades, "
            "empaques y filtro semántico vigente."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calcula y muestra el resumen sin escribir en Firestore.",
    )
    parser.add_argument(
        "--codigos",
        nargs="*",
        default=list(CODIGOS),
        help="Códigos a recalcular (por defecto, los cuatro expedientes).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    opciones = _argumentos(argv)
    configuracion = cargar_configuracion()
    cliente = crear_cliente_firestore(
        project_id=configuracion.project_id,
        ruta_credenciales=configuracion.ruta_credenciales,
        credenciales_json=configuracion.credenciales_json,
        emulador_host=configuracion.emulador_host,
    )
    procesados = 0
    with CatalogoDirectoSupermercados() as buscador:
        for codigo in opciones.codigos:
            resumen = recalcular_documento(
                cliente,
                buscador,
                codigo,
                dry_run=opciones.dry_run,
            )
            if resumen.get("procesado"):
                print(
                    f"{codigo}: {resumen['versiones']} versiones, "
                    f"{resumen['renglones']} renglones evaluados, "
                    f"{resumen['sin_referencia']} sin referencia."
                )
                procesados += 1
            else:
                print(f"{codigo}: omitido ({resumen.get('motivo', 'vacío')}).")
    modo = "simulación (sin escribir)" if opciones.dry_run else "Firestore actualizado"
    print(f"Recálculo terminado: {procesados} expedientes procesados; {modo}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

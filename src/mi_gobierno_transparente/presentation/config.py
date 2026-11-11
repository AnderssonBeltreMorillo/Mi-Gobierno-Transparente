"""Configuración de la API leída desde variables de entorno.

La configuración no crea clientes ni valida credenciales: solo traduce el
entorno a valores tipados. La conexión a Firestore se hace de forma perezosa en
``dependencies.py`` para que el proceso pueda arrancar y responder ``/health``
incluso si el backend aún no está disponible.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_ORIGENES_POR_DEFECTO: tuple[str, ...] = (
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
)

_VARIABLES_CREDENCIALES: tuple[str, ...] = (
    "FIREBASE_CREDENTIALS",
    "GOOGLE_APPLICATION_CREDENTIALS",
)


@dataclass(frozen=True, slots=True)
class ConfiguracionAPI:
    """Parámetros de ejecución de la capa HTTP."""

    origenes_cors: tuple[str, ...]
    permitir_credenciales: bool
    ruta_credenciales: Path | None
    credenciales_json: Mapping[str, object] | None
    project_id: str | None
    emulador_host: str | None
    port: int


def _leer_origenes_cors() -> tuple[str, ...]:
    valor = os.environ.get("CORS_ORIGINS")
    if valor is None:
        return _ORIGENES_POR_DEFECTO

    origenes = tuple(origen.strip() for origen in valor.split(",") if origen.strip())
    return origenes or _ORIGENES_POR_DEFECTO


def _leer_ruta_credenciales() -> Path | None:
    for variable in _VARIABLES_CREDENCIALES:
        valor = os.environ.get(variable)
        if valor:
            ruta = Path(valor).expanduser()
            if ruta.is_file():
                return ruta
            if os.environ.get("FIREBASE_CREDENTIALS_JSON"):
                return None
            return ruta

    predeterminada = Path("firebase_credentials.json")
    if predeterminada.is_file():
        return predeterminada
    return None


def _leer_credenciales_json() -> Mapping[str, object] | None:
    """Lee JSON en texto o Base64; se usa si no existe una ruta local."""
    valor = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if not valor:
        return None
    valor_limpio = "".join(valor.split())
    try:
        documento: object = json.loads(valor)
    except json.JSONDecodeError:
        try:
            try:
                bytes_json = base64.b64decode(valor_limpio, validate=True)
            except ValueError:
                bytes_json = base64.urlsafe_b64decode(
                    valor_limpio + "=" * (-len(valor_limpio) % 4)
                )
            decodificado = bytes_json.decode("utf-8")
            documento = json.loads(decodificado)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "FIREBASE_CREDENTIALS_JSON debe ser JSON válido en texto o Base64."
            ) from exc
    if not isinstance(documento, Mapping):
        raise ValueError("FIREBASE_CREDENTIALS_JSON debe contener un objeto JSON.")
    return {str(clave): campo for clave, campo in documento.items()}


def cargar_configuracion() -> ConfiguracionAPI:
    """Construye la configuración a partir del entorno actual."""
    origenes = _leer_origenes_cors()
    ruta_credenciales = _leer_ruta_credenciales()
    credenciales_json = None if ruta_credenciales else _leer_credenciales_json()
    proyecto_json = credenciales_json.get("project_id") if credenciales_json else None
    return ConfiguracionAPI(
        origenes_cors=origenes,
        permitir_credenciales="*" not in origenes,
        ruta_credenciales=ruta_credenciales,
        credenciales_json=credenciales_json,
        project_id=os.environ.get("FIREBASE_PROJECT_ID") or (str(proyecto_json) if proyecto_json else None),
        emulador_host=os.environ.get("FIRESTORE_EMULATOR_HOST") or None,
        port=int(os.environ.get("PORT", "8000")),
    )


__all__ = ["ConfiguracionAPI", "cargar_configuracion"]

"""Validación de credenciales Firebase en texto JSON o Base64."""

from __future__ import annotations

import base64
import json
import os
import unittest
from unittest.mock import patch

from mi_gobierno_transparente.presentation.config import cargar_configuracion


class TestFirebaseCredentialsJson(unittest.TestCase):
    def test_lee_json_plano_si_no_hay_archivo_de_credenciales(self) -> None:
        documento = {"type": "service_account", "project_id": "proyecto-prueba"}
        with patch.dict(os.environ, {
            "FIREBASE_CREDENTIALS": "C:/no-existe/firebase.json",
            "FIREBASE_CREDENTIALS_JSON": json.dumps(documento),
        }, clear=True):
            configuracion = cargar_configuracion()

        self.assertIsNone(configuracion.ruta_credenciales)
        self.assertEqual(configuracion.credenciales_json, documento)
        self.assertEqual(configuracion.project_id, "proyecto-prueba")

    def test_lee_json_base64(self) -> None:
        documento = {"type": "service_account", "project_id": "proyecto-base64"}
        codificado = base64.b64encode(json.dumps(documento).encode("utf-8")).decode("ascii")
        with patch.dict(os.environ, {
            "FIREBASE_CREDENTIALS": "C:/no-existe/firebase.json",
            "FIREBASE_CREDENTIALS_JSON": codificado,
        }, clear=True):
            configuracion = cargar_configuracion()
        self.assertEqual(configuracion.credenciales_json, documento)

    def test_rechaza_secret_json_malformado(self) -> None:
        with patch.dict(os.environ, {
            "FIREBASE_CREDENTIALS": "C:/no-existe/firebase.json",
            "FIREBASE_CREDENTIALS_JSON": "esto-no-es-json-ni-base64",
        }, clear=True):
            with self.assertRaises(ValueError):
                cargar_configuracion()


if __name__ == "__main__":
    unittest.main()

"""El adaptador Firestore acepta credenciales cargadas desde JSON en memoria."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from mi_gobierno_transparente.infrastructure.firebase_repository import crear_cliente_firestore


class TestCredencialesFirebase(unittest.TestCase):
    def test_cliente_firestore_construye_certificate_desde_json(self) -> None:
        credencial_json = {
            "type": "service_account",
            "project_id": "proyecto-prueba",
            "private_key": "no-es-una-clave-real",
        }
        with (
            patch("firebase_admin.get_app", side_effect=ValueError("app inexistente")),
            patch("firebase_admin.credentials.Certificate", return_value="credencial") as certificado,
            patch("firebase_admin.initialize_app", return_value="app") as inicializar,
            patch("firebase_admin.firestore.client", return_value="cliente"),
        ):
            cliente = crear_cliente_firestore(
                project_id="proyecto-prueba",
                credenciales_json=credencial_json,
            )

        certificado.assert_called_once_with(credencial_json)
        inicializar.assert_called_once_with(
            "credencial",
            {"projectId": "proyecto-prueba"},
            name="mi-gobierno-transparente",
        )
        self.assertEqual(cliente, "cliente")


if __name__ == "__main__":
    unittest.main()

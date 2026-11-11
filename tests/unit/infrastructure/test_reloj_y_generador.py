"""Pruebas de los adaptadores de reloj e identificadores."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest import TestCase
from uuid import UUID

from mi_gobierno_transparente.infrastructure import GeneradorUuid4, RelojSistema


class TestRelojSistema(TestCase):
    def test_ahora_devuelve_utc(self) -> None:
        antes = datetime.now(UTC)
        momento = RelojSistema().ahora()
        despues = datetime.now(UTC)

        self.assertIsNotNone(momento.tzinfo)
        self.assertEqual(momento.utcoffset(), timedelta(0))
        self.assertGreaterEqual(momento, antes)
        self.assertLessEqual(momento, despues)

    def test_hoy_usa_la_fecha_utc(self) -> None:
        self.assertEqual(RelojSistema().hoy(), datetime.now(UTC).date())


class TestGeneradorUuid4(TestCase):
    def test_genera_uuid4_unicos(self) -> None:
        generador = GeneradorUuid4()
        identificadores = {generador.nuevo() for _ in range(100)}

        self.assertEqual(len(identificadores), 100)
        for identificador in identificadores:
            self.assertEqual(UUID(identificador).version, 4)

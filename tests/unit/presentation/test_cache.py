"""Pruebas de caché TTL, stale-while-revalidate y límite global de refresh."""

from __future__ import annotations

import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from mi_gobierno_transparente.presentation.cache import CacheTTL


class TestCacheTTL(unittest.TestCase):
    def test_miss_concurrente_hace_una_sola_carga(self) -> None:
        cache = CacheTTL(ttl_segundos=10)
        iniciado = threading.Event()
        liberar = threading.Event()
        cuenta = 0
        cuenta_lock = threading.Lock()

        def cargar() -> str:
            nonlocal cuenta
            with cuenta_lock:
                cuenta += 1
            iniciado.set()
            liberar.wait(2)
            return "desde firestore"

        with ThreadPoolExecutor(max_workers=12) as pool:
            futuros = [pool.submit(cache.obtener, "kpi", cargar) for _ in range(12)]
            self.assertTrue(iniciado.wait(1))
            liberar.set()
            valores = [futuro.result(timeout=2) for futuro in futuros]

        self.assertEqual(cuenta, 1)
        self.assertEqual(set(valores), {"desde firestore"})

    def test_force_refresh_sirve_cache_y_limita_recargas_globales(self) -> None:
        cache = CacheTTL(ttl_segundos=10, intervalo_force_refresh=0.5)
        self.assertEqual(cache.obtener("productos", lambda: "productos-v1"), "productos-v1")
        self.assertEqual(cache.obtener("licitaciones", lambda: "licitaciones-v1"), "licitaciones-v1")
        inicio = threading.Event()
        liberar = threading.Event()
        cuenta = 0

        def refrescar() -> str:
            nonlocal cuenta
            cuenta += 1
            inicio.set()
            liberar.wait(2)
            return "v2"

        # Responde sin esperar al scraper/Firestore.
        self.assertEqual(cache.obtener("productos", refrescar, force_refresh=True), "productos-v1")
        self.assertTrue(inicio.wait(1))
        # El límite se comparte incluso con otra ruta: retorna su propio caché.
        self.assertEqual(
            cache.obtener("licitaciones", lambda: "licitaciones-v2", force_refresh=True),
            "licitaciones-v1",
        )
        self.assertEqual(cuenta, 1)
        liberar.set()
        limite = time.monotonic() + 2
        while time.monotonic() < limite and cache.obtener("productos", lambda: "productos-v3") != "v2":
            time.sleep(0.01)
        self.assertEqual(cache.obtener("productos", lambda: "productos-v3"), "v2")


if __name__ == "__main__":
    unittest.main()

"""Pruebas del scraper DGCP con transporte HTTP simulado."""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from typing import Any

import requests

from mi_gobierno_transparente.infrastructure.dgcp_scraper import (
    DgcpScraper,
    SelectoresDgcp,
)
from mi_gobierno_transparente.infrastructure.exceptions import ErrorDeExtraccion

_HTML = """
<html>
  <body>
    <table>
      <tbody>
        <tr>
          <td class="producto">Arroz extra 1 kg</td>
          <td class="precio">S/ 4.50</td>
          <td class="proveedor">Proveedor Andino</td>
          <td class="fecha">01/02/2026</td>
          <td><a href="/detalle/1">Ver</a></td>
        </tr>
        <tr>
          <td class="producto">Aceite vegetal 1 L</td>
          <td class="precio">S/ 8.90</td>
          <td class="proveedor">Proveedor Costa</td>
          <td class="fecha">02/02/2026</td>
          <td><a href="/detalle/2">Ver</a></td>
        </tr>
        <tr>
          <td class="producto">Fila sin precio</td>
          <td class="precio">no disponible</td>
          <td class="proveedor">Proveedor X</td>
          <td class="fecha">03/02/2026</td>
          <td><a href="/detalle/3">Ver</a></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


class _RespuestaFalsa:
    def __init__(self, text: str, url: str = "https://compras.gob/buscar") -> None:
        self.text = text
        self.url = url

    def raise_for_status(self) -> None:
        return None


class _SesionFalsa:
    def __init__(self, respuesta: _RespuestaFalsa) -> None:
        self.respuesta = respuesta
        self.headers: dict[str, str] = {}
        self.llamadas: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        *,
        params: dict[str, object] | None = None,
        timeout: float | None = None,
    ) -> _RespuestaFalsa:
        self.llamadas.append({"url": url, "params": params, "timeout": timeout})
        return self.respuesta


class _SesionConError:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def get(self, *args: object, **kwargs: object) -> _RespuestaFalsa:
        raise requests.RequestException("fallo de red simulado")


class TestDgcpScraper(unittest.TestCase):
    def test_extrae_precios_de_una_tabla(self) -> None:
        sesion = _SesionFalsa(_RespuestaFalsa(_HTML))
        scraper = DgcpScraper(
            "https://compras.gob/buscar",
            session=sesion,  # type: ignore[arg-type]
        )

        precios = scraper.extraer("arroz", limite=10)

        self.assertEqual(len(precios), 2)
        primero = precios[0]
        self.assertEqual(primero.producto, "Arroz extra 1 kg")
        self.assertEqual(primero.monto, Decimal("4.50"))
        self.assertEqual(primero.moneda, "PEN")
        self.assertEqual(primero.proveedor, "Proveedor Andino")
        self.assertEqual(primero.fecha, date(2026, 2, 1))
        self.assertEqual(primero.url, "https://compras.gob/detalle/1")
        self.assertEqual(primero.fuente, "DGCP")
        self.assertEqual(
            sesion.llamadas,
            [
                {
                    "url": "https://compras.gob/buscar",
                    "params": {"q": "arroz"},
                    "timeout": 15.0,
                }
            ],
        )

    def test_respeta_el_limite(self) -> None:
        scraper = DgcpScraper("https://compras.gob/buscar")

        precios = scraper.extraer_de_html(_HTML, limite=1)

        self.assertEqual(len(precios), 1)
        self.assertEqual(precios[0].producto, "Arroz extra 1 kg")

    def test_permite_selectores_personalizados(self) -> None:
        html = """
        <table><tbody>
          <tr>
            <td class="nombre">Jabón</td>
            <td class="valor">S/ 3.20</td>
          </tr>
        </tbody></table>
        """
        scraper = DgcpScraper(
            "https://compras.gob/buscar",
            selectores=SelectoresDgcp(
                producto="td.nombre",
                precio="td.valor",
                proveedor=None,
                fecha=None,
                enlace=None,
            ),
        )

        precios = scraper.extraer_de_html(html)

        self.assertEqual(len(precios), 1)
        self.assertEqual(precios[0].producto, "Jabón")
        self.assertEqual(precios[0].monto, Decimal("3.20"))
        self.assertIsNone(precios[0].proveedor)
        self.assertIsNone(precios[0].url)

    def test_consulta_vacia_es_invalida(self) -> None:
        scraper = DgcpScraper("https://compras.gob/buscar")

        with self.assertRaises(ValueError):
            scraper.extraer("   ")

    def test_error_http_se_traduce_a_error_de_extraccion(self) -> None:
        scraper = DgcpScraper(
            "https://compras.gob/buscar",
            session=_SesionConError(),  # type: ignore[arg-type]
        )

        with self.assertRaises(ErrorDeExtraccion):
            scraper.extraer("arroz")


if __name__ == "__main__":
    unittest.main()

"""Pruebas de la consulta paginada a la API oficial DGCP y su evaluación."""

from __future__ import annotations

import unittest
from decimal import Decimal
from typing import Any, cast
from unittest.mock import Mock

from mi_gobierno_transparente.infrastructure.dgcp_scraper import DgcpOpenDataClient
from mi_gobierno_transparente.infrastructure.market_search_adapter import OfertaSupermercado
from sync_licitaciones_dgcp import evaluar_renglones


class _Respuesta:
    def __init__(self, datos: object) -> None:
        self.datos = datos

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self.datos


class _Sesion:
    def __init__(self, respuestas: list[object]) -> None:
        self.respuestas = respuestas
        self.llamadas: list[dict[str, Any]] = []
        self.headers: dict[str, str] = {}

    def get(self, url: str, *, params: dict[str, object], timeout: float) -> _Respuesta:
        self.llamadas.append({"url": url, "params": params, "timeout": timeout})
        return _Respuesta(self.respuestas.pop(0))


def _envuelta(content: list[dict[str, object]], page: int, pages: int) -> dict[str, object]:
    return {
        "code": 200,
        "hasError": False,
        "payload": {"content": content},
        "page": page,
        "pages": pages,
    }


class TestDgcpOpenDataClient(unittest.TestCase):
    def test_busca_procesos_con_paginacion_y_fechas(self) -> None:
        sesion = _Sesion([
            _envuelta([{"codigo_proceso": "ABC-2026-1"}], 1, 2),
            _envuelta([{"codigo_proceso": "ABC-2026-2"}], 2, 2),
        ])
        api = DgcpOpenDataClient(session=cast(Any, sesion), page_size=50)

        procesos = api.buscar_procesos(
            desde=__import__("datetime").date(2026, 10, 1),
            hasta=__import__("datetime").date(2026, 11, 9),
            max_paginas=5,
        )

        self.assertEqual([proceso["codigo_proceso"] for proceso in procesos], ["ABC-2026-1", "ABC-2026-2"])
        self.assertEqual(sesion.llamadas[0]["url"], "https://datosabiertos.dgcp.gob.do/api-dgcp/v1/procesos")
        self.assertEqual(sesion.llamadas[0]["params"]["startdate"], "2026-10-01")
        self.assertEqual(sesion.llamadas[1]["params"]["page"], 2)

    def test_obtiene_articulos_por_codigo_de_proceso(self) -> None:
        sesion = _Sesion([_envuelta([{"codigo_proceso": "ABC-2026-1", "cantidad": 2}], 1, 1)])
        api = DgcpOpenDataClient(session=cast(Any, sesion))

        articulos = api.obtener_articulos("ABC-2026-1")

        self.assertEqual(len(articulos), 1)
        self.assertEqual(sesion.llamadas[0]["url"], "https://datosabiertos.dgcp.gob.do/api-dgcp/v1/procesos/articulos")
        self.assertEqual(sesion.llamadas[0]["params"]["proceso"], "ABC-2026-1")

    def test_evaluacion_usa_el_minimo_y_conserva_las_fuentes(self) -> None:
        ofertas = [
            OfertaSupermercado("Canela 60 g", "Nacional", Decimal("59.95"), "DOP", "https://supermercadosnacional.com/canela"),
            OfertaSupermercado("Canela 60 g", "La Sirena", Decimal("58.00"), "DOP", "https://sirena.do/canela"),
        ]
        buscador = Mock()
        buscador.buscar_para_renglon.return_value = ofertas
        proceso = {"codigo_proceso": "ABC-2026-1", "fecha_publicacion": "2026-11-01"}
        articulos = [{
            "familia_unspsc": "50170000",
            "descripcion_usuario": "Canela sobre 2 onzas",
            "unidad_medida": "Unidad",
            "cantidad": 1_000_000,
            "precio_unitario_estimado": 70,
            "precio_total_estimado": 70_000_000,
        }]

        resultado = evaluar_renglones(proceso, articulos, cast(Any, buscador))
        fila = resultado["version"]["auditoria_renglones"][0]

        self.assertEqual(fila["precio_mercado"], "58.00")
        self.assertEqual(fila["fuente_mercado"], "La Sirena | https://sirena.do/canela")
        self.assertEqual(len(fila["fuentes_mercado"]), 2)
        self.assertEqual(fila["diferencia"], "12.00")
        self.assertEqual(fila["sobreprecio"], "20.69")
        self.assertIn("presentación equivalente", fila["equivalencia"])
        self.assertIn("Catálogo: Canela 60 g", fila["presentacion_comercial"])


class TestEvaluacionModoRecalculo(unittest.TestCase):
    def _buscador(self) -> Mock:
        buscador = Mock()
        buscador.buscar_para_renglon.return_value = [
            OfertaSupermercado(
                "Repuesto 1 unidad",
                "Nacional",
                Decimal("100.00"),
                "DOP",
                "https://supermercadosnacional.com/repuesto",
            )
        ]
        return buscador

    def _articulo(self) -> dict[str, object]:
        return {
            "familia_unspsc": "12345678",
            "descripcion_usuario": "REPUESTO",
            "unidad_medida": "Unidad",
            "cantidad": 2,
            "precio_unitario_estimado": 150,
            "precio_total_estimado": 300,
        }

    def test_filtrar_objetivos_false_recalcula_renglones_guardados(self) -> None:
        proceso = {"codigo_proceso": "ABC-2026-9"}

        filtrado = evaluar_renglones(
            proceso, [self._articulo()], cast(Any, self._buscador())
        )
        completo = evaluar_renglones(
            proceso,
            [self._articulo()],
            cast(Any, self._buscador()),
            filtrar_objetivos=False,
        )

        self.assertEqual(filtrado["version"]["auditoria_renglones"], [])
        self.assertEqual(len(completo["version"]["auditoria_renglones"]), 1)
        self.assertEqual(
            completo["version"]["auditoria_renglones"][0]["precio_mercado"],
            "100.00",
        )

    def test_monto_total_conocido_conserva_el_total_del_expediente(self) -> None:
        resultado = evaluar_renglones(
            {"codigo_proceso": "ABC-2026-9"},
            [self._articulo()],
            cast(Any, self._buscador()),
            filtrar_objetivos=False,
            monto_total_conocido=Decimal("5000.00"),
        )
        version = resultado["version"]

        self.assertEqual(version["monto_total"], "5000.00")
        self.assertEqual(version["monto_mercado"], "200.00")
        self.assertIn("motor_version", version)

    def test_sin_referencia_incluye_renglones_no_comparables(self) -> None:
        buscador = Mock()
        buscador.buscar_para_renglon.return_value = []

        resultado = evaluar_renglones(
            {"codigo_proceso": "ABC-2026-9"},
            [self._articulo()],
            cast(Any, buscador),
            filtrar_objetivos=False,
        )

        self.assertEqual(len(resultado["renglones_sin_referencia"]), 1)
        self.assertEqual(resultado["version"]["auditoria_renglones"], [])


if __name__ == "__main__":
    unittest.main()

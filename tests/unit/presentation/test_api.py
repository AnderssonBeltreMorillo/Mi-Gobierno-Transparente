"""Pruebas de la API HTTP con repositorios en memoria."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest import TestCase

from fastapi.testclient import TestClient

from mi_gobierno_transparente.application.dto import (
    EvaluarPrecioCommand,
    RegistrarPrecioMercadoCommand,
    RegistrarPrecioReportadoCommand,
    RegistrarProductoCommand,
)
from mi_gobierno_transparente.application.use_cases import (
    EvaluarPrecio,
    ListarEvaluaciones,
    ListarProductos,
    ObtenerResumenRiesgo,
    RegistrarPrecioMercado,
    RegistrarPrecioReportado,
    RegistrarProducto,
)
from mi_gobierno_transparente.domain.services import EvaluadorPrecio
from mi_gobierno_transparente.domain.value_objects import (
    CategoriaProducto,
    UnidadMedida,
)
from mi_gobierno_transparente.presentation.app import crear_app
from mi_gobierno_transparente.presentation.cache import cache_lecturas
from mi_gobierno_transparente.presentation.dependencies import (
    obtener_cliente_firestore,
    obtener_listar_evaluaciones,
    obtener_listar_productos,
    obtener_obtener_resumen_riesgo,
)
from tests.unit.application.fakes import (
    EvaluacionPrecioRepositorioEnMemoria,
    GeneradorSecuencial,
    PrecioMercadoRepositorioEnMemoria,
    PrecioReportadoRepositorioEnMemoria,
    ProductoRepositorioEnMemoria,
    RelojFijo,
)


class TestAPI(TestCase):
    def setUp(self) -> None:
        self.productos = ProductoRepositorioEnMemoria()
        self.precios_mercado = PrecioMercadoRepositorioEnMemoria()
        self.precios_reportados = PrecioReportadoRepositorioEnMemoria()
        self.evaluaciones = EvaluacionPrecioRepositorioEnMemoria()
        self.reloj = RelojFijo(datetime(2026, 1, 15, 12, 0, tzinfo=UTC))
        self.generador = GeneradorSecuencial("id")

        producto = RegistrarProducto(
            self.productos,
            self.generador,
        ).ejecutar(
            RegistrarProductoCommand(
                nombre="Lata de Habichuelas Rojas 15oz",
                categoria=CategoriaProducto.ALIMENTOS,
                unidad_medida=UnidadMedida.UNIDAD,
                marca="Goya",
            )
        )
        self.producto_id = producto.id

        RegistrarPrecioMercado(
            self.productos,
            self.precios_mercado,
            self.generador,
            self.reloj,
        ).ejecutar(
            RegistrarPrecioMercadoCommand(
                producto_id=self.producto_id,
                monto=Decimal("100.00"),
                fuente="Plaza Lama (Santo Domingo)",
            )
        )
        reportado = RegistrarPrecioReportado(
            self.productos,
            self.precios_reportados,
            self.generador,
            self.reloj,
        ).ejecutar(
            RegistrarPrecioReportadoCommand(
                producto_id=self.producto_id,
                monto=Decimal("150.00"),
                establecimiento="Licitación DGCP - Lote 1",
            )
        )
        EvaluarPrecio(
            self.productos,
            self.precios_mercado,
            self.precios_reportados,
            self.evaluaciones,
            EvaluadorPrecio(),
            self.generador,
            self.reloj,
        ).ejecutar(
            EvaluarPrecioCommand(
                producto_id=self.producto_id,
                precio_reportado_id=reportado.id,
            )
        )

        self.app = crear_app()
        self.app.dependency_overrides[obtener_listar_productos] = lambda: (
            ListarProductos(self.productos)
        )
        self.app.dependency_overrides[obtener_listar_evaluaciones] = lambda: (
            ListarEvaluaciones(self.evaluaciones)
        )
        self.app.dependency_overrides[obtener_obtener_resumen_riesgo] = lambda: (
            ObtenerResumenRiesgo(self.evaluaciones)
        )
        self.cliente = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_health(self) -> None:
        respuesta = self.cliente.get("/health")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["estado"], "ok")

    def test_listar_licitaciones_incluye_procesos_sincronizados_de_firestore(self) -> None:
        proceso = {
            "id_version": "auto-HFMP-DAF-CM-2026-0148",
            "version": 1,
            "codigo": "HFMP-DAF-CM-2026-0148",
            "titulo": "Compra de despensa",
            "auditoria_renglones": [],
        }

        class DocumentoFalso:
            id = "HFMP-DAF-CM-2026-0148"

            def to_dict(self) -> dict[str, object]:
                return {"codigo": self.id, "version_original": proceso, "versiones": [proceso]}

        class ColeccionFalsa:
            def stream(self) -> list[DocumentoFalso]:
                return [DocumentoFalso()]

        class ClienteFalso:
            def collection(self, _nombre: str) -> ColeccionFalsa:
                return ColeccionFalsa()

        self.app.dependency_overrides[obtener_cliente_firestore] = ClienteFalso  # type: ignore[assignment]
        cache_lecturas.limpiar()

        respuesta = self.cliente.get("/licitaciones", params={"force_refresh": "true"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(
            "HFMP-DAF-CM-2026-0148",
            [version["codigo"] for version in respuesta.json()],
        )

    def test_listar_productos(self) -> None:
        respuesta = self.cliente.get("/productos")

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(len(datos), 1)
        self.assertEqual(datos[0]["id"], self.producto_id)
        self.assertEqual(datos[0]["categoria"], "alimentos")
        self.assertEqual(datos[0]["unidad_medida"], "unidad")

    def test_listar_evaluaciones_con_nivel_de_riesgo(self) -> None:
        respuesta = self.cliente.get("/evaluaciones")

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(len(datos), 1)
        self.assertEqual(datos[0]["nivel_riesgo"], "alto_riesgo")
        self.assertEqual(datos[0]["sobreprecio_porcentaje"], "50.00")
        self.assertTrue(datos[0]["requiere_intervencion"])

    def test_filtrar_evaluaciones_por_nivel(self) -> None:
        respuesta = self.cliente.get(
            "/evaluaciones",
            params={"nivel_riesgo": "precio_justo"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), [])

    def test_resumen_riesgo(self) -> None:
        respuesta = self.cliente.get("/resumen-riesgo")

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["total_evaluaciones"], 1)
        self.assertEqual(datos["precio_justo"], 0)
        self.assertEqual(datos["alerta_amarilla"], 0)
        self.assertEqual(datos["alto_riesgo"], 1)
        self.assertEqual(datos["porcentaje_alto_riesgo"], "100.00")

    def test_cors_para_frontend(self) -> None:
        respuesta = self.cliente.get(
            "/productos",
            headers={"Origin": "http://localhost:5173"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.headers.get("access-control-allow-origin"),
            "http://localhost:5173",
        )

    def test_error_de_aplicacion_se_traduce_a_http(self) -> None:
        respuesta = self.cliente.get(
            "/evaluaciones",
            params={"desde": "2026-01-01T00:00:00"},
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["error"]["codigo"], "solicitud_invalida")

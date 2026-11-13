"""Pruebas del adaptador de búsqueda de supermercados con SerpApi simulado."""

from __future__ import annotations

import json
import unittest
from decimal import Decimal
from typing import Any

import httpx
import requests

from mi_gobierno_transparente.infrastructure.exceptions import (
    ConfiguracionFaltanteError,
    ErrorDeBusquedaMercado,
)
from mi_gobierno_transparente.infrastructure.market_search_adapter import (
    BuscadorPlazaLama,
    CatalogoDirectoSupermercados,
    OfertaSupermercado,
    SerpApiBuscadorSupermercados,
    seleccionar_oferta_minima,
)

_JSON = {
    "shopping_results": [
        {
            "title": "Arroz extra 1 kg",
            "source": "Wong",
            "extracted_price": 4.9,
            "currency": "PEN",
            "link": "https://wong.example/arroz",
        },
        {
            "title": "Aceite vegetal 1 L",
            "source": "Metro",
            "price": "S/ 8.50",
            "link": "https://metro.example/aceite",
        },
        {
            "title": "Producto sin precio",
            "source": "Plaza Vea",
        },
    ]
}


class _RespuestaJsonFalsa:
    def __init__(self, datos: object) -> None:
        self._datos = datos

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._datos


class _RespuestaJsonInvalida:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        raise ValueError("JSON inválido")


class _SesionFalsa:
    def __init__(self, respuesta: object) -> None:
        self.respuesta = respuesta
        self.headers: dict[str, str] = {}
        self.llamadas: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        *,
        params: dict[str, object] | None = None,
        timeout: float | None = None,
    ) -> object:
        self.llamadas.append({"url": url, "params": params, "timeout": timeout})
        return self.respuesta


class _SesionConError:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def get(self, *args: object, **kwargs: object) -> object:
        raise requests.RequestException("fallo de red simulado")


class _RespuestaHtmlFalsa:
    def __init__(self, texto: str) -> None:
        self.text = texto

    def raise_for_status(self) -> None:
        return None


class _SesionHtmlFalsa:
    def __init__(self, texto: str) -> None:
        self.texto = texto
        self.headers: dict[str, str] = {}
        self.llamadas: list[dict[str, Any]] = []

    def get(self, url: str, *, timeout: float | None = None) -> object:
        self.llamadas.append({"url": url, "timeout": timeout})
        return _RespuestaHtmlFalsa(self.texto)


class TestBuscadorPlazaLama(unittest.TestCase):
    def test_consulta_el_buscador_con_la_url_esperada(self) -> None:
        sesion = _SesionHtmlFalsa("<html></html>")
        buscador = BuscadorPlazaLama(session=sesion, timeout=20)  # type: ignore[arg-type]

        buscador.buscar("leche evaporada")

        self.assertEqual(len(sesion.llamadas), 1)
        self.assertEqual(
            sesion.llamadas[0]["url"],
            "https://plazalama.com.do/search?name=leche+evaporada",
        )
        self.assertEqual(sesion.llamadas[0]["timeout"], 20)

    def test_extrae_productos_del_payload_de_next_js(self) -> None:
        payload = json.dumps(
            '1:{"name":"Leche de Coco Goya 400ml","price":145,"photosUrl":[],'
            '"slug":"leche-de-coco-goya-400ml-41331021647","__typename":"CatalogProductModel"}'
        )
        html = f'<html><script>self.__next_f.push([1,{payload}])</script></html>'
        buscador = BuscadorPlazaLama(session=_SesionHtmlFalsa(html))  # type: ignore[arg-type]

        ofertas = buscador.buscar("leche")

        self.assertEqual(len(ofertas), 1)
        self.assertEqual(ofertas[0].producto, "Leche de Coco Goya 400ml")
        self.assertEqual(ofertas[0].establecimiento, "Plaza Lama")
        self.assertEqual(ofertas[0].monto, Decimal("145"))
        self.assertEqual(ofertas[0].moneda, "DOP")
        self.assertEqual(
            ofertas[0].url,
            "https://plazalama.com.do/leche-de-coco-goya-400ml-41331021647",
        )

    def test_extrae_productos_de_tarjetas_html_y_limpia_el_simbolo_de_peso(self) -> None:
        html = """
        <div class="product-card">
          <h3 class="product-name">Canela entera 60 gr</h3>
          <span class="price">RD$ 58,50</span>
          <a href="/canela-entera-60-gr-41331021647">Ver producto</a>
        </div>
        """
        buscador = BuscadorPlazaLama(session=_SesionHtmlFalsa(html))  # type: ignore[arg-type]

        ofertas = buscador.buscar("canela", limite=5)

        self.assertEqual(len(ofertas), 1)
        self.assertEqual(ofertas[0].producto, "Canela entera 60 gr")
        self.assertEqual(ofertas[0].monto, Decimal("58.50"))
        self.assertEqual(ofertas[0].establecimiento, "Plaza Lama")
        self.assertEqual(ofertas[0].moneda, "DOP")


class TestSerpApiBuscadorSupermercados(unittest.TestCase):
    def test_buscar_normaliza_los_resultados(self) -> None:
        sesion = _SesionFalsa(_RespuestaJsonFalsa(_JSON))
        buscador = SerpApiBuscadorSupermercados(
            api_key="clave-de-prueba",
            session=sesion,  # type: ignore[arg-type]
        )

        ofertas = buscador.buscar("arroz", limite=10)

        self.assertEqual(len(ofertas), 2)
        self.assertEqual(ofertas[0].producto, "Arroz extra 1 kg")
        self.assertEqual(ofertas[0].establecimiento, "Wong")
        self.assertEqual(ofertas[0].monto, Decimal("4.9"))
        self.assertEqual(ofertas[0].moneda, "PEN")
        self.assertEqual(ofertas[1].monto, Decimal("8.50"))
        self.assertEqual(ofertas[1].establecimiento, "Metro")
        self.assertEqual(ofertas[1].fuente, "serpapi")
        self.assertEqual(
            sesion.llamadas[0]["params"],
            {
                "engine": "google_shopping",
                "q": "arroz",
                "api_key": "clave-de-prueba",
                "gl": "pe",
                "hl": "es",
                "currency": "PEN",
            },
        )

    def test_respeta_el_limite(self) -> None:
        buscador = SerpApiBuscadorSupermercados(
            api_key="clave",
            session=_SesionFalsa(_RespuestaJsonFalsa(_JSON)),  # type: ignore[arg-type]
        )

        ofertas = buscador.buscar("arroz", limite=1)

        self.assertEqual(len(ofertas), 1)

    def test_busca_solo_ofertas_de_las_cuatro_cadenas_y_las_ordena_por_precio(self) -> None:
        datos = {
            "shopping_results": [
                {"title": "Canela 60 g", "source": "Nacional", "extracted_price": 59.95, "currency": "DOP", "link": "https://supermercadosnacional.com/canela"},
                {"title": "Canela 60 g", "source": "La Sirena", "extracted_price": 58, "currency": "DOP", "link": "https://nuevo.sirena.do/canela"},
                {"title": "Canela 60 g", "source": "Tienda externa", "extracted_price": 40, "currency": "DOP", "link": "https://otra-tienda.do/canela"},
            ]
        }
        sesion = _SesionFalsa(_RespuestaJsonFalsa(datos))
        buscador = SerpApiBuscadorSupermercados(
            api_key="clave-de-prueba",
            session=sesion,  # type: ignore[arg-type]
            pais="do",
            moneda="DOP",
        )

        ofertas = buscador.buscar_ofertas_cadenas_verificadas("Canela sobre 2 onzas")

        self.assertEqual([oferta.establecimiento for oferta in ofertas], ["La Sirena", "Nacional"])
        self.assertEqual(ofertas[0].monto, Decimal("58"))
        self.assertIn("sirena.do", ofertas[0].url or "")

    def test_sin_api_key_falla_explicitamente(self) -> None:
        buscador = SerpApiBuscadorSupermercados(api_key="")

        with self.assertRaises(ConfiguracionFaltanteError):
            buscador.buscar("arroz")

    def test_json_invalido_se_traduce_a_error_de_busqueda(self) -> None:
        buscador = SerpApiBuscadorSupermercados(
            api_key="clave",
            session=_SesionFalsa(_RespuestaJsonInvalida()),  # type: ignore[arg-type]
        )

        with self.assertRaises(ErrorDeBusquedaMercado):
            buscador.buscar("arroz")

    def test_error_http_se_traduce_a_error_de_busqueda(self) -> None:
        buscador = SerpApiBuscadorSupermercados(
            api_key="clave",
            session=_SesionConError(),  # type: ignore[arg-type]
        )

        with self.assertRaises(ErrorDeBusquedaMercado):
            buscador.buscar("arroz")


class TestCatalogoDirectoSupermercados(unittest.TestCase):
    def test_minimo_directo_de_las_cuatro_cadenas_sin_clave_de_pago(self) -> None:
        html_nacional = """
        <ul><li class="product-item">
          <a class="product-item-link" href="/canela-60-gr">Canela entera 60 gr</a>
          <span data-price-type="finalPrice"><span class="price">RD$ 59.95</span></span>
        </li></ul>
        """
        html_jumbo = """
        <ul><li class="product-item">
          <a class="product-item-link" href="/canela-60-gr">Canela entera 60 gr</a>
          <span data-price-type="finalPrice"><span class="price">$60,00</span></span>
        </li></ul>
        """
        html_plaza_lama = """
        <div class="product-card">
          <h3 class="product-name">CANELA ENTERA 60 GR</h3>
          <span class="price">RD$ 58,50</span>
          <a href="/canela-entera-60-gr-41331021647">Ver producto</a>
        </div>
        """
        sirena_json = [{
            "productName": "Canela entera 60 Gr",
            "linkText": "canela-entera-60-gr",
            "items": [{"name": "1 Und.", "sellers": [{"commertialOffer": {"Price": 57.75, "AvailableQuantity": 10}}]}],
        }]

        def responder(request: httpx.Request) -> httpx.Response:
            host = request.url.host
            if host == "supermercadosnacional.com":
                return httpx.Response(200, text=html_nacional)
            if host == "jumbo.com.do":
                return httpx.Response(200, text=html_jumbo)
            return httpx.Response(200, json=sirena_json)

        plaza_lama = BuscadorPlazaLama(
            session=_SesionHtmlFalsa(html_plaza_lama),  # type: ignore[arg-type]
        )
        cliente = httpx.Client(transport=httpx.MockTransport(responder))
        with CatalogoDirectoSupermercados(
            cliente=cliente,
            buscador_plaza_lama=plaza_lama,
            cache_ttl_segundos=10,
        ) as catalogo:
            ofertas = catalogo.buscar_para_renglon({
                "descripcion_usuario": "CANELA SOBRE 2 ONZAS",
                "unidad_medida": "Unidad",
            })

        self.assertEqual(
            {oferta.establecimiento for oferta in ofertas},
            {"Nacional", "La Sirena", "Jumbo", "Plaza Lama"},
        )
        minima = seleccionar_oferta_minima(ofertas)
        self.assertEqual(minima.establecimiento, "La Sirena")
        self.assertEqual(minima.monto, Decimal("57.75"))
        self.assertEqual(minima.moneda, "DOP")

    def test_escala_presentacion_de_tamano_distinto(self) -> None:
        html = """
        <ul><li class="product-item">
          <a class="product-item-link" href="/leche-307-gr">Leche Evaporada 307 Gr</a>
          <span class="price">RD$ 61.95</span>
        </li></ul>
        """

        def responder(request: httpx.Request) -> httpx.Response:
            if request.url.host == "supermercadosnacional.com":
                return httpx.Response(200, text=html)
            if request.url.host == "nuevo.sirena.do":
                return httpx.Response(200, json=[])
            return httpx.Response(200, text="<ul></ul>")

        plaza_lama = BuscadorPlazaLama(
            session=_SesionHtmlFalsa("<html></html>"),  # type: ignore[arg-type]
        )
        with CatalogoDirectoSupermercados(
            cliente=httpx.Client(transport=httpx.MockTransport(responder)),
            buscador_plaza_lama=plaza_lama,
        ) as catalogo:
            ofertas = catalogo.buscar_para_renglon({
                "descripcion_usuario": "LECHE EVAPORADA 15 OZ",
                "unidad_medida": "Unidad",
            })
        self.assertEqual(len(ofertas), 1)
        self.assertAlmostEqual(float(ofertas[0].monto), 85.81, places=2)
        self.assertIn("Presentación ajustada", ofertas[0].equivalencia or "")

    def test_compara_caja_con_24_unidades_de_presentacion_exacta(self) -> None:
        oferta = OfertaSupermercado(
            "Guandules Verdes Líder 15 Onz",
            "Jumbo",
            Decimal("89.95"),
            "DOP",
            "https://jumbo.com.do/guandules-verdes-lider-15-onz",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "GUANDULES DE CALIDAD CAJ/24 UND 15 ONZ",
                "unidad_medida": "Caja",
            },
            oferta,
        )

        self.assertEqual(precio, Decimal("2158.80"))

    def test_no_compara_aceite_16_oz_con_renglon_de_1_lb(self) -> None:
        oferta = OfertaSupermercado(
            "Crisol Aceite Soya 16 Oz",
            "La Sirena",
            Decimal("92.00"),
            "DOP",
            "https://nuevo.sirena.do/crisol-aceite-soya-16-oz/p",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "ACEITE CAJA DE 24 UND DE 1 LB",
                "unidad_medida": "Caja",
            },
            oferta,
        )

        self.assertIsNone(precio)

    def test_multiplica_caja_con_barra_por_48(self) -> None:
        oferta = OfertaSupermercado(
            "Atún en lata 5 oz",
            "Nacional",
            Decimal("10.00"),
            "DOP",
            "https://supermercadosnacional.com/atun",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "ATUN CAJA/48",
                "unidad_medida": "Caja",
            },
            oferta,
        )

        self.assertEqual(precio, Decimal("480.00"))

    def test_multiplica_caja_de_por_48(self) -> None:
        oferta = OfertaSupermercado(
            "Atún en lata 5 oz",
            "Nacional",
            Decimal("10.00"),
            "DOP",
            "https://supermercadosnacional.com/atun",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "ATUN CAJA DE 48",
                "unidad_medida": "Caja",
            },
            oferta,
        )

        self.assertEqual(precio, Decimal("480.00"))

    def test_multiplica_fardos_con_barra_y_de_por_24(self) -> None:
        oferta = OfertaSupermercado(
            "Atún en lata 5 oz",
            "Nacional",
            Decimal("10.00"),
            "DOP",
            "https://supermercadosnacional.com/atun",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "ATUN FARDOS/DE 24",
                "unidad_medida": "Fardo",
            },
            oferta,
        )

        self.assertEqual(precio, Decimal("240.00"))

    def test_multiplica_caja_con_barra_por_4(self) -> None:
        oferta = OfertaSupermercado(
            "Atún en lata 5 oz",
            "Nacional",
            Decimal("10.00"),
            "DOP",
            "https://supermercadosnacional.com/atun",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "ATUN CAJA/4",
                "unidad_medida": "Caja",
            },
            oferta,
        )

        self.assertEqual(precio, Decimal("40.00"))

    def test_reconoce_variantes_de_caja_y_fardo(self) -> None:
        casos = (
            ("ATUN CAJ/48", Decimal("480.00")),
            ("ATUN FARDO/24", Decimal("240.00")),
            ("ATUN FARDO DE 24", Decimal("240.00")),
        )
        for descripcion, esperado in casos:
            with self.subTest(descripcion=descripcion):
                oferta = OfertaSupermercado(
                    "Atún en lata 5 oz",
                    "Nacional",
                    Decimal("10.00"),
                    "DOP",
                    "https://supermercadosnacional.com/atun",
                    "catalogo_directo",
                )
                precio = CatalogoDirectoSupermercados._precio_equivalente(
                    {
                        "descripcion_usuario": descripcion,
                        "unidad_medida": "Caja",
                    },
                    oferta,
                )

                self.assertEqual(precio, esperado)

    def test_no_compara_caja_de_4_oz_con_aceite_de_galon(self) -> None:
        oferta = OfertaSupermercado(
            "Aceite 3.78 L",
            "Nacional",
            Decimal("500.00"),
            "DOP",
            "https://supermercadosnacional.com/aceite",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "ACEITE CAJA/4 OZ",
                "unidad_medida": "Caja",
            },
            oferta,
        )

        self.assertIsNone(precio)

    def test_descarta_adobo_sal_o_sazon_cuando_se_pide_pimienta(self) -> None:
        for titulo in (
            "Adobo Con Pimienta Goya",
            "Sal con Pimienta",
            "Sazón con Pimienta",
        ):
            with self.subTest(titulo=titulo):
                oferta = OfertaSupermercado(
                    titulo,
                    "Nacional",
                    Decimal("50.00"),
                    "DOP",
                    "https://supermercadosnacional.com/pimienta",
                    "catalogo_directo",
                )
                precio = CatalogoDirectoSupermercados._precio_equivalente(
                    {
                        "descripcion_usuario": "PIMIENTA LB",
                        "unidad_medida": "Unidad",
                    },
                    oferta,
                )

                self.assertIsNone(precio)

    def test_descarta_harina_de_maiz_para_harina_blanca(self) -> None:
        oferta = OfertaSupermercado(
            "Harina de Maíz 1 lb",
            "Nacional",
            Decimal("45.00"),
            "DOP",
            "https://supermercadosnacional.com/harina-maiz",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "HARINA BLANCA",
                "unidad_medida": "Unidad",
            },
            oferta,
        )

        self.assertIsNone(precio)

    def test_acepta_harina_de_trigo_para_harina_blanca(self) -> None:
        oferta = OfertaSupermercado(
            "Harina de Trigo 1 lb",
            "Nacional",
            Decimal("45.00"),
            "DOP",
            "https://supermercadosnacional.com/harina-trigo",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "HARINA BLANCA",
                "unidad_medida": "Unidad",
            },
            oferta,
        )

        self.assertEqual(precio, Decimal("45.00"))

    def test_no_multiplica_cantidad_total_en_unidad_suelta(self) -> None:
        oferta = OfertaSupermercado(
            "Arroz Selecto 1 lb",
            "Nacional",
            Decimal("45.00"),
            "DOP",
            "https://supermercadosnacional.com/arroz",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "ARROZ LB 8,250 UND", "unidad_medida": "Unidad"},
            oferta,
        )

        self.assertEqual(precio, Decimal("45.00"))

    def test_describe_lote_con_factor_de_empaque(self) -> None:
        oferta = OfertaSupermercado(
            "Atún en lata 5 oz",
            "Nacional",
            Decimal("10.00"),
            "DOP",
            "https://supermercadosnacional.com/atun",
            "catalogo_directo",
        )
        descripcion = CatalogoDirectoSupermercados.describir_equivalencia(
            {"descripcion_usuario": "ATUN CAJA/48", "unidad_medida": "Caja"},
            oferta,
        )

        self.assertIn("Lote de 48 unidades", descripcion)
        self.assertIn("×48", descripcion)
        self.assertIn("total lote vs. total lote", descripcion)

    def test_describe_unidad_suelta_sin_factor_artificial(self) -> None:
        oferta = OfertaSupermercado(
            "Arroz Selecto 1 lb",
            "Nacional",
            Decimal("45.00"),
            "DOP",
            "https://supermercadosnacional.com/arroz",
            "catalogo_directo",
        )
        articulo = {"descripcion_usuario": "ARROZ LB", "unidad_medida": "Libra"}

        precio = CatalogoDirectoSupermercados._precio_equivalente(articulo, oferta)
        descripcion = CatalogoDirectoSupermercados.describir_equivalencia(articulo, oferta)

        self.assertEqual(precio, Decimal("45.00"))
        self.assertIn("Comparación por libra", descripcion)
        self.assertNotIn("Lote", descripcion)

    def test_reconoce_bulto_con_cantidad_interna(self) -> None:
        oferta = OfertaSupermercado(
            "Atún en lata 5 oz",
            "Nacional",
            Decimal("10.00"),
            "DOP",
            "https://supermercadosnacional.com/atun",
            "catalogo_directo",
        )
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "ATUN BULTO DE 12", "unidad_medida": "Bulto"},
            oferta,
        )

        self.assertEqual(precio, Decimal("120.00"))

    def test_describe_equivalencia_de_presentacion_canela(self) -> None:
        oferta = OfertaSupermercado(
            "Canela entera 60 g",
            "Nacional",
            Decimal("59.95"),
            "DOP",
            "https://supermercadosnacional.com/canela",
            "catalogo_directo",
        )
        descripcion = CatalogoDirectoSupermercados.describir_equivalencia(
            {"descripcion_usuario": "CANELA SOBRE 2 ONZAS", "unidad_medida": "Unidad"},
            oferta,
        )

        self.assertIn("presentación equivalente", descripcion)
        self.assertIn("56.7 g", descripcion)
        self.assertIn("60 g", descripcion)


def _oferta(
    producto: str,
    precio: str,
    *,
    establecimiento: str = "Nacional",
) -> OfertaSupermercado:
    return OfertaSupermercado(
        producto,
        establecimiento,
        Decimal(precio),
        "DOP",
        f"https://supermercadosnacional.com/{producto.lower().replace(' ', '-')}",
        "catalogo_directo",
    )


class TestMotorUniversalEscenarios(unittest.TestCase):
    def test_escenario_a_escala_20_oz_contra_40_oz(self) -> None:
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "ACEITE 20 OZ", "unidad_medida": "Unidad"},
            _oferta("Aceite 40 Oz", "350.00"),
        )

        self.assertEqual(precio, Decimal("175.00"))

    def test_escenario_a_pinol_galon_escala_por_volumen_y_no_1_a_1(self) -> None:
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "PINOL GALON", "unidad_medida": "Galon"},
            _oferta("Pinol 828 ML", "134.95"),
        )

        self.assertIsNotNone(precio)
        self.assertGreater(precio, Decimal("600"))
        self.assertNotEqual(precio, Decimal("134.95"))

    def test_escenario_a_caja_de_4_galones_contra_frasco_pequeno_es_sin_referencia(self) -> None:
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "VAINILLA BLANCA GALON CAJA/4",
                "unidad_medida": "Caja",
            },
            _oferta("Vainilla Blanca 4 Oz", "100.00"),
        )

        self.assertIsNone(precio)

    def test_escenario_b_caja_anidada_12_paquetes_de_60(self) -> None:
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {
                "descripcion_usuario": "GALLETAS CAJ/12 PAQ DE 60 UND",
                "unidad_medida": "Caja",
            },
            _oferta("Galletas PAQ DE 60 UND", "100.00"),
        )

        self.assertEqual(precio, Decimal("1200.00"))

    def test_escenario_b_faldo_de_6_y_six_pack(self) -> None:
        casos = ("ATUN FALDO DE 6", "ATUN SIX PACK")
        for descripcion in casos:
            with self.subTest(descripcion=descripcion):
                precio = CatalogoDirectoSupermercados._precio_equivalente(
                    {"descripcion_usuario": descripcion, "unidad_medida": "Fardo"},
                    _oferta("Atún en lata 5 oz", "10.00"),
                )
                self.assertEqual(precio, Decimal("60.00"))

    def test_escenario_c_repollo_por_unidad_con_peso_aproximado(self) -> None:
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "REPOLLO MORADO", "unidad_medida": "Unidad"},
            _oferta("Repollo Morado Lb (Peso Aprox. 4 Libras)", "59.00"),
        )

        self.assertEqual(precio, Decimal("236.00"))

    def test_escenario_c_sandia_usa_peso_promedio_si_catalogo_es_por_libra(self) -> None:
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "SANDIA", "unidad_medida": "Unidad"},
            _oferta("Sandia Lb", "20.00"),
        )

        self.assertEqual(precio, Decimal("200.00"))

    def test_escenario_c_sandia_con_peso_aproximado_explicito(self) -> None:
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "SANDIA", "unidad_medida": "Unidad"},
            _oferta("Sandia (Peso Aprox. 10 Libras)", "200.00"),
        )

        self.assertEqual(precio, Decimal("200.00"))


class TestFiltroSemanticoEstricto(unittest.TestCase):
    def test_sandia_no_acepta_chicles_jugos_ni_dulces(self) -> None:
        for titulo in (
            "Chicle Sabor Sandia",
            "Goma de Mascar Sandia",
            "Jugo de Sandia",
            "Gelatina Sabor Sandia",
            "Caramelo de Sandia",
        ):
            with self.subTest(titulo=titulo):
                precio = CatalogoDirectoSupermercados._precio_equivalente(
                    {"descripcion_usuario": "SANDIA", "unidad_medida": "Unidad"},
                    _oferta(titulo, "50.00"),
                )
                self.assertIsNone(precio)

    def test_pasas_no_acepta_reposteria_ni_cereales(self) -> None:
        for titulo in (
            "Cupcake con Pasas",
            "Ponque con Pasas",
            "Galletas con Pasas",
            "Cereal con Pasas",
            "Helado de Pasas",
        ):
            with self.subTest(titulo=titulo):
                precio = CatalogoDirectoSupermercados._precio_equivalente(
                    {"descripcion_usuario": "PASAS", "unidad_medida": "Unidad"},
                    _oferta(titulo, "50.00"),
                )
                self.assertIsNone(precio)

    def test_pasas_reales_multiplican_el_lote(self) -> None:
        precio = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "PASAS 48 UND", "unidad_medida": "Unidad"},
            _oferta("Ligo Uvas Pasas 1 Oz", "34.00"),
        )

        self.assertEqual(precio, Decimal("1632.00"))

    def test_apio_no_acepta_cepa_de_apio_pero_si_celery(self) -> None:
        cepa = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "APIO", "unidad_medida": "Unidad"},
            _oferta("Cepa de Apio", "20.00"),
        )
        celery = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "APIO", "unidad_medida": "Unidad"},
            _oferta("Celery", "30.00"),
        )

        self.assertIsNone(cepa)
        self.assertEqual(celery, Decimal("30.00"))

    def test_palo_de_escoba_no_acepta_escoba_completa(self) -> None:
        completa = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "PALO DE ESCOBA", "unidad_medida": "Unidad"},
            _oferta("Escoba con Palo", "40.00"),
        )
        suelto = CatalogoDirectoSupermercados._precio_equivalente(
            {"descripcion_usuario": "PALO DE ESCOBA", "unidad_medida": "Unidad"},
            _oferta("Palo de Escoba", "40.00"),
        )

        self.assertIsNone(completa)
        self.assertEqual(suelto, Decimal("40.00"))

    def test_regla_general_de_prefijos_procesados(self) -> None:
        casos = (
            ("SANDIA", "Jugo de Sandia"),
            ("PASAS", "Galletas con Pasas"),
            ("PIMIENTA", "Adobo con Pimienta"),
            ("SANDIA", "Sabor a Sandia"),
            ("SANDIA", "Con Sabor a Sandia"),
        )
        for requerido, titulo in casos:
            with self.subTest(requerido=requerido, titulo=titulo):
                precio = CatalogoDirectoSupermercados._precio_equivalente(
                    {"descripcion_usuario": requerido, "unidad_medida": "Unidad"},
                    _oferta(titulo, "50.00"),
                )
                self.assertIsNone(precio)


if __name__ == "__main__":
    unittest.main()

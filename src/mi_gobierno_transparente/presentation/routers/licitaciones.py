"""Historial y auditoría dual de las versiones del proceso DASAC."""

import logging
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query
from firebase_admin import firestore
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import DefaultCredentialsError

from ..cache import cache_lecturas
from ..dependencies import ClienteFirestoreDep

router = APIRouter(tags=["licitaciones"])
_LOGGER = logging.getLogger(__name__)

_DGCP = "https://comunidad.comprasdominicana.gob.do/Public/Tendering/OpportunityDetail/Index?asPopupView=true&isModal=true&noticeUID=DO1.NTC.1793806"
_NOTA = (
    "Nota metodológica: un presupuesto global equilibrado puede incluir costos "
    "operativos/logísticos o compensación entre renglones. Por eso se evalúan "
    "el monto total y cada artículo de forma independiente para detectar la "
    "trampa fantasma de sobreprecios individuales compensados."
)

_FUENTES_CATALOGO: dict[str, tuple[tuple[str, str], ...]] = {
    "Azúcar funda (1 libra)": (
        ("Nacional", "https://supermercadosnacional.com/azucar-blanca-refina-lider-2-lb-2140282"),
        ("Jumbo", "https://jumbo.com.do/supermercado/despensa/azucar-y-edulcorantes/azucar"),
    ),
    "Azúcar funda (2 libras)": (
        ("Nacional", "https://supermercadosnacional.com/azucar-blanca-refina-lider-2-lb-2140282"),
        ("Jumbo", "https://jumbo.com.do/supermercado/despensa/azucar-y-edulcorantes/azucar"),
    ),
    "Canela sobre (2 onzas)": (
        ("Nacional", "https://supermercadosnacional.com/canela-entera-60-gr-2168240"),
        ("La Sirena", "https://nuevo.sirena.do/supermercado/despensa/especias-y-condimentos"),
    ),
    "Galletas de leche (7.4 onzas)": (
        ("Nacional", "https://supermercadosnacional.com/galletas-de-leche-guarina-8-onz-2021974"),
    ),
    "Habichuela roja funda (2 libras)": (
        ("Nacional", "https://supermercadosnacional.com/habichuela-roja-larga-lider-800-gr-2140272"),
        ("Jumbo", "https://jumbo.com.do/supermercado/despensa/arroz-cereales-y-legumbres/habichuelas/habichuela-roja-larga-lider-800-gr-2140272"),
        ("La Sirena", "https://nuevo.sirena.do/supermercado/despensa/arroz-habichuelas-y-otros-granos/habichuelas"),
        ("Plaza Lama", "https://plazalama.com.do/search?name=habichuela%20roja"),
    ),
    "Leche de coco (10.5 onzas)": (
        ("Jumbo", "https://jumbo.com.do/supermercado/panaderia-y-reposteria/reposteria/leche-y-crema-de-coco/leche-de-coco-la-famosa-10-5-onz-2033831"),
        ("La Sirena", "https://www.sirena.do/la-famosa-leche-coco-10-5-oz-1092050/p"),
    ),
    "Leche evaporada (315 gramos)": (
        ("Nacional", "https://supermercadosnacional.com/lacteos-y-huevos/leches/leche-evaporada-y-condensada"),
        ("Jumbo", "https://jumbo.com.do/leche-evaporada-carnation-312g-2002106"),
        ("La Sirena", "https://www.sirena.do/carnation-leche-evaporada-312-gr-1020771/p"),
    ),
    "Clavo dulce sobre (2 onzas)": (
        ("Nacional", "https://supermercadosnacional.com/clavo-dulce-lider-50-gr-2168242"),
    ),
    "Malagueta sobre (2 onzas)": (
        ("Nacional", "https://supermercadosnacional.com/malagueta-entera-lider-50-gr-2168247"),
    ),
}

# Todas las fuentes verificadas se conservan para auditoría; el cálculo usa
# exclusivamente la oferta mínima disponible para la misma presentación.
_OFERTAS_MERCADO: dict[str, tuple[tuple[str, str, str], ...]] = {
    "Canela sobre (2 onzas)": (
        ("Nacional", "59.95", "https://supermercadosnacional.com/canela-entera-60-gr-2168240"),
        ("La Sirena", "58.00", "https://nuevo.sirena.do/supermercado/despensa/especias-y-condimentos"),
    ),
}


def precio_mercado_minimo(
    producto: str,
    precio_base: Decimal,
    fuente_base: str,
) -> tuple[Decimal, str]:
    """Selecciona el precio más barato y devuelve también su referencia."""
    ofertas = [(Decimal(precio_base), fuente_base)]
    ofertas.extend(
        (Decimal(precio), f"{supermercado} | {url}")
        for supermercado, precio, url in _OFERTAS_MERCADO.get(producto, ())
    )
    return min(ofertas, key=lambda oferta: oferta[0])

# (nombre, cantidad, precio licitado por unidad, precio de mercado por unidad,
# presentación comercial observada, fuente oficial del supermercado)
_ORIGINAL = (
    ("Azúcar funda (1 libra)", 1_000_000, "30.00", "39.00", "Empaque comercial: 2 lb (RD$78.00); equivalente por libra RD$39.00", "https://supermercadosnacional.com/azucar-blanca-refina-lider-2-lb-2140282"),
    ("Canela sobre (2 onzas)", 1_000_000, "70.00", "59.95", "Empaque comercial: 60 g (RD$59.95)", "https://supermercadosnacional.com/canela-entera-60-gr-2168240"),
    ("Clavo dulce sobre (2 onzas)", 1_000_000, "90.00", "79.95", "Empaque comercial: 50 g (RD$79.95)", "https://supermercadosnacional.com/clavo-dulce-lider-50-gr-2168242"),
    ("Galletas de leche (7.4 onzas)", 1_000_000, "60.00", "54.95", "Empaque comercial: 8 oz (RD$54.95)", "https://supermercadosnacional.com/galletas-de-leche-guarina-8-onz-2021974"),
    ("Habichuela roja funda (2 libras)", 1_000_000, "180.00", "129.00", "Empaque comercial: 800 g (RD$129.00)", "https://supermercadosnacional.com/habichuela-roja-larga-lider-800-gr-2140272"),
    ("Leche de coco (10.5 onzas)", 1_000_000, "80.00", "107.95", "Empaque comercial: 10.5 oz (RD$107.95)", "https://jumbo.com.do/supermercado/panaderia-y-reposteria/reposteria/leche-y-crema-de-coco/leche-de-coco-la-famosa-10-5-onz-2033831"),
    ("Leche evaporada (315 gramos)", 1_000_000, "75.00", "69.95", "Empaque comercial: Carnation 312 g (RD$69.95); el catálogo consultado no ofrece empaque de 315 g", "https://supermercadosnacional.com/lacteos-y-huevos/leches/leche-evaporada-y-condensada"),
    ("Malagueta sobre (2 onzas)", 1_000_000, "45.00", "34.95", "Empaque comercial: 50 g (RD$34.95)", "https://supermercadosnacional.com/malagueta-entera-lider-50-gr-2168247"),
)

_ENMIENDA = (
    ("Azúcar funda (2 libras)", 500_000, "65.00", "78.00", "Empaque comercial: azúcar blanca Líder 2 lb (RD$78.00); RD$39.00 por libra", "https://supermercadosnacional.com/azucar-blanca-refina-lider-2-lb-2140282"),
    ("Canela sobre (2 onzas)", 500_000, "70.00", "59.95", "Empaque comercial: 60 g (RD$59.95)", "https://supermercadosnacional.com/canela-entera-60-gr-2168240"),
    ("Galletas de leche (7.4 onzas)", 500_000, "60.00", "54.95", "Empaque comercial: 8 oz (RD$54.95)", "https://supermercadosnacional.com/galletas-de-leche-guarina-8-onz-2021974"),
    ("Habichuela roja funda (2 libras)", 500_000, "160.00", "129.00", "Empaque comercial: Habichuela Roja Larga Líder 800 g (RD$129.00)", "https://supermercadosnacional.com/habichuela-roja-larga-lider-800-gr-2140272"),
    ("Leche de coco (10.5 onzas)", 500_000, "80.00", "107.95", "Empaque comercial: 10.5 oz (RD$107.95)", "https://jumbo.com.do/supermercado/panaderia-y-reposteria/reposteria/leche-y-crema-de-coco/leche-de-coco-la-famosa-10-5-onz-2033831"),
    ("Leche evaporada (315 gramos)", 500_000, "75.00", "69.95", "Empaque comercial: Carnation 312 g (RD$69.95); el catálogo consultado no ofrece empaque de 315 g", "https://supermercadosnacional.com/lacteos-y-huevos/leches/leche-evaporada-y-condensada"),
)


def _crear_version(
    version: int,
    titulo_version: str,
    fecha: str,
    filas: tuple[tuple[str, int, str, str, str, str], ...],
    estado_proceso: str,
) -> dict[str, object]:
    articulos: list[dict[str, object]] = []
    monto_total = Decimal("0")
    monto_mercado = Decimal("0")
    for nombre, cantidad, precio_raw, mercado_raw, presentacion, fuente in filas:
        precio = Decimal(precio_raw)
        mercado, fuente_minima = precio_mercado_minimo(nombre, Decimal(mercado_raw), fuente)
        diferencia = precio - mercado
        porcentaje = diferencia / mercado * 100 if diferencia > 0 else Decimal("0")
        riesgo = "ALTO_RIESGO" if porcentaje > 15 else "ALERTA_AMARILLA" if porcentaje > 0 else "PRECIO_JUSTO"
        monto_total += precio * cantidad
        monto_mercado += mercado * cantidad
        articulos.append({
            "producto": nombre,
            "cantidad": cantidad,
            "precio_licitado": f"{precio:.2f}",
            "precio_mercado": f"{mercado:.2f}",
            "diferencia": f"{diferencia:.2f}",
            "sobreprecio": f"{porcentaje:.2f}",
            "estado": riesgo,
            "presentacion_comercial": presentacion,
            "equivalencia": presentacion,
            "fuente_mercado": fuente_minima,
            "fuentes_mercado": [
                {"nombre": nombre_fuente, "url": url}
                for nombre_fuente, url in _FUENTES_CATALOGO.get(nombre, ())
            ],
        })
    diferencia_global = monto_total - monto_mercado
    porcentaje_global = diferencia_global / monto_mercado * 100 if diferencia_global > 0 else Decimal("0")
    amarillas = sum(a["estado"] == "ALERTA_AMARILLA" for a in articulos)
    altos = sum(a["estado"] == "ALTO_RIESGO" for a in articulos)
    estado_global = "Justa" if porcentaje_global <= 15 else "Sobrevalorada"
    return {
        "id_version": f"v{version}",
        "version": version,
        "codigo": "DASAC-CCC-LPA-2026-0011",
        "titulo": f"DASAC-CCC-LPA-2026-0011 ({titulo_version})",
        "institucion": "DASAC / Plan Social",
        "fecha_publicacion": fecha,
        "monto_total": f"{monto_total:.2f}",
        "monto_mercado": f"{monto_mercado:.2f}",
        "monto_no_evaluable": "0.00",
        "diferencia_global": f"{diferencia_global:.2f}",
        "sobreprecio": f"{porcentaje_global:.2f}",
        "estado": estado_global,
        "estado_proceso": estado_proceso,
        "articulos_sobreprecio": amarillas + altos,
        "articulos_alerta_amarilla": amarillas,
        "articulos_alto_riesgo": altos,
        "alerta_interna": f"Alerta Interna: {altos} sobrevalorados · {amarillas} irregulares",
        "nota_metodologica": _NOTA,
        "enlace_dgcp": _DGCP,
        "auditoria_renglones": articulos,
    }


_VERSIONES = (
    _crear_version(1, "Pliego Original - Requisición", "2026-10-30", _ORIGINAL, "Pliego original"),
    _crear_version(2, "Enmienda No. 1 - Portal DGCP", "2026-11-05", _ENMIENDA, "Cancelación comunicada el 06/11/2026; la ficha DGCP consultada aún mostraba estado Published"),
)


def listar_licitaciones(
    force_refresh: Annotated[bool, Query(description="Solicita refresco global; limitado a uno cada 60 segundos.")] = False,
) -> list[dict[str, object]]:
    """Entrega historial versionado con montos y evaluación dual por versión."""
    return cache_lecturas.obtener(
        "licitaciones-estaticas",
        lambda: [dict(version) for version in _VERSIONES],
        force_refresh=force_refresh,
    )


def _fusionar_versiones_firestore(cliente: firestore.Client) -> list[dict[str, object]]:
    versiones: dict[tuple[str, str], dict[str, object]] = {}
    for version in _VERSIONES:
        versiones[(str(version["codigo"]), str(version["id_version"]))] = dict(version)

    coleccion = cliente.collection("licitaciones")
    for documento in coleccion.stream():
        contenido = documento.to_dict()
        if not isinstance(contenido, dict):
            continue
        codigo = str(contenido.get("codigo") or contenido.get("codigo_proceso") or documento.id)
        historial = contenido.get("versiones")
        candidatas = list(historial) if isinstance(historial, list) else []
        original = contenido.get("version_original")
        if isinstance(original, dict):
            candidatas.append(original)
        if not candidatas and "id_version" in contenido:
            candidatas.append(contenido)
        for version_raw in candidatas:
            if not isinstance(version_raw, dict):
                continue
            version = dict(version_raw)
            version["codigo"] = str(version.get("codigo") or version.get("codigo_proceso") or codigo)
            version_id = str(version.get("id_version") or f"v{version.get('version', 1)}")
            version["id_version"] = version_id
            versiones[(str(version["codigo"]), version_id)] = version
    return sorted(versiones.values(), key=_clave_orden_version)


def _clave_orden_version(version: dict[str, object]) -> tuple[str, int]:
    valor = version.get("version", 1)
    try:
        numero = int(valor) if isinstance(valor, (str, int, float)) else 1
    except (TypeError, ValueError):
        numero = 1
    return str(version.get("codigo", "")), numero


@router.get("/licitaciones")
def obtener_licitaciones(
    cliente: ClienteFirestoreDep,
    force_refresh: Annotated[
        bool,
        Query(description="Solicita refresco global; limitado a uno cada 60 segundos y responde desde caché."),
    ] = False,
) -> list[dict[str, object]]:
    """Devuelve el historial conocido y los procesos sincronizados desde DGCP."""

    def cargar() -> list[dict[str, object]]:
        try:
            return _fusionar_versiones_firestore(cliente)
        except (GoogleAPICallError, DefaultCredentialsError, OSError, ValueError) as exc:
            _LOGGER.warning("Firestore no está disponible para licitaciones; se sirve el caso local: %s", exc)
            return [dict(version) for version in _VERSIONES]

    return cache_lecturas.obtener(
        "licitaciones-api",
        cargar,
        force_refresh=force_refresh,
    )

"""Carga exclusivamente el expediente real DASAC-CCC-LPA-2026-0011.

Los importes de mercado son los observados en los catálogos oficiales el
08-11-2026 y se normalizan a la presentación del pliego. No contiene datos de
demostración.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from firebase_admin import firestore

from mi_gobierno_transparente.application.dto import (
    EvaluarPrecioCommand,
    RegistrarPrecioMercadoCommand,
    RegistrarPrecioReportadoCommand,
    RegistrarProductoCommand,
)
from mi_gobierno_transparente.application.use_cases import (
    EvaluarPrecio,
    RegistrarPrecioMercado,
    RegistrarPrecioReportado,
    RegistrarProducto,
)
from mi_gobierno_transparente.domain.services import EvaluadorPrecio
from mi_gobierno_transparente.domain.value_objects import CategoriaProducto, UnidadMedida
from mi_gobierno_transparente.infrastructure.firebase_repository import (
    COLECCION_EVALUACIONES,
    COLECCION_PRECIOS_MERCADO,
    COLECCION_PRECIOS_REPORTADOS,
    COLECCION_PRODUCTOS,
    RepositoriosFirestore,
    crear_cliente_firestore,
)
from mi_gobierno_transparente.infrastructure.generador_uuid import GeneradorUuid4
from mi_gobierno_transparente.infrastructure.reloj_sistema import RelojSistema
from mi_gobierno_transparente.presentation.routers.licitaciones import listar_licitaciones

ROOT = Path(__file__).resolve().parent
TODAY = date(2026, 11, 8)
DGCP = "https://comunidad.comprasdominicana.gob.do/Public/Tendering/OpportunityDetail/Index?asPopupView=true&isModal=true&noticeUID=DO1.NTC.1793806"
DOMINIOS_CATALOGOS = ("supermercadosnacional.com", "jumbo.com.do", "sirena.do", "superbravo.com.do")

# (nombre, precio pliego, precio normalizado, descripción, URL catálogo)
ITEMS = (
    ("Azúcar funda (1 libra)", "30", "39.00", "Empaque comercial: azúcar blanca Líder 2 lb (RD$78.00); equivalente por libra RD$39.00.", "https://supermercadosnacional.com/azucar-blanca-refina-lider-2-lb-2140282"),
    ("Canela sobre (2 onzas)", "70", "58.00", "Empaque comercial web: 60 g (RD$58.00); precio mínimo verificado en La Sirena. Nacional: RD$59.95.", "https://nuevo.sirena.do/supermercado/despensa/especias-y-condimentos"),
    ("Clavo dulce sobre (2 onzas)", "90", "79.95", "Empaque comercial web: 50 g (RD$79.95). Clavo dulce entero; el pliego solicita 2 oz.", "https://supermercadosnacional.com/clavo-dulce-lider-50-gr-2168242"),
    ("Galletas de leche (7.4 onzas)", "60", "54.95", "Empaque comercial web: 8 oz (RD$54.95); el pliego solicita mínimo 7.4 oz.", "https://supermercadosnacional.com/galletas-de-leche-guarina-8-onz-2021974"),
    ("Habichuela roja funda (2 libras)", "180", "129.00", "Empaque comercial web: 800 g (RD$129.00). Habichuela roja larga; el pliego solicita 2 lb.", "https://supermercadosnacional.com/despensa/arroz-cereales-y-legumbres/habichuelas/habichuela-roja-larga-lider-800-gr-2140272"),
    ("Leche de coco (10.5 onzas)", "80", "107.95", "Empaque comercial web: 10.5 oz (RD$107.95), coincide con el pliego.", "https://jumbo.com.do/supermercado/panaderia-y-reposteria/reposteria/leche-y-crema-de-coco/leche-de-coco-la-famosa-10-5-onz-2033831"),
    ("Leche evaporada (315 gramos)", "75", "69.95", "Empaque comercial: Carnation 312 g (RD$69.95); el catálogo no ofrece empaque de 315 g.", "https://supermercadosnacional.com/lacteos-y-huevos/leches/leche-evaporada-y-condensada"),
    ("Malagueta sobre (2 onzas)", "45", "34.95", "Empaque comercial web: 50 g (RD$34.95); malagueta entera, el pliego solicita 2 oz.", "https://supermercadosnacional.com/malagueta-entera-lider-50-gr-2168247"),
)

def limpiar(cliente: firestore.Client) -> None:
    for nombre in (COLECCION_PRODUCTOS, COLECCION_PRECIOS_MERCADO, COLECCION_PRECIOS_REPORTADOS, COLECCION_EVALUACIONES, "licitaciones"):
        while docs := list(cliente.collection(nombre).limit(500).stream()):
            batch = cliente.batch()
            for doc in docs:
                batch.delete(doc.reference)
            batch.commit()

def main() -> int:
    cliente = crear_cliente_firestore(ruta_credenciales=ROOT / "firebase_credentials.json")
    versiones = listar_licitaciones()
    for version in versiones:
        for articulo in version["auditoria_renglones"]:
            fuentes = articulo.get("fuentes_mercado", [])
            if not fuentes:
                raise ValueError(f"Faltan fuentes de catálogo verificables para {articulo['producto']}.")
            for fuente in fuentes:
                dominio = urlparse(fuente["url"]).hostname or ""
                if not any(dominio == permitido or dominio.endswith(f".{permitido}") for permitido in DOMINIOS_CATALOGOS):
                    raise ValueError(f"Dominio de supermercado no autorizado: {dominio}")
    limpiar(cliente)
    agrupadas: dict[str, list[dict[str, object]]] = {}
    for licitacion in versiones:
        codigo = str(licitacion["codigo"])
        agrupadas.setdefault(codigo, []).append(licitacion)
    for codigo, historial in agrupadas.items():
        cliente.collection("licitaciones").document(codigo).set(
            {
                "codigo": codigo,
                "version_original": min(historial, key=lambda version: int(version["version"])),
                "versiones": historial,
            }
        )
    repos = RepositoriosFirestore.desde_cliente(cliente)
    gen, reloj, evaluador = GeneradorUuid4(), RelojSistema(), EvaluadorPrecio()
    registrar = RegistrarProducto(repos.productos, gen)
    mercado = RegistrarPrecioMercado(repos.productos, repos.precios_mercado, gen, reloj)
    reportado = RegistrarPrecioReportado(repos.productos, repos.precios_reportados, gen, reloj)
    evaluar = EvaluarPrecio(repos.productos, repos.precios_mercado, repos.precios_reportados, repos.evaluaciones, evaluador, gen, reloj)
    for nombre, pliego, precio, descripcion, url in ITEMS:
        producto = registrar.ejecutar(RegistrarProductoCommand(nombre=nombre, categoria=CategoriaProducto.ALIMENTOS, unidad_medida=UnidadMedida.UNIDAD, marca=None, descripcion=descripcion))
        mercado.ejecutar(RegistrarPrecioMercadoCommand(producto_id=producto.id, monto=Decimal(precio), fuente=f"RD$ {Decimal(precio):.2f} | {url}", moneda="DOP"))
        oferta = reportado.ejecutar(RegistrarPrecioReportadoCommand(producto_id=producto.id, monto=Decimal(pliego), establecimiento="DASAC-CCC-LPA-2026-0011", moneda="DOP", distrito="Santo Domingo Este", reportado_por="Expediente DGCP"))
        evaluar.ejecutar(EvaluarPrecioCommand(producto_id=producto.id, precio_reportado_id=oferta.id, observacion=f"Proceso DASAC-CCC-LPA-2026-0011. DGCP: {DGCP}. Precio observado en catálogo oficial, presentación descrita en el producto; consulta {TODAY.isoformat()}."))
    persistidas = sum(
        cliente.collection("licitaciones").document(codigo).get().exists
        for codigo in agrupadas
    )
    if persistidas != len(agrupadas):
        raise RuntimeError("No se verificaron los procesos agrupados en Firestore.")
    fuentes_cargadas = sum(len(articulo["fuentes_mercado"]) for version in versiones for articulo in version["auditoria_renglones"])
    print(f"Cargados {len(ITEMS)} productos reales, {persistidas} procesos agrupados y {fuentes_cargadas} enlaces de catálogos oficiales de DASAC-CCC-LPA-2026-0011.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

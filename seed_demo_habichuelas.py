"""Seed de demostración: 'Kits de Habichuelas con Dulce'.

El script conecta con Cloud Firestore usando ``firebase_credentials.json`` y
ejecuta el flujo completo de la arquitectura:

1. Registra cinco productos reales de alimentos.
2. Registra un precio de mercado de referencia por producto (Bravo, La Sirena,
   Nacional y Jumbo).
3. Registra el precio reportado en la licitación (con sobreprecios de 200 % a
   300 %, un caso de alerta amarilla del 10 % y un caso de precio justo).
4. Ejecuta ``EvaluarPrecio`` para cada caso y deja la evaluación persistida.

Uso:
    python seed_demo_habichuelas.py
    python seed_demo_habichuelas.py --limpiar

``--limpiar`` elimina los documentos de las cuatro colecciones del demo antes
de sembrar. Úselo solo en un entorno de demostración.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from firebase_admin import firestore

from mi_gobierno_transparente.application.dto import (
    CambiarEstadoProductoCommand,
    EvaluarPrecioCommand,
    ObtenerResumenRiesgoQuery,
    RegistrarPrecioMercadoCommand,
    RegistrarPrecioReportadoCommand,
    RegistrarProductoCommand,
)
from mi_gobierno_transparente.application.use_cases import (
    CambiarEstadoProducto,
    EvaluarPrecio,
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

MONEDA = "DOP"
RUTA_CREDENCIALES = Path(__file__).resolve().parent / "firebase_credentials.json"

_COLECCIONES_DEMO: tuple[str, ...] = (
    COLECCION_PRODUCTOS,
    COLECCION_PRECIOS_MERCADO,
    COLECCION_PRECIOS_REPORTADOS,
    COLECCION_EVALUACIONES,
)


@dataclass(frozen=True, slots=True)
class CasoDemo:
    """Datos completos de un producto y su evaluación de demostración."""

    nombre: str
    categoria: CategoriaProducto
    unidad_medida: UnidadMedida
    marca: str | None
    descripcion: str
    precio_mercado: Decimal
    fuente_mercado: str
    precio_reportado: Decimal
    establecimiento: str
    distrito: str
    reportado_por: str
    observacion: str


# Los importes son referencias de demostración en pesos dominicanos (DOP).
# Cada producto usa una fuente de mercado distinta para cubrir Bravo, La Sirena,
# Nacional y Jumbo. Los precios reportados simulan las ofertas de la licitación.
CASOS_DEMO: tuple[CasoDemo, ...] = (
    CasoDemo(
        nombre="Lata de Habichuelas Rojas 15oz",
        categoria=CategoriaProducto.ALIMENTOS,
        unidad_medida=UnidadMedida.UNIDAD,
        marca="Goya",
        descripcion=(
            "Habichuelas rojas enlatadas de 15 onzas para el kit de "
            "habichuelas con dulce."
        ),
        precio_mercado=Decimal("110.00"),
        fuente_mercado="Bravo (Santo Domingo)",
        precio_reportado=Decimal("330.00"),
        establecimiento="Licitación DGCP - Lote 1",
        distrito="Distrito Nacional",
        reportado_por="Comité de Compras DGCP",
        observacion="Sobreprecio del 200 % sobre el precio de mercado de referencia.",
    ),
    CasoDemo(
        nombre="Leche Evaporada 315g",
        categoria=CategoriaProducto.ALIMENTOS,
        unidad_medida=UnidadMedida.UNIDAD,
        marca="Carnation",
        descripcion=(
            "Leche evaporada de 315 gramos para el kit de habichuelas con dulce."
        ),
        precio_mercado=Decimal("95.00"),
        fuente_mercado="La Sirena (Santo Domingo)",
        precio_reportado=Decimal("380.00"),
        establecimiento="Licitación DGCP - Lote 2",
        distrito="Distrito Nacional",
        reportado_por="Comité de Compras DGCP",
        observacion="Sobreprecio del 300 % sobre el precio de mercado de referencia.",
    ),
    CasoDemo(
        nombre="Libra de Azúcar",
        categoria=CategoriaProducto.ALIMENTOS,
        unidad_medida=UnidadMedida.UNIDAD,
        marca="Central Romana",
        descripcion=(
            "Libra de azúcar (454 g) para endulzar el kit de habichuelas con dulce."
        ),
        precio_mercado=Decimal("50.00"),
        fuente_mercado="Nacional (Santo Domingo)",
        precio_reportado=Decimal("175.00"),
        establecimiento="Licitación DGCP - Lote 3",
        distrito="Distrito Nacional",
        reportado_por="Comité de Compras DGCP",
        observacion="Sobreprecio del 250 % sobre el precio de mercado de referencia.",
    ),
    CasoDemo(
        nombre="Caja de Pasas",
        categoria=CategoriaProducto.ALIMENTOS,
        unidad_medida=UnidadMedida.CAJA,
        marca="Sun-Maid",
        descripcion="Caja de pasas para el kit de habichuelas con dulce.",
        precio_mercado=Decimal("180.00"),
        fuente_mercado="Jumbo (Santo Domingo)",
        precio_reportado=Decimal("198.00"),
        establecimiento="Licitación DGCP - Lote 4",
        distrito="Distrito Nacional",
        reportado_por="Comité de Compras DGCP",
        observacion="Sobreprecio del 10 %: caso de alerta amarilla.",
    ),
    CasoDemo(
        nombre="Paquete de Galletas de Leche",
        categoria=CategoriaProducto.ALIMENTOS,
        unidad_medida=UnidadMedida.PAQUETE,
        marca="Guarina",
        descripcion="Paquete de galletas de leche para acompañar el kit.",
        precio_mercado=Decimal("75.00"),
        fuente_mercado="Bravo (Santo Domingo)",
        precio_reportado=Decimal("72.00"),
        establecimiento="Licitación DGCP - Lote 5",
        distrito="Distrito Nacional",
        reportado_por="Comité de Compras DGCP",
        observacion="Precio por debajo del mercado: caso de precio justo.",
    ),
)


def _configurar_salida_utf8() -> None:
    """Evita acentos corruptos en consolas Windows con code page heredado."""
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if callable(reconfigurar):
            try:
                reconfigurar(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _normalizar_nombre(nombre: str) -> str:
    return " ".join(nombre.split()).casefold()


def _formatear(monto: Decimal, moneda: str) -> str:
    simbolo = "RD$" if moneda == MONEDA else moneda
    return f"{simbolo} {monto:,.2f}"


def _limpiar_colecciones(cliente: firestore.Client) -> None:
    """Elimina los documentos de las colecciones del demo en lotes."""
    print("Limpiando colecciones del demo...")
    for nombre in _COLECCIONES_DEMO:
        coleccion = cliente.collection(nombre)
        eliminados = 0
        while True:
            documentos = list(coleccion.limit(500).stream())
            if not documentos:
                break
            lote = cliente.batch()
            for documento in documentos:
                lote.delete(documento.reference)
            lote.commit()
            eliminados += len(documentos)
        print(f"  {nombre}: {eliminados} documento(s) eliminado(s).")


def _obtener_o_registrar_producto(
    caso: CasoDemo,
    *,
    repositorios: RepositoriosFirestore,
    registrar_producto: RegistrarProducto,
    cambiar_estado: CambiarEstadoProducto,
) -> str:
    """Devuelve el ID del producto, registrándolo si aún no existe."""
    existente = repositorios.productos.obtener_por_nombre(
        _normalizar_nombre(caso.nombre)
    )
    if existente is not None:
        if not existente.activo:
            cambiar_estado.ejecutar(
                CambiarEstadoProductoCommand(
                    producto_id=existente.id,
                    activo=True,
                )
            )
            print(f"  Producto reactivado: {existente.nombre} ({existente.id})")
        else:
            print(f"  Producto existente: {existente.nombre} ({existente.id})")
        return existente.id

    producto = registrar_producto.ejecutar(
        RegistrarProductoCommand(
            nombre=caso.nombre,
            categoria=caso.categoria,
            unidad_medida=caso.unidad_medida,
            marca=caso.marca,
            descripcion=caso.descripcion,
        )
    )
    print(f"  Producto registrado: {producto.nombre} ({producto.id})")
    return producto.id


def ejecutar_seed(*, limpiar: bool = False) -> int:
    """Ejecuta el flujo completo del seed y devuelve el código de salida."""
    _configurar_salida_utf8()
    if not RUTA_CREDENCIALES.is_file():
        print(
            "Error: no se encontró firebase_credentials.json en "
            f"{RUTA_CREDENCIALES.parent}."
        )
        return 1

    print(f"Conectando a Firestore con {RUTA_CREDENCIALES.name}...")
    cliente = crear_cliente_firestore(ruta_credenciales=RUTA_CREDENCIALES)
    if limpiar:
        _limpiar_colecciones(cliente)

    repositorios = RepositoriosFirestore.desde_cliente(cliente)
    reloj = RelojSistema()
    generador = GeneradorUuid4()
    evaluador = EvaluadorPrecio()

    registrar_producto = RegistrarProducto(repositorios.productos, generador)
    cambiar_estado = CambiarEstadoProducto(repositorios.productos)
    registrar_mercado = RegistrarPrecioMercado(
        repositorios.productos,
        repositorios.precios_mercado,
        generador,
        reloj,
    )
    registrar_reportado = RegistrarPrecioReportado(
        repositorios.productos,
        repositorios.precios_reportados,
        generador,
        reloj,
    )
    evaluar_precio = EvaluarPrecio(
        repositorios.productos,
        repositorios.precios_mercado,
        repositorios.precios_reportados,
        repositorios.evaluaciones,
        evaluador,
        generador,
        reloj,
    )
    obtener_resumen = ObtenerResumenRiesgo(repositorios.evaluaciones)

    print(
        f"\nSembrando {len(CASOS_DEMO)} productos del caso "
        "'Kits de Habichuelas con Dulce'...\n"
    )

    for indice, caso in enumerate(CASOS_DEMO, start=1):
        print(f"[{indice}/{len(CASOS_DEMO)}] {caso.nombre}")
        producto_id = _obtener_o_registrar_producto(
            caso,
            repositorios=repositorios,
            registrar_producto=registrar_producto,
            cambiar_estado=cambiar_estado,
        )

        mercado = registrar_mercado.ejecutar(
            RegistrarPrecioMercadoCommand(
                producto_id=producto_id,
                monto=caso.precio_mercado,
                fuente=caso.fuente_mercado,
                moneda=MONEDA,
            )
        )
        reportado = registrar_reportado.ejecutar(
            RegistrarPrecioReportadoCommand(
                producto_id=producto_id,
                monto=caso.precio_reportado,
                establecimiento=caso.establecimiento,
                moneda=MONEDA,
                distrito=caso.distrito,
                reportado_por=caso.reportado_por,
            )
        )
        evaluacion = evaluar_precio.ejecutar(
            EvaluarPrecioCommand(
                producto_id=producto_id,
                precio_reportado_id=reportado.id,
                observacion=caso.observacion,
            )
        )

        print(
            "  Mercado   : "
            f"{_formatear(mercado.monto, mercado.moneda)} "
            f"({mercado.fuente})"
        )
        print(
            "  Reportado : "
            f"{_formatear(reportado.monto, reportado.moneda)} "
            f"({reportado.establecimiento})"
        )
        print(
            "  Resultado : "
            f"{evaluacion.nivel_riesgo.etiqueta} | "
            f"sobreprecio {evaluacion.sobreprecio_porcentaje:.2f} %"
        )
        print(f"  Evaluación guardada: {evaluacion.id}\n")

    resumen = obtener_resumen.ejecutar(ObtenerResumenRiesgoQuery())
    print("Resumen de riesgo")
    print(f"  Total de evaluaciones : {resumen.total_evaluaciones}")
    print(f"  Precio justo          : {resumen.precio_justo}")
    print(f"  Alerta amarilla       : {resumen.alerta_amarilla}")
    print(f"  Alto riesgo           : {resumen.alto_riesgo}")
    print(
        "  % de alto riesgo      : "
        f"{resumen.porcentaje_alto_riesgo:.2f} %"
    )
    print("\nSeed completado.")
    return 0


def main() -> int:
    """Punto de entrada del script."""
    parser = argparse.ArgumentParser(
        description=(
            "Siembra el caso de estudio 'Kits de Habichuelas con Dulce' en "
            "Firestore."
        )
    )
    parser.add_argument(
        "--limpiar",
        action="store_true",
        help=(
            "Elimina los documentos de las colecciones productos, "
            "precios_mercado, precios_reportados y evaluaciones antes de "
            "sembrar. Úselo solo en un entorno de demostración."
        ),
    )
    argumentos = parser.parse_args()
    return ejecutar_seed(limpiar=argumentos.limpiar)


if __name__ == "__main__":
    raise SystemExit(main())

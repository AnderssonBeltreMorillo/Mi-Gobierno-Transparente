"""Descubre y sincroniza procesos reales de alimentos y aseo publicados por DGCP.

Uso: ``python sync_licitaciones_dgcp.py``. Si ``DGCP_PROCESS_URLS`` está vacío,
se consultan automáticamente las páginas recientes de la API oficial de Datos
Abiertos. Los precios se aceptan solo desde enlaces directos de los cuatro
supermercados y en DOP; se elige el mínimo de las ofertas disponibles.
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, urlparse

from firebase_admin import firestore

from mi_gobierno_transparente.infrastructure.dgcp_scraper import DgcpOpenDataClient
from mi_gobierno_transparente.infrastructure.firebase_repository import crear_cliente_firestore
from mi_gobierno_transparente.infrastructure.gemini_market_evaluator import GeminiMarketEvaluator
from mi_gobierno_transparente.infrastructure.market_search_adapter import (
    CatalogoDirectoSupermercados,
    OfertaSupermercado,
    seleccionar_oferta_minima,
)
from mi_gobierno_transparente.presentation.config import cargar_configuracion

_HOST_DGCP = "comunidad.comprasdominicana.gob.do"
_PALABRAS_PROCESO = (
    "alimento", "despensa", "comedor", "raciones", "aseo", "limpieza",
    "higienico", "higiene", "supermercado", "comestible", "insumo alimenticio",
    "viveres", "canasta", "productos basicos", "material de limpieza",
    "productos de aseo", "articulos de higiene", "suministros de limpieza",
)
_PALABRAS_ASEO = (
    "cloro", "detergente", "desinfectante", "jabon", "papel higienico",
    "escoba", "trapeador", "limpiador", "fundas", "bolsas para basura",
)

_MOTOR_VERSION = "2026-11-escenarios-abc"


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto)
    return "".join(caracter for caracter in sin_tildes if unicodedata.category(caracter) != "Mn").casefold()


def _titulo_candidato(proceso: dict[str, object]) -> bool:
    texto = _normalizar(" ".join(str(proceso.get(campo, "")) for campo in ("titulo", "descripcion", "objeto_proceso")))
    return any(palabra in texto for palabra in _PALABRAS_PROCESO)


def _articulo_objetivo(articulo: dict[str, object]) -> bool:
    familia = re.sub(r"\D", "", str(articulo.get("familia_unspsc", "")))
    descripcion = _normalizar(" ".join(
        str(articulo.get(campo, ""))
        for campo in ("descripcion_usuario", "descripcion_articulo")
    ))
    return familia.startswith(("50", "47")) or any(palabra in descripcion for palabra in _PALABRAS_ASEO)


def _url_proceso(proceso: dict[str, object]) -> str:
    candidata = str(proceso.get("url", "")).strip()
    parsed = urlparse(candidata)
    if parsed.scheme == "https" and parsed.hostname == _HOST_DGCP and parsed.query:
        return candidata.replace("//Public/", "/Public/")
    return "https://datosabiertos.dgcp.gob.do/data-compras"


def _leer_filtros_manuales() -> tuple[list[str], list[str]]:
    codigos: list[str] = []
    notices: list[str] = []
    for valor in os.getenv("DGCP_PROCESS_URLS", "").split(","):
        valor = valor.strip()
        if not valor:
            continue
        parsed = urlparse(valor)
        if parsed.scheme in {"http", "https"}:
            if parsed.hostname != _HOST_DGCP:
                raise ValueError(f"La URL no pertenece al portal oficial de Compras Dominicanas: {valor}")
            notice = parse_qs(parsed.query).get("noticeUID", [""])[0]
            if not notice:
                raise ValueError(f"La ficha DGCP no incluye noticeUID: {valor}")
            notices.append(notice)
        else:
            codigos.append(valor)
    return codigos, notices


def _descubrir(
    api: DgcpOpenDataClient,
    *,
    desde: date,
    hasta: date,
    max_paginas: int,
    manuales: list[str],
    notice_uids: list[str],
) -> list[dict[str, object]]:
    if manuales:
        encontrados: list[dict[str, object]] = []
        for codigo in manuales:
            encontrados.extend(dict(proceso) for proceso in api.buscar_procesos(
                desde=desde, hasta=hasta, max_paginas=1, codigo=codigo,
            ))
        procesos = encontrados
    else:
        procesos = [
            dict(proceso)
            for proceso in api.buscar_procesos(desde=desde, hasta=hasta, max_paginas=max_paginas)
        ]
    if notice_uids:
        procesos = [
            proceso for proceso in procesos
            if any(uid in str(proceso.get("url", "")) for uid in notice_uids)
        ]
    unicos: dict[str, dict[str, object]] = {}
    for proceso in procesos:
        codigo = str(proceso.get("codigo_proceso", "")).strip()
        if codigo and _titulo_candidato(proceso):
            unicos[codigo] = proceso
    return list(unicos.values())


def _buscar_ofertas(
    buscador: CatalogoDirectoSupermercados,
    articulo: dict[str, object],
    evaluador_ia: GeminiMarketEvaluator | None = None,
) -> OfertaSupermercado | None:
    """Busca en el supermercado y pide a la IA que decida."""
    ofertas_crudas = buscador.buscar_ofertas_cadenas_verificadas(
        str(articulo.get("descripcion_usuario", "")), 
        limite=10
    )
    if not ofertas_crudas:
        return None
    if evaluador_ia:
        return evaluador_ia.seleccionar_oferta_correcta(articulo, ofertas_crudas)
    return seleccionar_oferta_minima(ofertas_crudas)


def evaluar_renglones(
    proceso: dict[str, object],
    articulos: list[dict[str, object]],
    buscador: CatalogoDirectoSupermercados,
    *,
    filtrar_objetivos: bool = True,
    monto_total_conocido: Decimal | None = None,
) -> dict[str, Any]:
    try:
        evaluador_ia = GeminiMarketEvaluator()
    except ValueError:
        print("Advertencia: No se configuró GEMINI_API_KEY. Usando fallback.")
        evaluador_ia = None

    filas: list[dict[str, object]] = []
    sin_referencia: list[dict[str, object]] = []
    monto_total = Decimal("0")
    monto_evaluable = Decimal("0")
    monto_mercado = Decimal("0")
    
    # 1. Recopilar todos los artículos objetivo y sus candidatos brutos
    articulos_objetivo = []
    for index, articulo in enumerate(articulos):
        if filtrar_objetivos and not _articulo_objetivo(articulo):
            continue
            
        ofertas_crudas = buscador.buscar_ofertas_cadenas_verificadas(
            str(articulo.get("descripcion_usuario", "")), 
            limite=10
        )
        
        articulos_objetivo.append({
            "id_interno": str(index),
            "datos_dgcp": articulo,
            "ofertas_crudas": ofertas_crudas
        })

    # 2. Dividir en bloques (Batching)
    TAMANO_BLOQUE = 15
    ofertas_validadas_global = {}

    try:
        if evaluador_ia:
            for i in range(0, len(articulos_objetivo), TAMANO_BLOQUE):
                bloque_actual = articulos_objetivo[i : i + TAMANO_BLOQUE]
                
                datos_para_ia = []
                for item in bloque_actual:
                    if not item["ofertas_crudas"]:
                        continue 
                        
                    datos_para_ia.append({
                        "id_articulo": item["id_interno"],
                        "producto_dgcp": item["datos_dgcp"].get("descripcion_usuario", ""),
                        "unidad_dgcp": item["datos_dgcp"].get("unidad_medida", "Unidad"),
                        "candidatos_mercado": [
                            {
                                "id": idx,
                                "producto_catalogo": o.producto,
                                "establecimiento": o.establecimiento,
                                "precio": float(o.monto),
                                "url": o.url
                            } for idx, o in enumerate(item["ofertas_crudas"])
                        ]
                    })

                if datos_para_ia:
                    print(f"Evaluando bloque de {len(datos_para_ia)} artículos con Gemini...")
                    resultados_bloque = evaluador_ia.evaluar_bloque(datos_para_ia)
                    
                    if resultados_bloque:
                         ofertas_validadas_global.update(resultados_bloque)
                    else:
                         print("Advertencia: Gemini devolvió un resultado vacío para este bloque. Usando evaluación local (fallback).")
                    
                    # Pausa incrementada a 60 segundos para evitar saturar la API
                    time.sleep(60)

        # 3. Procesar los resultados finales
        for item in articulos_objetivo:
            articulo = item["datos_dgcp"]
            cantidad = Decimal(str(articulo.get("cantidad") or 0))
            precio_estimado = Decimal(str(articulo.get("precio_unitario_estimado") or 0))
            total_estimado = Decimal(str(articulo.get("precio_total_estimado") or cantidad * precio_estimado))
            monto_total += total_estimado

            if not item["ofertas_crudas"]:
                sin_referencia.append(dict(articulo))
                continue

            oferta_validada = ofertas_validadas_global.get(item["id_interno"])
            if not oferta_validada:
                oferta_validada = seleccionar_oferta_minima(item["ofertas_crudas"])

            diferencia = precio_estimado - oferta_validada.monto
            porcentaje = diferencia / oferta_validada.monto * 100 if diferencia > 0 and oferta_validada.monto else Decimal("0")
            riesgo = "ALTO_RIESGO" if porcentaje > 15 else "ALERTA_AMARILLA" if porcentaje > 0 else "PRECIO_JUSTO"
            total_mercado = oferta_validada.monto * cantidad
            
            monto_evaluable += total_estimado
            monto_mercado += total_mercado
            unidad = str(articulo.get("unidad_medida") or "Unidad").strip() or "Unidad"
            
            filas.append({
                "producto": str(articulo.get("descripcion_usuario") or articulo.get("descripcion_articulo") or "Producto sin descripción"),
                "cantidad": int(cantidad),
                "precio_licitado": f"{precio_estimado:.2f}",
                "precio_mercado": f"{oferta_validada.monto:.2f}",
                "diferencia": f"{diferencia:.2f}",
                "sobreprecio": f"{porcentaje:.2f}",
                "estado": riesgo,
                "presentacion_comercial": f"{unidad} · Catálogo: {oferta_validada.producto}",
                "equivalencia": oferta_validada.equivalencia or "Evaluación local.",
                "fuente_mercado": f"{oferta_validada.establecimiento} | {oferta_validada.url or ''}".strip(),
                "fuentes_mercado": [
                    {"nombre": oferta_validada.establecimiento, "url": oferta_validada.url}
                ],
            })

        if monto_total_conocido is not None and monto_total_conocido > 0:
            monto_total = monto_total_conocido
        diferencia_global = monto_evaluable - monto_mercado
        sobreprecio_global = diferencia_global / monto_mercado * 100 if diferencia_global > 0 and monto_mercado else Decimal("0")
        evaluadas = bool(filas)
        estados = [str(fila["estado"]) for fila in filas]
        amarillas = estados.count("ALERTA_AMARILLA")
        altas = estados.count("ALTO_RIESGO")
        estado_global = "Justa" if evaluadas and sobreprecio_global <= 15 else "Sobrevalorada" if evaluadas else "Irregular"
        
        version = {
            "id_version": f"auto-{proceso.get('codigo_proceso', 'dgcp')}",
            "version": 1,
            "codigo": str(proceso.get("codigo_proceso", "")),
            "titulo": f"{proceso.get('codigo_proceso', '')} (Evaluación automática DGCP)",
            "institucion": str(proceso.get("unidad_compra", "Institución DGCP")),
            "fecha_publicacion": str(proceso.get("fecha_publicacion", "")),
            "monto_total": f"{monto_total:.2f}",
            "monto_mercado": f"{monto_mercado:.2f}",
            "monto_no_evaluable": f"{monto_total - monto_evaluable:.2f}",
            "diferencia_global": f"{diferencia_global:.2f}",
            "sobreprecio": f"{sobreprecio_global:.2f}",
            "estado": estado_global,
            "estado_proceso": str(proceso.get("estado_proceso", "Proceso publicado")),
            "articulos_sobreprecio": amarillas + altas,
            "articulos_alerta_amarilla": amarillas,
            "articulos_alto_riesgo": altas,
            "alerta_interna": f"Alerta Interna: {altas} sobrevalorados · {amarillas} irregulares",
            "nota_metodologica": "Solo se evalúan renglones con precios DOP y enlaces directos verificados de supermercados; la referencia es el menor precio observado.",
            "enlace_dgcp": _url_proceso(proceso),
            "motor_version": _MOTOR_VERSION,
            "auditoria_renglones": filas,
        }
        return {"version": version, "renglones_sin_referencia": sin_referencia}
        
    except Exception as e:
        print(f"Error crítico en evaluar_renglones: {e}")
        # Estructura de respaldo segura para evitar TypeError
        fallback_version = {
            "id_version": f"auto-{proceso.get('codigo_proceso', 'dgcp')}",
            "version": 1,
            "codigo": str(proceso.get("codigo_proceso", "")),
            "titulo": f"Error de evaluación",
            "estado": "Error",
            "auditoria_renglones": [],
        }
        return {"version": fallback_version, "renglones_sin_referencia": []}


def _guardar_agrupado(cliente: firestore.Client, proceso: dict[str, object], resultado: dict[str, Any]) -> None:
    codigo = str(proceso["codigo_proceso"])
    referencia = cliente.collection("licitaciones").document(codigo)
    existente = referencia.get()
    anterior: dict[str, Any] = existente.to_dict() or {} if existente.exists else {}
    versiones_raw = anterior.get("versiones", [])
    versiones = [dict(version) for version in versiones_raw if isinstance(version, dict)] if isinstance(versiones_raw, list) else []
    version = dict(resultado["version"])
    versiones = [actual for actual in versiones if actual.get("id_version") != version["id_version"]]
    versiones.append(version)
    version_original = anterior.get("version_original")
    if (
        not isinstance(version_original, dict)
        or version_original.get("id_version") == version.get("id_version")
    ):
        version_original = version
    referencia.set({
        "codigo": codigo,
        "version_original": version_original,
        "versiones": versiones,
        "proceso_dgcp": proceso,
        "renglones_sin_referencia": resultado["renglones_sin_referencia"],
        "sincronizado_en": datetime.now(UTC).isoformat(),
        "motor_version": _MOTOR_VERSION,
        "fuente_datos": "API oficial de Datos Abiertos DGCP",
    })


def _unidad_desde_fila(fila: Mapping[str, object]) -> str:
    unidad = str(fila.get("unidad_medida") or "").strip()
    if unidad:
        return unidad
    presentacion = str(fila.get("presentacion_comercial") or "")
    if " · " in presentacion:
        candidata = presentacion.split(" · ", 1)[0].strip()
        if candidata:
            return candidata
    return "Unidad"


def _articulos_desde_version(
    version: Mapping[str, object],
) -> list[dict[str, object]]:
    filas = version.get("auditoria_renglones")
    if not isinstance(filas, list):
        return []
    articulos: list[dict[str, object]] = []
    for fila in filas:
        if not isinstance(fila, Mapping):
            continue
        producto = str(fila.get("producto") or "").strip()
        if not producto:
            continue
        try:
            cantidad = Decimal(str(fila.get("cantidad") or 0))
            precio = Decimal(str(fila.get("precio_licitado") or 0))
        except (ArithmeticError, ValueError):
            continue
        articulo: dict[str, object] = {
            "descripcion_usuario": producto,
            "unidad_medida": _unidad_desde_fila(fila),
            "cantidad": (
                int(cantidad)
                if cantidad == cantidad.to_integral_value()
                else float(cantidad)
            ),
            "precio_unitario_estimado": str(precio),
            "precio_total_estimado": str(precio * cantidad),
        }
        if fila.get("familia_unspsc"):
            articulo["familia_unspsc"] = fila["familia_unspsc"]
        articulos.append(articulo)
    return articulos


def _proceso_desde_documento(
    contenido: Mapping[str, object],
    codigo: str,
) -> dict[str, object]:
    proceso_raw = contenido.get("proceso_dgcp")
    if isinstance(proceso_raw, Mapping):
        proceso = dict(proceso_raw)
        proceso.setdefault("codigo_proceso", codigo)
        return proceso
    versiones = contenido.get("versiones")
    candidatas = [
        version for version in versiones if isinstance(version, Mapping)
    ] if isinstance(versiones, list) else []
    original = contenido.get("version_original")
    if isinstance(original, Mapping):
        candidatas.append(original)
    primera = candidatas[0] if candidatas else {}
    return {
        "codigo_proceso": codigo,
        "fecha_publicacion": str(primera.get("fecha_publicacion") or ""),
        "unidad_compra": str(primera.get("institucion") or "Institución DGCP"),
        "estado_proceso": str(primera.get("estado_proceso") or "Proceso publicado"),
        "url": str(primera.get("enlace_dgcp") or ""),
    }


def _fusionar_version_recalculada(
    original: Mapping[str, object],
    calculada: Mapping[str, object],
) -> dict[str, object]:
    actualizada = dict(original)
    for campo in (
        "monto_total", "monto_mercado", "monto_no_evaluable",
        "diferencia_global", "sobreprecio", "estado",
        "articulos_sobreprecio", "articulos_alerta_amarilla",
        "articulos_alto_riesgo", "alerta_interna", "auditoria_renglones",
        "motor_version",
    ):
        if campo in calculada:
            actualizada[campo] = calculada[campo]
    return actualizada


def recalcular_documento(
    cliente: firestore.Client,
    buscador: CatalogoDirectoSupermercados,
    codigo: str,
    *,
    dry_run: bool = False,
) -> dict[str, object]:
    referencia = cliente.collection("licitaciones").document(codigo)
    documento = referencia.get()
    if not documento.exists:
        return {
            "codigo": codigo, "procesado": False, "actualizado": False,
            "motivo": "no existe", "versiones": 0, "renglones": 0,
            "sin_referencia": 0,
        }
    contenido = documento.to_dict() or {}
    if not isinstance(contenido, Mapping):
        return {
            "codigo": codigo, "procesado": False, "actualizado": False,
            "motivo": "documento inválido", "versiones": 0, "renglones": 0,
            "sin_referencia": 0,
        }

    proceso = _proceso_desde_documento(contenido, codigo)
    versiones_raw = contenido.get("versiones")
    versiones = [
        dict(version) for version in versiones_raw if isinstance(version, Mapping)
    ] if isinstance(versiones_raw, list) else []
    original = contenido.get("version_original")
    if isinstance(original, Mapping):
        ids = {str(version.get("id_version")) for version in versiones}
        if str(original.get("id_version")) not in ids:
            versiones.append(dict(original))
    if not versiones:
        return {
            "codigo": codigo, "procesado": False, "actualizado": False,
            "motivo": "sin versiones", "versiones": 0, "renglones": 0,
            "sin_referencia": 0,
        }

    nuevas: list[dict[str, object]] = []
    sin_referencia: list[dict[str, object]] = []
    total_renglones = 0
    for version in versiones:
        articulos = _articulos_desde_version(version)
        if not articulos:
            nuevas.append(version)
            continue
        try:
            total_conocido = Decimal(str(version.get("monto_total") or 0))
        except (ArithmeticError, ValueError):
            total_conocido = None
        resultado = evaluar_renglones(
            proceso,
            articulos,
            buscador,
            filtrar_objetivos=False,
            monto_total_conocido=(
                total_conocido if total_conocido and total_conocido > 0 else None
            ),
        )
        nuevas.append(_fusionar_version_recalculada(version, resultado["version"]))
        sin_referencia.extend(resultado["renglones_sin_referencia"])
        total_renglones += len(resultado["version"]["auditoria_renglones"])

    actualizado = dict(contenido)
    actualizado["codigo"] = codigo
    actualizado["versiones"] = nuevas
    if isinstance(contenido.get("version_original"), Mapping):
        original_id = str(contenido["version_original"].get("id_version"))
        actualizado["version_original"] = next(
            (
                version for version in nuevas
                if str(version.get("id_version")) == original_id
            ),
            contenido["version_original"],
        )
    actualizado["renglones_sin_referencia"] = sin_referencia
    actualizado["motor_version"] = _MOTOR_VERSION
    actualizado["recalculado_en"] = datetime.now(UTC).isoformat()
    if not dry_run:
        referencia.set(actualizado)
    return {
        "codigo": codigo,
        "procesado": True,
        "actualizado": not dry_run,
        "versiones": len(nuevas),
        "renglones": total_renglones,
        "sin_referencia": len(sin_referencia),
    }


def _procesos_nuevos(
   cliente: firestore.Client,
   procesos: list[dict[str, object]],
) -> list[dict[str, object]]:
   nuevos: list[dict[str, object]] = []
   for proceso in procesos:
       codigo = str(proceso.get("codigo_proceso", "")).strip()
       if not codigo:
           continue
       # ARREGLO: Verifica que no esté procesada ni en la lista de descartadas
       if not cliente.collection("licitaciones").document(codigo).get().exists and \
          not cliente.collection("licitaciones_descartadas").document(codigo).get().exists:
           nuevos.append(proceso)
   return nuevos


def _siguiente_pendiente(cliente: firestore.Client) -> str | None:
    for documento in cliente.collection("licitaciones").stream():
        contenido = documento.to_dict() or {}
        if not isinstance(contenido, Mapping):
            continue
        if str(contenido.get("motor_version") or "") != _MOTOR_VERSION:
            return documento.id
    return None


def _procesar_proceso(
   cliente: firestore.Client,
   buscador: CatalogoDirectoSupermercados,
   api: DgcpOpenDataClient,
   proceso: dict[str, object],
) -> bool:
   codigo = str(proceso.get("codigo_proceso", "")).strip()
   if not codigo:
       return False
   articulos = [
       dict(articulo) for articulo in api.obtener_articulos(codigo)
   ]
   if not any(_articulo_objetivo(articulo) for articulo in articulos):
       # ARREGLO: Registrarla como descartada para romper el bucle infinito
       cliente.collection("licitaciones_descartadas").document(codigo).set({
           "codigo": codigo,
           "motivo": "Sin artículos auditables en supermercado"
       })
       return False
   resultado = evaluar_renglones(proceso, articulos, buscador)
   _guardar_agrupado(cliente, proceso, resultado)
   version = resultado["version"]
   print(
       f"Sincronizado {codigo}: {len(version['auditoria_renglones'])} renglones "
       f"evaluados; {len(resultado['renglones_sin_referencia'])} sin precio de "
       f"supermercado. {version['enlace_dgcp']}"
   )
   return True


def main() -> int:
   hoy = date.today()
   dias = max(1, int(os.getenv("DGCP_LOOKBACK_DAYS", "120")))
   max_paginas = max(1, int(os.getenv("DGCP_MAX_PAGES", "20")))
   max_procesos = max(1, int(os.getenv("DGCP_MAX_PROCESSES", "50")))
   desde = hoy - timedelta(days=dias)
   api = DgcpOpenDataClient()
   manuales, notices = _leer_filtros_manuales()
   procesos = _descubrir(
       api,
       desde=desde,
       hasta=hoy,
       max_paginas=max_paginas,
       manuales=manuales,
       notice_uids=notices,
   )
   configuracion = cargar_configuracion()
   cliente = crear_cliente_firestore(
       project_id=configuracion.project_id,
       ruta_credenciales=configuracion.ruta_credenciales,
       credenciales_json=configuracion.credenciales_json,
       emulador_host=configuracion.emulador_host,
   )
   palabras_clave_permitidas = [
       "alimentos", "bebidas", "comida", "provisiones", "aseo",
       "limpieza", "detergente", "escoba", "trapeador", "cubeta", "supermercado"
   ]
   with CatalogoDirectoSupermercados() as buscador:
       nuevos = _procesos_nuevos(cliente, procesos)
       if nuevos:
           sincronizados = 0
           for proceso in nuevos:
               if sincronizados >= max_procesos:
                   break
               codigo = str(proceso.get("codigo_proceso", ""))
               texto_filtro = f"{proceso.get('titulo', '')} {proceso.get('descripcion', '')} {proceso.get('objeto_proceso', '')}".lower()
               if not any(palabra in texto_filtro for palabra in palabras_clave_permitidas):
                   # ARREGLO: Registrarla como descartada para que no la lea en el siguiente ciclo
                   cliente.collection("licitaciones_descartadas").document(codigo).set({
                       "codigo": codigo,
                       "motivo": "No cumple filtro de rubro"
                   })
                   continue
               if _procesar_proceso(cliente, buscador, api, proceso):
                   sincronizados += 1
           # ARREGLO: Si sincronizó algo válido, termina. Si todas fueron basura, que no se rinda y pase a pendientes.
           if sincronizados > 0:
               print(
                   f"Procesos DGCP nuevos agrupados en Firestore: {sincronizados} "
                   f"(ventana {desde.isoformat()}–{hoy.isoformat()})."
               )
               return 0
           else:
               print("Licitaciones recientes descartadas por no ser del rubro. Pasando a historial...")
       pendiente = _siguiente_pendiente(cliente)
       if pendiente:
           resumen = recalcular_documento(cliente, buscador, pendiente)
           print(
               f"Sin licitaciones nuevas; lote pendiente {pendiente} "
               f"recalculado: {resumen['renglones']} renglones, "
               f"{resumen['sin_referencia']} sin referencia."
           )
           return 0
   print(
       "Sin licitaciones nuevas ni lotes pendientes; se espera al siguiente "
       "ciclo de 2 horas."
   )
   return 0
if __name__ == "__main__":
   raise SystemExit(main())

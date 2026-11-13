"""Evaluador Semántico de Mercado en Lotes (Batch) usando Google Gemini API."""

from __future__ import annotations

import json
import os
import time
from decimal import Decimal
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError

from .market_search_adapter import OfertaSupermercado


class GeminiMarketEvaluator:
    """Delegado de IA para auditoría comercial por bloques (Batch Processing)."""

    def __init__(self, api_key: str | None = None) -> None:
        clave = api_key or os.getenv("GEMINI_API_KEY")
        if not clave:
            raise ValueError("GEMINI_API_KEY no encontrada.")
        self.client = genai.Client(api_key=clave)

    def evaluar_bloque(
        self,
        bloque_datos: list[dict[str, Any]],
        max_reintentos: int = 3
    ) -> dict[str, OfertaSupermercado]:
        """Envía un lote entero de productos a evaluar en 1 sola consulta a Gemini."""
        if not bloque_datos:
            return {}

        prompt = f"""
        Actúa como auditor experto en compras públicas de la República Dominicana.
        Tu tarea es emparejar estrictamente cada producto solicitado por la DGCP con su equivalente EXACTO en la lista de candidatos de los supermercados.

        REGLAS INQUEBRANTABLES DE AUDITORÍA:
        1. Identidad Estricta: El resultado debe ser exactamente el mismo producto. Rechaza mezclas incompatibles (ej. 'Café en grano' NO es 'Latte Frío'; 'Pimienta' NO es 'Pollo a la pimienta').
        2. Unidad de Medida (¡CRÍTICO!): Debes analizar el peso o volumen. Si la DGCP pide "Galón" (128 oz) y el supermercado ofrece "16 oz", debes calcular el `factor_multiplicador` exacto (128 / 16 = 8). Si no puedes establecer una proporción matemática lógica, RECHAZA la oferta devolviendo null.
        3. Falsos Positivos de Empaque: "Salsa de Tomate" en lata de 8 oz NO es lo mismo que en frasco de cristal de 16 oz. Elige la presentación comercial idéntica o más similar.
        4. Corrección de Digitación: Corrige errores obvios de la DGCP (ej. 'Habichuelas Rojas 2 Gramos' seguramente significa '2 Libras'). Aplica sentido común solo en errores de tipeo de la unidad.
        5. Preferencia al Ahorro Real: Si hay dos candidatos idénticos en volumen/peso y marca (o genéricos), elige siempre el de MENOR precio.

        DATOS A EVALUAR:
        {json.dumps(bloque_datos, indent=2, ensure_ascii=False)}

        DEVUELVE TU RESPUESTA EXACTAMENTE EN ESTE FORMATO JSON (Un array donde cada objeto corresponda al id_articulo enviado):
        [
          {{
            "id_articulo": "ID_DEL_ARTICULO",
            "id_oferta_elegida": (int con el id del candidato ganador, o null si ninguno sirve),
            "factor_multiplicador": (float, el factor a aplicar al precio del supermercado para igualar lo pedido por DGCP),
            "razonamiento": "Explicación breve de por qué coincide o por qué se calculó el factor"
          }}
        ]
        """

        intentos = 0
        while intentos < max_reintentos:
            try:
                response = self.client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0
                    ),
                )
                
                # Procesar la respuesta masiva
                resultados_ia = json.loads(response.text)
                ofertas_validadas = {}

                for res in resultados_ia:
                    id_articulo = res.get("id_articulo")
                    id_oferta = res.get("id_oferta_elegida")
                    
                    # Buscar los datos originales que enviamos para este artículo
                    datos_originales = next((d for d in bloque_datos if d["id_articulo"] == id_articulo), None)
                    
                    if datos_originales and id_oferta is not None and isinstance(id_oferta, int):
                        candidatos = datos_originales.get("candidatos_mercado", [])
                        if 0 <= id_oferta < len(candidatos):
                            candidato_elegido = candidatos[id_oferta]
                            factor = Decimal(str(res.get("factor_multiplicador", 1.0)))
                            
                            ofertas_validadas[id_articulo] = OfertaSupermercado(
                                producto=candidato_elegido["producto_catalogo"],
                                establecimiento=candidato_elegido["establecimiento"],
                                monto=Decimal(str(candidato_elegido["precio"])) * factor,
                                moneda="DOP",
                                url=candidato_elegido["url"],
                                fuente="gemini_batch",
                                equivalencia=f"Evaluado por IA: {res.get('razonamiento')}"
                            )
                
                return ofertas_validadas
                
            except APIError as e:
                if e.code in (429, 503):
                    intentos += 1
                    print(f"Alerta Gemini ({e.code}) procesando bloque. Reintentando en 15s... (Intento {intentos}/{max_reintentos})")
                    time.sleep(15) 
                else:
                    print(f"Error en Gemini API: {e}")
                    return {}
            except Exception as e:
                print(f"Error inesperado procesando bloque: {e}")
                return {}
                
        print("Se agotaron los reintentos para el bloque actual.")
        return {}
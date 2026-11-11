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
        Te enviaré un JSON con un lote de productos solicitados por el Estado y los posibles candidatos del supermercado para cada uno.

        INSTRUCCIONES DE EVALUACIÓN PARA CADA ITEM:
        1. Identidad: El resultado debe ser el mismo producto base. No cruces granos/especias con carnes, bebidas frías o snacks mixtos ('Pimienta' no es 'Pollo con Pimienta'; 'Café' no es 'Latte Frío').
        2. Proporción Lógica: Si piden Galón/Fardo, descarta onzas pequeñas.
        3. Falsos Positivos de Peso: Corrige errores obvios de digitación estatal (ej. 'Habichuelas Rojas 2 Gramos' seguramente significa '2 Libras').
        4. Factor: Si piden 'CAJA/48' y el supermercado vende unidad, factor=48. Si supermercado dice 'Aprox 5-7 unidades por libra' y piden 'LIBRA', factor=1 (ambos son libras).

        DATOS A EVALUAR:
        {json.dumps(bloque_datos, indent=2, ensure_ascii=False)}

        DEVUELVE TU RESPUESTA EXACTAMENTE EN ESTE FORMATO JSON (Un array donde cada objeto corresponda al id_articulo enviado):
        [
          {{
            "id_articulo": "ID_DEL_ARTICULO",
            "id_oferta_elegida": (int con el id del candidato ganador, o null si ninguno sirve),
            "factor_multiplicador": (float, el factor a aplicar al precio),
            "razonamiento": "explicación breve"
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
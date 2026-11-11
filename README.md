# Mi gobierno transparente — Backend

Demo funcional de transparencia de precios para productos de **alimentos** y
**aseo**. El backend está construido en Python con **programación orientada a
objetos**, **tipado estricto** y **arquitectura Onion**.

> **Estado actual:** capas `domain`, `application`, `infrastructure` y
> `presentation` implementadas. FastAPI expone productos, evaluaciones,
> resumen de riesgo e historial de licitaciones; el sincronizador DGCP detecta
> procesos publicados y los agrupa en Firestore por código de proceso.

---

## 1. Reglas de negocio

Solo se procesan productos de **alimentos** y **aseo**. Cualquier otra
categoría se rechaza con `CategoriaNoPermitidaError`.

La evaluación compara el precio reportado contra el precio de mercado vigente:

| Condición sobre el precio de mercado | Nivel de riesgo |
| --- | --- |
| Precio reportado **≤** precio de mercado (sobreprecio ≤ 0 %) | `PRECIO_JUSTO` |
| `0 % < sobreprecio < 1 %` | `PRECIO_JUSTO` (banda de tolerancia) |
| `1 % ≤ sobreprecio ≤ 15 %` | `ALERTA_AMARILLA` |
| `sobreprecio > 15 %` | `ALTO_RIESGO` |

### Decisión sobre el tramo (0 %, 1 %)

La regla original deja sin clasificar el intervalo `(0 %, 1 %)`. Para que
ningún precio quede sin categoría, ese tramo se trata como **tolerancia
operativa** y se reporta como `PRECIO_JUSTO` (el DTO expone
`dentro_de_tolerancia = true`). Los umbrales son configurables mediante
`UmbralesEvaluacion`; para una lectura estricta basta con usar
`alerta_amarilla_desde=Porcentaje.cero()`.

### Otras invariantes

- Los importes usan `Decimal`, nunca `float`, y se normalizan a dos decimales.
- Moneda por defecto: `PEN`. No se pueden comparar precios de monedas distintas.
- El precio de mercado debe ser mayor que cero.
- Un producto solo puede tener un precio de mercado vigente a la vez.
- Las evaluaciones son inmutables y guardan una foto de precios, sobreprecio,
  nivel de riesgo y umbrales aplicados (auditoría).
- Las fechas de precio no pueden ser futuras y las evaluaciones usan
  `datetime` con zona horaria.

---

## 2. Arquitectura Onion

```
┌──────────────────────────────────────────────────────────────┐
│ Presentación · Infraestructura                               │
│ FastAPI · CORS · Firestore · scraper DGCP · buscador         │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐   │
│   │ Aplicación                                           │   │
│   │ Casos de uso · DTOs · comandos/consultas · puertos   │   │
│   │                                                      │   │
│   │   ┌──────────────────────────────────────────────┐   │   │
│   │   │ Dominio                                      │   │   │
│   │   │ Entidades · Objetos de valor · Servicios     │   │   │
│   │   └──────────────────────────────────────────────┘   │   │
│   └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

Regla de dependencia: las flechas apuntan hacia adentro. El dominio no conoce
Firebase, HTTP, la base de datos ni la aplicación. La aplicación solo conoce el
dominio y sus propios puertos. La infraestructura implementa esos puertos.

### Decisiones de diseño

- **Entidades y objetos de valor inmutables** (`frozen=True, slots=True`): los
  cambios devuelven nuevas instancias.
- **Lenguaje ubicuo en español** para el modelo de negocio.
- **Servicio de dominio puro** (`EvaluadorPrecio`) para la regla de sobreprecio.
- **Puertos con ABCs** para inversión de dependencias.
- **Reloj y generador de IDs inyectables** para pruebas deterministas.
- **Sin lógica de negocio en los casos de uso**: solo orquestan y traducen
  errores de recursos.

---

## 3. Estructura del proyecto

```
Mi_Gobierno_Transparente/
├── pyproject.toml
├── README.md
├── seed_demo_habichuelas.py
├── src/
│   └── mi_gobierno_transparente/
│       ├── domain/
│       │   ├── entities/
│       │   │   ├── producto.py
│       │   │   ├── precio_mercado.py
│       │   │   ├── precio_reportado.py
│       │   │   └── evaluacion_precio.py
│       │   ├── value_objects/
│       │   │   ├── dinero.py
│       │   │   ├── porcentaje.py
│       │   │   ├── categoria_producto.py
│       │   │   ├── unidad_medida.py
│       │   │   ├── nivel_riesgo.py
│       │   │   ├── umbrales_evaluacion.py
│       │   │   └── resultado_evaluacion.py
│       │   ├── services/
│       │   │   └── evaluador_precio.py
│       │   └── exceptions.py
│       ├── application/
│       │   ├── ports/
│       │   │   ├── repositories.py
│       │   │   ├── reloj.py
│       │   │   └── generador_identificadores.py
│       │   ├── dto/
│       │   │   ├── commands.py
│       │   │   ├── queries.py
│       │   │   ├── producto_dto.py
│       │   │   ├── precio_mercado_dto.py
│       │   │   ├── precio_reportado_dto.py
│       │   │   ├── evaluacion_dto.py
│       │   │   └── resumen_riesgo_dto.py
│       │   ├── use_cases/
│       │   │   ├── registrar_producto.py
│       │   │   ├── registrar_precio_mercado.py
│       │   │   ├── registrar_precio_reportado.py
│       │   │   ├── evaluar_precio.py
│       │   │   ├── listar_evaluaciones.py
│       │   │   ├── obtener_resumen_riesgo.py
│       │   │   ├── obtener_producto.py
│       │   │   ├── listar_productos.py
│       │   │   └── cambiar_estado_producto.py
│       │   ├── exceptions.py
│       │   └── mappers.py
│       ├── infrastructure/
│       │   ├── firebase_repository.py
│       │   ├── firestore_documents.py
│       │   ├── reloj_sistema.py
│       │   ├── generador_uuid.py
│       │   ├── dgcp_scraper.py
│       │   ├── market_search_adapter.py
│       │   ├── parsing.py
│       │   ├── html_utils.py
│       │   └── exceptions.py
│       └── presentation/
│           ├── app.py
│           ├── config.py
│           ├── dependencies.py
│           ├── errors.py
│           ├── schemas.py
│           └── routers/
│               ├── productos.py
│               ├── evaluaciones.py
│               └── resumen_riesgo.py
└── tests/
    └── unit/
        ├── domain/
        ├── application/
        ├── infrastructure/
        └── presentation/
```

---

## 4. Modelo de dominio

| Elemento | Responsabilidad |
| --- | --- |
| `Producto` | Producto permitido (alimentos/aseo), unidad de medida y estado. |
| `PrecioMercado` | Precio de referencia con fuente y fecha; único vigente por producto. |
| `PrecioReportado` | Precio observado en un establecimiento, con distrito y autor. |
| `EvaluacionPrecio` | Auditoría inmutable de una comparación. |
| `Dinero` | Importe en `Decimal` con moneda ISO 4217 y operaciones seguras. |
| `Porcentaje` | Fracción decimal con formato y comparaciones. |
| `CategoriaProducto` | Catálogo y validación de categorías procesables. |
| `UnidadMedida` | Unidades soportadas (`kg`, `L`, `und`, etc.). |
| `NivelRiesgo` | `PRECIO_JUSTO`, `ALERTA_AMARILLA`, `ALTO_RIESGO`. |
| `UmbralesEvaluacion` | Umbrales configurables y clasificación. |
| `ResultadoEvaluacion` | Resultado autoconsistente (precios, excedente, sobreprecio, nivel). |
| `EvaluadorPrecio` | Servicio puro que calcula el sobreprecio y el nivel. |

---

## 5. Puertos (interfaces abstractas)

| Puerto | Contrato |
| --- | --- |
| `ProductoRepositorio` | CRUD, búsqueda por nombre normalizado, listado y conteo. |
| `PrecioMercadoRepositorio` | Guardado, reemplazo atómico del vigente, consulta del vigente. |
| `PrecioReportadoRepositorio` | Guardado y listado por producto/rango de fechas. |
| `EvaluacionPrecioRepositorio` | Guardado, listado filtrado y resumen por nivel. |
| `Reloj` | Instante actual con zona horaria. |
| `GeneradorIdentificadores` | IDs únicos (UUID, ULID o IDs de Firestore). |

La capa `infrastructure` implementa estas ABCs con Firestore. Los casos de uso
no importan ningún SDK de Firebase.

---

## 6. Infraestructura

### Firestore

`firebase_repository.py` contiene:

- `ProductoRepositorioFirestore`
- `PrecioMercadoRepositorioFirestore`
- `PrecioReportadoRepositorioFirestore`
- `EvaluacionPrecioRepositorioFirestore`
- `RepositoriosFirestore`, que agrupa los cuatro adaptadores con un mismo
  cliente.
- `crear_cliente_firestore(...)`, que inicializa `firebase-admin` una sola vez y
  permite usar el emulador con `emulador_host`.

Colecciones y esquema:

| Colección | ID del documento | Campos principales |
| --- | --- | --- |
| `productos` | `Producto.id` | `nombre`, `nombre_normalizado`, `categoria`, `unidad_medida`, `activo` |
| `precios_mercado` | `PrecioMercado.id` | `producto_id`, `precio`, `fuente`, `fecha_registro`, `vigente` |
| `precios_reportados` | `PrecioReportado.id` | `producto_id`, `precio`, `establecimiento`, `fecha_reporte` |
| `evaluaciones` | `EvaluacionPrecio.id` | `producto_id`, `resultado`, `evaluado_en`, `version_regla` |

Los importes se guardan como `{ "monto": "4.50", "moneda": "PEN" }` (texto, no
`float`) y las fechas sin hora como ISO `YYYY-MM-DD`. `reemplazar_vigente` usa
una transacción para desactivar el precio anterior y guardar el nuevo.

Índices recomendados en Firestore:

- `precios_mercado`: `producto_id ASC`, `vigente ASC`, `fecha_registro DESC`.
- `precios_reportados`: `producto_id ASC`, `fecha_reporte DESC`.
- `evaluaciones`: `producto_id ASC`, `evaluado_en DESC`;
  `resultado.nivel_riesgo ASC`, `evaluado_en DESC`; y
  `producto_id ASC`, `resultado.nivel_riesgo ASC`, `evaluado_en DESC`.

`ProductoRepositorioFirestore.listar` usa solo filtros de igualdad y ordena en
memoria, por lo que no requiere índices compuestos para `productos`. Si el
catálogo crece mucho, conviene mover el orden y la paginación a Firestore y
crear el índice `activo ASC`, `nombre_normalizado ASC` (y su variante con
`categoria ASC`).

### Reloj e identificadores

- `RelojSistema` implementa `Reloj` con `datetime.now(timezone.utc)`.
- `GeneradorUuid4` implementa `GeneradorIdentificadores` con `uuid4` en formato
  canónico (36 caracteres), seguro para usarlo como ID de documento.

### Extracción y búsqueda

- `DgcpScraper` usa `requests` + `BeautifulSoup` con selectores CSS
  configurables. `extraer_de_html` permite probar el parseo sin red.
- `SerpApiBuscadorSupermercados` consulta SerpApi (Google Shopping) y normaliza
  las ofertas. La clave se toma de `SERPAPI_API_KEY` o del argumento `api_key`.
- `DgcpOpenDataClient` pagina la API oficial de Datos Abiertos (`/procesos` y
  `/procesos/articulos`) para descubrir procedimientos y sus renglones.
- `CatalogoDirectoSupermercados` consulta sin clave de pago la búsqueda Magento
  de Nacional/Jumbo, el endpoint público VTEX de La Sirena y la tabla pública
  de precios al costo de Bravo. Solo conserva coincidencias verificables de
  nombre/presentación y escoge el menor precio DOP.
- `sync_licitaciones_dgcp.py` busca automáticamente los procesos de alimentos
  y aseo en los últimos 120 días si `DGCP_PROCESS_URLS` no está configurada;
  opcionalmente admite códigos de proceso o fichas oficiales para limitar la
  búsqueda. Guarda el historial agrupado por código en `licitaciones`.
- El sincronizador no requiere `SERPAPI_API_KEY`: si un catálogo directo está
  indisponible o no hay coincidencia exacta, ese renglón queda no evaluable.
  No se extrapolan ni se inventan precios.

```powershell
python sync_licitaciones_dgcp.py
```

```python
from mi_gobierno_transparente.infrastructure.firebase_repository import (
    RepositoriosFirestore,
    crear_cliente_firestore,
)

cliente = crear_cliente_firestore(project_id="mi-gobierno-transparente")
repos = RepositoriosFirestore.desde_cliente(cliente)
```

---

## 7. API HTTP (FastAPI)

La capa `presentation` construye la aplicación con `crear_app()` y expone:

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/productos` | Lista productos. Filtros: `categoria`, `incluir_inactivos`, `limite`, `desplazamiento`. |
| `GET` | `/evaluaciones` | Lista evaluaciones con `nivel_riesgo`. Filtros: `producto_id`, `nivel_riesgo`, `desde`, `hasta`, `limite`, `desplazamiento`. |
| `GET` | `/resumen-riesgo` | Devuelve el `ResumenRiesgoDTO` general; admite `producto_id`. |
| `GET` | `/licitaciones` | Historial versionado local más los procesos agrupados sincronizados en Firestore. Acepta `force_refresh=true`. |
| `GET` | `/health` | Liveness; no consulta Firestore. |

Los endpoints de lectura usan caché en memoria de 5 minutos y stale-while-
revalidate. `force_refresh=true` solicita una recarga, pero el servidor acepta
como máximo una recarga forzada real cada 60 segundos globalmente.

Arranque:

```powershell
uvicorn mi_gobierno_transparente.presentation.app:app --reload --port 8000
```

Documentación interactiva: `http://localhost:8000/docs`.

### CORS

`CORSMiddleware` permite por defecto `http://localhost:3000` y
`http://localhost:5173` (React/Vite). Para otros orígenes:

```powershell
$env:CORS_ORIGINS = "https://mi-frontend.example.com,http://localhost:5173"
```

Si se usa `*`, la API desactiva `allow_credentials` automáticamente.

### Configuración

| Variable | Uso |
| --- | --- |
| `FIREBASE_CREDENTIALS` | Ruta al JSON de servicio. Si no se define, se usa `firebase_credentials.json` del directorio actual. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Alternativa estándar de ADC. |
| `FIREBASE_PROJECT_ID` | Project ID explícito (opcional). |
| `FIRESTORE_EMULATOR_HOST` | Host del emulador de Firestore (opcional). |
| `DGCP_PROCESS_URLS` | Filtro opcional de códigos o URLs oficiales. Vacío activa el descubrimiento automático. |
| `DGCP_LOOKBACK_DAYS` | Ventana de publicación consultada; por defecto `120`. |
| `DGCP_MAX_PAGES` | Máximo de páginas DGCP a recorrer; por defecto `20`. |
| `DGCP_MAX_PROCESSES` | Máximo de procesos a sincronizar por ejecución; por defecto `3`. |
| `ENABLE_BACKGROUND_SYNC` | Activa el ciclo automático cada `7200` segundos. Por defecto `false`; en Render se define `true`. |

El ciclo de 2 horas primero busca licitaciones nuevas en la DGCP; si no hay
nuevas, recalcula un lote pendiente del historial; si todo está analizado, no
hace nada y espera al siguiente ciclo.

Para recalcular únicamente los expedientes ya guardados, sin consultar la DGCP:

```powershell
python recalcular_existentes.py
```

Use `python recalcular_existentes.py --dry-run` para ver el resultado sin
escribir en Firestore.

La conexión a Firestore es perezosa: el proceso arranca y `/health` responde
aunque el backend aún no esté disponible. Los errores se traducen a un cuerpo
uniforme `{"error": {"codigo": "...", "mensaje": "..."}}` con estados `400`,
`404`, `409`, `422`, `502` o `503`.

---

## 8. Seed de demostración

`seed_demo_habichuelas.py` siembra el caso "Kits de Habichuelas con Dulce" en
Firestore:

```powershell
python seed_demo_habichuelas.py
# Limpia las cuatro colecciones del demo antes de sembrar:
python seed_demo_habichuelas.py --limpiar
```

El seed registra 5 productos de alimentos, precios de mercado de referencia en
DOP (Bravo, La Sirena, Nacional y Jumbo), precios reportados de la licitación y
ejecuta `EvaluarPrecio` para cada uno. Incluye tres casos de alto riesgo
(200 %, 250 % y 300 %), un caso de alerta amarilla (10 %) y un caso de precio
justo. Al final imprime el resumen de riesgo persistido.

> Ejecutar el seed repetidamente reutiliza los productos existentes y agrega
> nuevas fotos de precios y evaluaciones. Use `--limpiar` para una demo limpia.

---

## 9. Casos de uso

- `RegistrarProducto`: crea productos de alimentos/aseo y evita duplicados.
- `RegistrarPrecioMercado`: registra la referencia y reemplaza la vigente.
- `RegistrarPrecioReportado`: registra el precio de un establecimiento.
- `EvaluarPrecio`: compara contra el mercado vigente y persiste la evaluación.
- `ListarEvaluaciones`: filtra por producto, nivel de riesgo y fechas.
- `ObtenerResumenRiesgo`: agrega conteos para el tablero.
- `ObtenerProducto` / `ListarProductos`: consultas de catálogo.
- `CambiarEstadoProducto`: activa o desactiva sin borrar el histórico.

### Ejemplo de composición

```python
from decimal import Decimal

from mi_gobierno_transparente.application.dto import EvaluarPrecioCommand
from mi_gobierno_transparente.application.use_cases import EvaluarPrecio
from mi_gobierno_transparente.domain.services import EvaluadorPrecio

evaluar_precio = EvaluarPrecio(
    productos=producto_repositorio,
    precios_mercado=precio_mercado_repositorio,
    precios_reportados=precio_reportado_repositorio,
    evaluaciones=evaluacion_repositorio,
    evaluador=EvaluadorPrecio(),
    generador_id=generador_identificadores,
    reloj=reloj,
)

resultado = evaluar_precio.ejecutar(
    EvaluarPrecioCommand(
        producto_id="prod-123",
        precio_reportado_id="rep-456",
    )
)
print(resultado.nivel_riesgo.value, resultado.sobreprecio_porcentaje)
```

---

## 10. Ejecutar pruebas y verificación de tipos

Las pruebas usan `unittest` de la biblioteca estándar y también son compatibles
con pytest:

```powershell
python -m unittest discover -s tests -t . -v
# o, si se instala el extra de desarrollo:
python -m pytest
```

Verificación estricta de tipos (configurada en `pyproject.toml`):

```powershell
$env:PYTHONPATH = "src"
python -m mypy src
```

Resultado actual: **94 pruebas pytest** (`90` por `unittest discover`),
`ruff check` limpio y **mypy strict sin errores** en 68 archivos fuente.

---

## 11. Próximos pasos

1. Añadir autenticación y autorización para reportes ciudadanos.
2. Incorporar observabilidad (logs estructurados, métricas, trazas).
3. Añadir pruebas de integración contra el emulador de Firestore.
4. Programar una tarea periódica de Render para ejecutar el sincronizador DGCP.
5. Crear los índices compuestos documentados en el proyecto de Firestore.

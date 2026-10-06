# Sniplyze

Herramienta SEO en local construida sobre la **API v3 de DataForSEO** con tus propias credenciales.
Backend en FastAPI e interfaz web incluida (sin compilación). Sin scraping: todos los datos salen de DataForSEO.

## Funciones

| Área | Función | Endpoint de DataForSEO |
|---|---|---|
| Keywords | Volumen, CPC, competencia y tendencia | `keywords_data/google_ads/search_volume/live` |
| | Keywords relacionadas | `dataforseo_labs/google/related_keywords/live` |
| | Sugerencias long tail | `dataforseo_labs/google/keyword_suggestions/live` |
| | Dificultad (KD) | `dataforseo_labs/google/bulk_keyword_difficulty/live` |
| | Intención de búsqueda | `dataforseo_labs/google/search_intent/live` |
| Dominio | Visión general (tráfico, keywords, posiciones) | `dataforseo_labs/google/domain_rank_overview/live` |
| | Keywords posicionadas | `dataforseo_labs/google/ranked_keywords/live` |
| | Competidores orgánicos | `dataforseo_labs/google/competitors_domain/live` |
| | Keyword gap entre dos dominios | `dataforseo_labs/google/domain_intersection/live` |
| | Páginas principales | `dataforseo_labs/google/relevant_pages/live` |
| | Evolución histórica | `dataforseo_labs/google/historical_rank_overview/live` |
| | Tráfico de varios dominios | `dataforseo_labs/google/bulk_traffic_estimation/live` |
| Backlinks | Resumen, listado, dominios de referencia, anclas | `backlinks/{summary,backlinks,referring_domains,anchors}/live` |
| SERP | Resultados orgánicos de Google y comprobación de posición | `serp/google/organic/live/advanced` |
| Auditoría | Rastreo del sitio tipo Screaming Frog: resumen, páginas, enlaces rotos, recursos con error, titles/descriptions duplicados, redirecciones, no indexables | `on_page/task_post`, `on_page/summary/{id}`, `on_page/pages`, `on_page/links`, `on_page/resources`, `on_page/duplicate_tags`, `on_page/redirect_chains`, `on_page/non_indexable` |
| | Análisis instantáneo de una URL | `on_page/instant_pages` |
| | Lighthouse (rendimiento, SEO, accesibilidad) | `on_page/lighthouse/live/json` |
| Cuenta | Saldo | `appendix/user_data` |

Por defecto: España (`location_code` 2724) y español (`language_code` "es"); se puede cambiar en la interfaz.
Todas las tablas se pueden ordenar y exportar a CSV.

> Backlinks requiere tener activa la suscripción de Backlinks en DataForSEO. Si no lo está, la API
> devuelve un error y la app lo muestra tal cual.

## Puesta en marcha

Requiere Python 3.11 o superior.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # y rellena DATAFORSEO_LOGIN y DATAFORSEO_PASSWORD
uvicorn app.main:create_app --factory --reload
```

- Interfaz: http://127.0.0.1:8000
- Documentación interactiva de la API: http://127.0.0.1:8000/docs

Las credenciales (login y contraseña **de API**, no los de la web) están en https://app.dataforseo.com/api-access.
Solo se leen de variables de entorno o de `.env`, que está en `.gitignore`.

## Control de gasto

- **Coste real:** cada llamada guarda el `cost` que devuelve DataForSEO. Lo ves en cada resultado
  y en *Cuenta → Costes y caché* (total, por día, por endpoint y últimas llamadas).
- **Confirmación antes de gastar:** antes de llamar se estima el coste a partir del historial
  (mayor coste por unidad observado × unidades pedidas: keywords, resultados, páginas de SERP o
  páginas a rastrear). Si la estimación supera `COST_CONFIRM_THRESHOLD` (0,50 $ por defecto), la
  app pide confirmación. La estimación es conservadora y orientativa.
- **Primera llamada a cada endpoint:** su coste aún no se conoce, así que se pide confirmación
  (`CONFIRM_UNKNOWN_COST=true`). Desde la segunda ya hay estimación.
- **Tope diario opcional:** `DAILY_BUDGET` bloquea cualquier consulta que lo superaría, aunque se confirme.
- **Validación previa:** las keywords se limpian y deduplican (máx. 80 caracteres y 10 palabras;
  sin emojis) y se limita su número por petición. Los dominios se normalizan
  (`https://www.Ejemplo.com/x` → `ejemplo.com`). Las entradas inválidas se rechazan sin llamar a la API.
- **Caché local (SQLite en `data/`):** la misma consulta no se paga dos veces. Duración: keywords
  30 días, dominios y backlinks 7 días, SERP, URL y Lighthouse 1 día. Los rastreos no se cachean.
  Se puede vaciar desde la interfaz.
- **Reintentos:** solo uno y solo si la petición no llegó a enviarse o la API respondió 429/502/503/504.
  Ante un timeout no se reintenta, porque la consulta pudo cobrarse.

En la API REST, una consulta que necesita confirmación responde **HTTP 402** con
`{"error": "confirmation_required", "estimated_cost": ..., "threshold": ...}`; para lanzarla se repite
con `?confirm=true`.

## Datos ausentes

Si DataForSEO no devuelve un campo, la app lo deja en `null` y la interfaz muestra la celda vacía.
Nunca se rellenan huecos con valores inventados.

## Arquitectura

```
app/
  main.py                     FastAPI (create_app) + interfaz estática
  config.py                   configuración desde entorno/.env
  deps.py                     construcción de dependencias
  core/                       caché, costes, validación, base de datos, errores (sin dependencia del proveedor)
  providers/base.py           contrato SEOProvider que usa la app
  providers/dataforseo/
    client.py                 HTTP, autenticación, caché, control de gasto, errores
    provider.py               endpoints, parámetros y unidades de coste
    mappers.py                traducción de respuestas → estructuras propias
  routers/                    rutas REST (/api/...)
  static/                     interfaz web (HTML + JS sin dependencias)
tests/                        tests con DataForSEO simulado
```

Los nombres de campo de DataForSEO solo aparecen en `providers/dataforseo/`. Para cambiar de
proveedor basta con implementar `SEOProvider`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Los tests usan un transporte HTTP simulado y `pytest-socket` bloquea cualquier conexión de red:
**ningún test puede llamar a la API real ni gastar crédito**.

## Pendiente de confirmar con la primera llamada real

La integración se ha escrito contra la especificación OpenAPI oficial de DataForSEO (cliente
`dataforseo-client` 2.1.8). Al no haber hecho aún llamadas reales, conviene confirmar:

- Que los códigos de éxito son 2xxxx (20000 OK, 20100 tarea creada).
- Los valores de `type` en `on_page/duplicate_tags` (`duplicate_title`, `duplicate_description`) y
  los filtros usados en enlaces rotos (`is_broken`) y recursos con error (`status_code >= 400`).
- Las traducciones de las comprobaciones On-Page (`CHECK_LABELS` en `mappers.py`): la clave
  original de DataForSEO se muestra siempre junto a la traducción.

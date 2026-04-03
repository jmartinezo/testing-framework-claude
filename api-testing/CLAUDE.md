# CLAUDE.md — api-testing

## Descripción del proyecto

Repositorio de testing de APIs REST. Cubre validación de contrato OpenAPI,
tests funcionales CRUD y tests de rendimiento bajo carga.

Este repo es el primero en ejecutarse en el pipeline general. Su salida principal
es un artefacto JSON con los datos de estado creados vía API, que el repo
`ui-testing` consume para ejecutar los tests de Playwright.

---

## Stack

| Capa | Herramienta | Propósito |
|---|---|---|
| Contrato / Schema | Schemathesis 4.x | Validación automática OpenAPI |
| Funcional / CRUD | pytest + requests | Tests de API funcionales |
| Carga | k6 | Load testing y performance thresholds |
| Reporting | Allure | Resultados y análisis de fallos |
| CI/CD | GitHub Actions | Ejecución continua |
| Lenguaje | Python 3.11+ | Lenguaje principal |

---

## Estructura

```
api-testing/
├── CLAUDE.md
├── pyproject.toml                # Dependencias y configuración pytest
├── .env.example                  # Variables de entorno requeridas
├── config/
│   └── schemathesis.toml         # Perfiles de ejecución de Schemathesis
├── hooks/
│   └── hooks.py                  # Hooks personalizados Schemathesis
├── mcp/
│   └── schemathesis-mcp/
│       └── server.py             # Servidor MCP — herramientas para Claude Code
├── tests/
│   ├── conftest.py               # Fixtures compartidas
│   ├── schema/                   # Tests de contrato OpenAPI
│   ├── crud/                     # Tests funcionales por recurso
│   └── load/                     # Scripts k6
├── data/
│   ├── fixtures/                 # Datos de entrada estáticos
│   └── output/                   # Datos generados — consumidos por ui-testing
│       └── test-state.json       # Artefacto compartido con ui-testing
├── schemathesis-report/          # Reportes ndjson generados por Schemathesis 4.x
│   └── ndjson-<timestamp>.ndjson # Un fichero por ejecución — leído por get_last_failures
└── reports/
    ├── allure-results/           # Salida JSON para Allure
    └── run-history.json          # Historial de runs (últimos 50) — leído por analyze_trends
```

---

## Variables de entorno

Nunca hardcodear valores de entorno en el código. Usar siempre `.env` local
o secrets de GitHub Actions.

```bash
BASE_URL=https://tu-api.com        # URL base de la API bajo prueba
API_KEY=...                        # Credenciales si aplica
ENV=staging                        # Entorno: local | staging | production
```

---

## Comandos habituales

### Schemathesis

```bash
# Validación rápida del schema
st run $BASE_URL/openapi.json --checks all

# Con perfil definido en config/
python scripts/run_tests.py --fast
python scripts/run_tests.py --schema
python scripts/run_tests.py --report
```

### pytest

```bash
# Todos los tests
pytest tests/

# Solo contrato
pytest tests/schema/ -v

# Solo CRUD
pytest tests/crud/ -v

# Con reporte Allure
pytest tests/ --alluredir=reports/allure-results
```

### k6

```bash
# Ejecutar script de carga
k6 run tests/load/load.js --env BASE_URL=$BASE_URL

# Con salida JSON para análisis
k6 run tests/load/load.js --out json=reports/k6-summary.json
```

### Allure

```bash
allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report
```

---

## Convenciones

### Naming

- Tests de schema: `test_schema_<endpoint>_<método>.py`
- Tests CRUD: `test_crud_<recurso>_<operación>.py`
- Scripts k6: `<recurso>_load.js`

### Comentarios

- Comentarios inline en **español**
- Nombres de funciones y variables en **inglés**

### Fixtures y datos

- Fixtures compartidas en `tests/conftest.py`
- Datos de entrada estáticos en `data/fixtures/`
- El estado generado durante los tests se escribe en `data/output/test-state.json`
- Este fichero es el artefacto que GitHub Actions pasa a `ui-testing`

---

## Hooks personalizados (`hooks/hooks.py`)

| Hook | Propósito |
|---|---|
| `filter_invalid_ids` | Restringe IDs al rango válido del endpoint |
| `detect_slow_response` | Fallo si la respuesta supera el umbral configurado |
| `check_embedded_errors` | Detecta errores JSON en respuestas 200 OK |

---

## Thresholds de rendimiento

Configurados en `config/schemathesis.toml` y en los scripts k6:

- P95 < 500ms
- Error rate < 1%
- Respuestas > umbral configurable → warning en hooks

---

## Pipeline GitHub Actions

Jobs definidos en `.github/workflows/test.yml`:

| Job | Herramienta | Trigger |
|---|---|---|
| `schema-tests` | Schemathesis | push / PR |
| `crud-tests` | pytest + requests | push / PR |
| `load-tests` | k6 | push a main |

Al finalizar, el job `export-state` sube `data/output/test-state.json`
como artefacto de GitHub Actions para que `ui-testing` lo consuma.

---

## MCP Servers conectados

| Server | Propósito |
|---|---|
| `schemathesis-mcp` | Ejecutar tests, leer fallos, analizar resultados |
| `xray-export-mcp` | Generar casos de prueba CSV desde historias de usuario |

```bash
# Registrar en Claude Code
claude mcp add --transport stdio schemathesis-mcp -- python mcp/schemathesis-mcp/server.py
claude mcp add --transport stdio xray-export-mcp -- python mcp/xray_server.py
```

### Herramientas de `schemathesis-mcp`

#### `run_tests`

Ejecuta Schemathesis contra una API. Invoca el binario `st` del entorno virtual
(no `python -m schemathesis`, que no existe en 4.x). Genera un fichero ndjson en
`schemathesis-report/` y guarda el historial en `reports/run-history.json`.

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `profile` | str | — | `fast` · `schema` · `full` |
| `base_url` | str | `$BASE_URL` | URL base de la API |
| `openapi_path` | str | `/openapi.json` | Ruta del spec relativa a `base_url` |
| `spec_url` | str | `""` | URL absoluta del spec (prioridad sobre `base_url+openapi_path`). URLs de GitHub blob se convierten automáticamente a `raw.githubusercontent.com`. Cuando se indica, se pasa `--url base_url` a Schemathesis |
| `auth` | str | `""` | HTTP Basic en formato `user:password` — equivale a `--auth` |
| `headers` | list[str] | `null` | Cabeceras extra en formato `"Nombre: valor"`. Usar para tokens y cookies, p.ej. `["Cookie: token=abc123"]` |

Perfiles definidos en `server.py`:

| Perfil | Checks | Ejemplos |
|---|---|---|
| `fast` | `not_a_server_error` | 10 |
| `schema` | `all` | 50 |
| `full` | `all` + stateful links | 200 |

#### `get_last_failures`

Lee el fichero `ndjson-*.ndjson` más reciente de `schemathesis-report/` y extrae
los eventos `ScenarioFinished` con `status: "failure"`, deduplicados por
`phase:label`. Devuelve cada fallo con su fase (Coverage, Fuzzing, Stateful) y
el endpoint afectado.

#### `list_coverage`

Acepta los mismos parámetros `base_url`, `openapi_path` y `spec_url` que
`run_tests`. Carga el spec con `schemathesis.openapi.from_url()` (API 4.x —
`schemathesis.from_uri()` no existe en 4.x) y cruza los endpoints con los fallos
del último ndjson para mostrar qué pasa y qué falla.

#### `analyze_trends`

Lee `reports/run-history.json` (hasta 50 runs) y calcula tasa de éxito y
comparativa respecto al run anterior.

---

## Notas para Claude

- Usar siempre la API de **Schemathesis 4.x** — breaking changes respecto a 3.x.
- El CLI de Schemathesis 4.x es `st run`, no `python -m schemathesis run`.
- La API Python de Schemathesis 4.x es `schemathesis.openapi.from_url()`, no `schemathesis.from_uri()`.
- `--report` en 4.x acepta un **formato** (`ndjson`, `junit`, `vcr`, `har`, `allure`), no una ruta de fichero.
- Los reportes ndjson se escriben en `schemathesis-report/ndjson-<timestamp>.ndjson` — directorio gestionado por Schemathesis automáticamente.
- Los scripts k6 usan **ES6 modules** (`import`), no CommonJS.
- Allure espera resultados en `reports/allure-results/` — no cambiar esta ruta.
- `BASE_URL` siempre viene de variable de entorno — nunca hardcodeada.
- El fichero `data/output/test-state.json` es crítico — es el contrato con `ui-testing`.
- Este repo no tiene nada de TypeScript ni Node — es Python puro.

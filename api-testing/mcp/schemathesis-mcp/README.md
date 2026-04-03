# schemathesis-mcp

Servidor MCP para Schemathesis. Permite a Claude Code ejecutar tests de contrato
OpenAPI, leer fallos, analizar tendencias y listar cobertura de endpoints —
todo desde lenguaje natural.

---

## Instalación

```bash
# Clonar o copiar la carpeta mcp/ dentro de api-testing
cd /Users/jorgemartinezortega/Desktop/testing/claude/api-testing

# Instalar dependencias
pip install mcp schemathesis

# O instalar como paquete editable
pip install -e mcp/schemathesis-mcp/
```

---

## Registrar en Claude Code

```bash
claude mcp add --transport stdio schemathesis-mcp \
  -- python /Users/jorgemartinezortega/Desktop/testing/claude/api-testing/mcp/schemathesis-mcp/server.py
```

Para verificar que está registrado:

```bash
claude mcp list
```

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `BASE_URL` | URL base de la API bajo prueba | `https://api.ejemplo.com` |
| `API_TESTING_ROOT` | Ruta raíz del proyecto api-testing | `/Users/jorge/.../api-testing` |

Puedes definirlas en un `.env` en la raíz de `api-testing` o exportarlas en tu shell.

---

## Herramientas disponibles

### `run_tests`
Ejecuta Schemathesis con el perfil indicado.

```
Perfiles:
  fast    → smoke test, 10 ejemplos por endpoint
  schema  → validación completa, 50 ejemplos
  full    → exhaustivo + stateful, 200 ejemplos
```

**Ejemplo en Claude Code:**
> "Ejecuta los tests con el perfil fast contra https://api.ejemplo.com"

---

### `get_last_failures`
Devuelve los fallos del último run: endpoint, método, código de respuesta,
check fallido y el ejemplo que lo provocó.

**Ejemplo en Claude Code:**
> "¿Qué endpoints fallaron en el último run?"

---

### `analyze_trends`
Analiza el historial de runs y devuelve:
- Tasa de éxito de los últimos N runs
- Endpoints más inestables
- Comparativa último run vs anterior

**Ejemplo en Claude Code:**
> "Analiza las tendencias de los últimos 10 runs"

---

### `list_coverage`
Lista todos los endpoints del spec OpenAPI con su estado:
- ✅ Sin fallos en el último run
- ❌ Con fallos en el último run

**Ejemplo en Claude Code:**
> "¿Qué endpoints no están cubiertos o han fallado?"

---

## Estructura de ficheros generados

```
api-testing/
└── reports/
    ├── schemathesis-results.json   # Resultado del último run
    └── run-history.json            # Historial de runs (máx. 50)
```

---

## Uso desde Claude Code

Una vez registrado el servidor, abre Claude Code en el proyecto:

```bash
cd /Users/jorgemartinezortega/Desktop/testing/claude/api-testing
claude
```

Y usa lenguaje natural:

```
"Ejecuta los tests con perfil schema contra https://api.ejemplo.com/openapi.json"
"¿Cuáles fueron los fallos del último run?"
"Analiza las tendencias de los últimos 5 runs"
"Lista todos los endpoints y dime cuáles han fallado"
```

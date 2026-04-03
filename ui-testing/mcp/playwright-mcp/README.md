# playwright-mcp

Servidor MCP para Playwright. Permite a Claude Code ejecutar tests de UI,
leer fallos, analizar tendencias por suite y abrir el reporte HTML —
todo desde lenguaje natural.

---

## Instalación

```bash
cd /Users/jorgemartinezortega/Desktop/testing/claude/ui-testing

# El servidor usa Python y el venv de api-testing (comparten mcp)
# Si quieres un venv propio:
python3 -m venv venv-mcp
source venv-mcp/bin/activate
pip install mcp
```

---

## Registrar en Claude Code

```bash
claude mcp add --transport stdio playwright-mcp \
  -- python3 /Users/jorgemartinezortega/Desktop/testing/claude/ui-testing/mcp/playwright-mcp/server.py
```

Verificar:

```bash
claude mcp list
```

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `BASE_URL` | URL base de la aplicación bajo prueba | `https://tu-app.com` |
| `UI_TESTING_ROOT` | Ruta raíz del proyecto ui-testing | `/Users/jorge/.../ui-testing` |

---

## Herramientas disponibles

### `run_tests`
Ejecuta Playwright con la suite y navegador indicados.

```
Suites:   smoke | e2e | regression | all
Browsers: chromium | firefox | webkit | all
```

Ejemplo en Claude Code:
> "Ejecuta los smoke tests en chromium contra https://mi-app.com"

---

### `get_last_failures`
Devuelve los fallos del último run con su contexto de error.

Ejemplo en Claude Code:
> "¿Qué tests fallaron en el último run?"

---

### `analyze_results`
Analiza el historial de runs por suite y navegador.

Ejemplo en Claude Code:
> "Analiza los resultados de los últimos 10 runs"

---

### `open_report`
Abre el reporte HTML de Playwright en el navegador.

Ejemplo en Claude Code:
> "Abre el reporte del último run"

---

## Uso desde Claude Code

```bash
cd /Users/jorgemartinezortega/Desktop/testing/claude/ui-testing
claude
```

Ejemplos de uso:
```
"Ejecuta los smoke tests en chromium"
"¿Qué tests fallaron en el último run?"
"Analiza los resultados de los últimos 5 runs"
"Abre el reporte HTML"
```

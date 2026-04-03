"""
Servidor MCP para Playwright.
Expone herramientas para ejecutar tests, leer fallos, analizar resultados
por suite y abrir el reporte HTML — consumibles desde Claude Code.

Compatible con mcp >= 1.0.0 (FastMCP API).
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from mcp.server import FastMCP

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(os.getenv("UI_TESTING_ROOT", Path(__file__).parent.parent.parent))
REPORTS_DIR = PROJECT_ROOT / "reports"
PLAYWRIGHT_REPORT = REPORTS_DIR / "playwright-report"
ALLURE_RESULTS = REPORTS_DIR / "allure-results"
TEST_RESULTS = REPORTS_DIR / "test-results"
HISTORY_FILE = REPORTS_DIR / "pw-run-history.json"

# Suites disponibles
SUITES = {
    "smoke": "tests/smoke/",
    "e2e": "tests/e2e/",
    "regression": "tests/regression/",
    "all": "tests/",
}

# Navegadores disponibles
BROWSERS = ["chromium", "firefox", "webkit", "all"]

mcp = FastMCP("playwright-mcp")


# ---------------------------------------------------------------------------
# Herramientas
# ---------------------------------------------------------------------------

@mcp.tool()
def run_tests(
    suite: str = "smoke",
    browser: str = "chromium",
    headed: bool = False,
    base_url: str = "",
) -> str:
    """
    Ejecuta tests de Playwright.

    Args:
        suite: Suite a ejecutar — 'smoke', 'e2e', 'regression' o 'all'.
        browser: Navegador — 'chromium', 'firefox', 'webkit' o 'all'.
        headed: Si True, abre el navegador en modo visible. Por defecto: False.
        base_url: URL base de la aplicación. Si no se indica, usa BASE_URL.
    """
    if suite not in SUITES:
        return f"Error: suite desconocida '{suite}'. Usa: {', '.join(SUITES.keys())}"
    if browser not in BROWSERS:
        return f"Error: navegador desconocido '{browser}'. Usa: {', '.join(BROWSERS)}"

    base_url = base_url or os.getenv("BASE_URL", "")
    if not base_url:
        return "Error: no se ha indicado base_url y la variable BASE_URL no está definida."

    # Buscar npx en el PATH o en node_modules
    npx = _find_npx()
    if not npx:
        return "Error: npx no encontrado. Asegúrate de que Node.js está instalado."

    cmd = [npx, "playwright", "test", SUITES[suite]]

    # Navegador
    if browser != "all":
        cmd += ["--project", browser]

    # Modo headed
    if headed:
        cmd += ["--headed"]

    # Reporter
    cmd += ["--reporter", "html,list"]

    timestamp = datetime.now().isoformat()
    env = {**os.environ, "BASE_URL": base_url}

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=300,
            env=env,
        )

        success = proc.returncode == 0
        _append_run_history({
            "timestamp": timestamp,
            "suite": suite,
            "browser": browser,
            "success": success,
        })

        status = "✅ Tests completados sin fallos" if success else "❌ Tests completados con fallos"
        output = (
            f"{status}\n\n"
            f"Suite: {suite}\n"
            f"Navegador: {browser}\n"
            f"Timestamp: {timestamp}\n\n"
            f"Salida:\n{proc.stdout[-3000:]}"
        )
        if proc.stderr:
            output += f"\n\nErrores:\n{proc.stderr[-500:]}"

        return output

    except subprocess.TimeoutExpired:
        return "Timeout: los tests tardaron más de 5 minutos."
    except FileNotFoundError:
        return "Error: Playwright no encontrado. Ejecuta: npm install"


@mcp.tool()
def get_last_failures(limit: int = 20) -> str:
    """
    Devuelve los fallos del último run de Playwright leyendo
    los ficheros de error-context.md generados en test-results/.

    Args:
        limit: Número máximo de fallos a devolver. Por defecto: 20.
    """
    if not TEST_RESULTS.exists():
        return "No se encontraron resultados. Ejecuta primero run_tests."

    # Buscar ficheros error-context.md generados por Playwright
    error_files = sorted(TEST_RESULTS.rglob("error-context.md"))

    if not error_files:
        # Intentar leer del JSON de resultados si existe
        results_json = TEST_RESULTS / "results.json"
        if results_json.exists():
            return _parse_results_json(results_json, limit)
        return "✅ No se encontraron fallos en el último run."

    error_files = error_files[:limit]
    lines = [f"Fallos encontrados: {len(error_files)}\n"]

    for i, error_file in enumerate(error_files, 1):
        # El nombre del directorio padre contiene el nombre del test
        test_name = error_file.parent.name
        # Limpiar el nombre — Playwright usa hashes al final
        test_name = "-".join(test_name.split("-")[:-1]) if "-" in test_name else test_name

        try:
            content = error_file.read_text()[:500]
        except Exception:
            content = "No se pudo leer el contexto del error."

        lines.append(
            f"{i}. {test_name}\n"
            f"   {content}\n"
        )

    return "\n".join(lines)


@mcp.tool()
def analyze_results(last_n_runs: int = 5) -> str:
    """
    Analiza el historial de runs de Playwright por suite y devuelve tendencias.

    Args:
        last_n_runs: Número de runs a analizar. Por defecto: 5.
    """
    if not HISTORY_FILE.exists():
        return "No hay historial. Ejecuta al menos un test con run_tests."

    try:
        with open(HISTORY_FILE) as f:
            history = json.load(f)
    except json.JSONDecodeError:
        return "El historial está corrupto."

    runs = history.get("runs", [])[-last_n_runs:]
    if not runs:
        return "No hay suficientes runs para analizar."

    total = len(runs)
    runs_ok = sum(1 for r in runs if r.get("success"))
    success_rate = (runs_ok / total * 100) if total > 0 else 0

    # Agrupar por suite
    suite_stats: dict[str, dict] = {}
    for run in runs:
        suite = run.get("suite", "unknown")
        if suite not in suite_stats:
            suite_stats[suite] = {"total": 0, "ok": 0}
        suite_stats[suite]["total"] += 1
        if run.get("success"):
            suite_stats[suite]["ok"] += 1

    # Agrupar por navegador
    browser_stats: dict[str, dict] = {}
    for run in runs:
        browser = run.get("browser", "unknown")
        if browser not in browser_stats:
            browser_stats[browser] = {"total": 0, "ok": 0}
        browser_stats[browser]["total"] += 1
        if run.get("success"):
            browser_stats[browser]["ok"] += 1

    # Comparativa último vs anterior
    ultimo = runs[-1] if runs else {}
    anterior = runs[-2] if len(runs) > 1 else {}
    if anterior:
        if ultimo.get("success") and not anterior.get("success"):
            comparativa = "Mejora respecto al run anterior."
        elif not ultimo.get("success") and anterior.get("success"):
            comparativa = "Regresión respecto al run anterior."
        else:
            comparativa = "Sin cambios de estado respecto al run anterior."
    else:
        comparativa = "Solo hay un run disponible."

    lines = [
        f"Análisis de tendencias (últimos {total} runs)\n",
        f"Runs exitosos: {runs_ok}/{total} ({success_rate:.1f}%)",
        f"{comparativa}\n",
        "Por suite:",
    ]
    for suite, stats in suite_stats.items():
        rate = (stats["ok"] / stats["total"] * 100) if stats["total"] > 0 else 0
        lines.append(f"  {suite}: {stats['ok']}/{stats['total']} ({rate:.0f}%)")

    lines.append("\nPor navegador:")
    for browser, stats in browser_stats.items():
        rate = (stats["ok"] / stats["total"] * 100) if stats["total"] > 0 else 0
        lines.append(f"  {browser}: {stats['ok']}/{stats['total']} ({rate:.0f}%)")

    return "\n".join(lines)


@mcp.tool()
def open_report() -> str:
    """
    Abre el reporte HTML de Playwright en el navegador por defecto.
    """
    if not PLAYWRIGHT_REPORT.exists():
        return "No se encontró el reporte HTML. Ejecuta primero run_tests."

    npx = _find_npx()
    if not npx:
        return "Error: npx no encontrado."

    try:
        subprocess.Popen(
            [npx, "playwright", "show-report", str(PLAYWRIGHT_REPORT)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Reporte abierto en el navegador: {PLAYWRIGHT_REPORT}"
    except Exception as e:
        return f"Error al abrir el reporte: {e}"


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _find_npx() -> str | None:
    """Busca npx en node_modules/.bin o en el PATH."""
    local_npx = PROJECT_ROOT / "node_modules" / ".bin" / "npx"
    if local_npx.exists():
        return str(local_npx)
    # Buscar en PATH
    result = subprocess.run(["which", "npx"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def _parse_results_json(results_json: Path, limit: int) -> str:
    """Parsea el JSON de resultados de Playwright si existe."""
    try:
        with open(results_json) as f:
            data = json.load(f)

        failures = []
        for suite in data.get("suites", []):
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    for result in test.get("results", []):
                        if result.get("status") == "failed":
                            failures.append({
                                "title": spec.get("title", "unknown"),
                                "error": result.get("error", {}).get("message", "Sin mensaje"),
                            })

        if not failures:
            return "✅ No se encontraron fallos en el último run."

        failures = failures[:limit]
        lines = [f"Fallos encontrados: {len(failures)}\n"]
        for i, f in enumerate(failures, 1):
            lines.append(f"{i}. {f['title']}\n   {f['error'][:200]}\n")
        return "\n".join(lines)

    except Exception as e:
        return f"Error al parsear resultados: {e}"


def _append_run_history(run_data: dict) -> None:
    """Añade el run al historial."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = {"runs": []}
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                history = json.load(f)
        except Exception:
            pass
    history["runs"].append(run_data)
    history["runs"] = history["runs"][-50:]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")

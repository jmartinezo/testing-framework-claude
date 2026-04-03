"""
Servidor MCP para Schemathesis.
Expone herramientas para ejecutar tests, leer fallos, analizar tendencias
y listar cobertura de endpoints — consumibles desde Claude Code.

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

PROJECT_ROOT = Path(os.getenv("API_TESTING_ROOT", Path(__file__).parent.parent.parent))
REPORTS_DIR = PROJECT_ROOT / "reports" / "allure-results"
RESULTS_FILE = PROJECT_ROOT / "reports" / "schemathesis-results.json"
HISTORY_FILE = PROJECT_ROOT / "reports" / "run-history.json"

PROFILES = {
    "fast": ["--checks", "not_a_server_error", "--max-examples", "10"],
    "schema": ["--checks", "all", "--max-examples", "50"],
    "full": ["--checks", "all", "--max-examples", "200", "--stateful", "links"],
}

mcp = FastMCP("schemathesis-mcp")


@mcp.tool()
def run_tests(
    profile: str,
    base_url: str = "",
    openapi_path: str = "/openapi.json",
    spec_url: str = "",
    auth: str = "",
    headers: list[str] | None = None,
) -> str:
    """
    Ejecuta tests de Schemathesis contra la API configurada.

    Args:
        profile: Perfil de ejecucion — 'fast' (smoke, 10 ejemplos),
                 'schema' (validacion completa, 50 ejemplos),
                 'full' (exhaustivo + stateful, 200 ejemplos).
        base_url: URL base de la API. Si no se indica, usa BASE_URL.
        openapi_path: Ruta al spec OpenAPI relativa a base_url. Por defecto: /openapi.json
        spec_url: URL absoluta al spec OpenAPI. Si se indica, tiene prioridad sobre
                  base_url+openapi_path para localizar el spec, y base_url se pasa
                  como --url para dirigir las peticiones.
        auth: Credenciales HTTP Basic en formato 'user:password'. Equivale a --auth.
        headers: Lista de cabeceras extra en formato 'Nombre: valor'.
                 Util para tokens y cookies, p.ej. ['Cookie: token=abc123',
                 'Authorization: Bearer eyJ...'].
    """
    base_url = base_url or os.getenv("BASE_URL", "")
    if not base_url and not spec_url:
        return "Error: no se ha indicado base_url y la variable BASE_URL no esta definida."
    if profile not in PROFILES:
        return f"Error: perfil desconocido '{profile}'. Usa: fast, schema o full."

    # Si spec_url es una URL de GitHub blob, convertir a raw para que Schemathesis pueda leerla
    if spec_url and "github.com" in spec_url and "/blob/" in spec_url:
        spec_url = spec_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

    location = spec_url if spec_url else f"{base_url.rstrip('/')}{openapi_path}"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Schemathesis 4.x expone el CLI como `st`, no como módulo Python ejecutable
    # --report acepta formato (ndjson), no ruta de fichero
    st_bin = Path(sys.executable).parent / "st"
    cmd = [
        str(st_bin), "run", location,
        "--output-truncate", "false",
        "--report", "ndjson",
        *PROFILES[profile],
    ]
    # Cuando el spec viene de una URL externa, indicar la base URL de la API con --url
    if spec_url and base_url:
        cmd += ["--url", base_url]
    # Autenticacion HTTP Basic
    if auth:
        cmd += ["--auth", auth]
    # Cabeceras adicionales (tokens, cookies, API keys)
    for header in (headers or []):
        cmd += ["-H", header]

    timestamp = datetime.now().isoformat()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=300)
        success = proc.returncode == 0
        # Guardar stdout (ndjson) como fichero de resultados para get_last_failures
        if proc.stdout.strip():
            RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            RESULTS_FILE.write_text(proc.stdout)
        _append_run_history({"timestamp": timestamp, "profile": profile, "success": success})
        status = "Tests completados sin fallos" if success else "Tests completados con fallos"
        output = f"{status}\n\nPerfil: {profile}\nSpec: {spec_url}\nTimestamp: {timestamp}\n\n"
        output += f"Salida:\n{proc.stdout[-3000:]}"
        if proc.stderr:
            output += f"\n\nErrores:\n{proc.stderr[-1000:]}"
        return output
    except subprocess.TimeoutExpired:
        return "Timeout: los tests tardaron mas de 5 minutos. Considera usar el perfil 'fast'."
    except FileNotFoundError:
        return "Schemathesis no encontrado. Instala con: pip install schemathesis"


@mcp.tool()
def get_last_failures(limit: int = 20) -> str:
    """
    Devuelve los fallos del ultimo run de Schemathesis.

    Args:
        limit: Numero maximo de fallos a devolver. Por defecto: 20.
    """
    failures = _load_ndjson_failures()
    if failures is None:
        return "No se encontraron resultados. Ejecuta primero run_tests."
    failures = failures[:limit]
    if not failures:
        return "No se encontraron fallos en el ultimo run."

    lines = [f"Fallos encontrados: {len(failures)}\n"]
    for i, fallo in enumerate(failures, 1):
        lines.append(
            f"{i}. [{fallo['phase']}] {fallo['label']}\n"
            f"   Mensaje: {fallo.get('message', 'Sin mensaje')}\n"
        )
    return "\n".join(lines)


@mcp.tool()
def analyze_trends(last_n_runs: int = 5) -> str:
    """
    Analiza el historial de runs y devuelve tendencias.

    Args:
        last_n_runs: Numero de runs a analizar. Por defecto: 5.
    """
    if not HISTORY_FILE.exists():
        return "No hay historial. Ejecuta al menos un test con run_tests."
    try:
        with open(HISTORY_FILE) as f:
            history = json.load(f)
    except json.JSONDecodeError:
        return "El historial esta corrupto."

    runs = history.get("runs", [])[-last_n_runs:]
    if not runs:
        return "No hay suficientes runs para analizar tendencias."

    total = len(runs)
    runs_ok = sum(1 for r in runs if r.get("success"))
    success_rate = (runs_ok / total * 100) if total > 0 else 0

    ultimo = runs[-1] if runs else {}
    anterior = runs[-2] if len(runs) > 1 else {}
    if anterior:
        if ultimo.get("success") and not anterior.get("success"):
            comparativa = "Mejora respecto al run anterior."
        elif not ultimo.get("success") and anterior.get("success"):
            comparativa = "Regresion respecto al run anterior."
        else:
            comparativa = "Sin cambios de estado respecto al run anterior."
    else:
        comparativa = "Solo hay un run disponible."

    return (
        f"Analisis de tendencias (ultimos {total} runs)\n\n"
        f"Runs exitosos: {runs_ok}/{total} ({success_rate:.1f}%)\n"
        f"Runs con fallos: {total - runs_ok}/{total}\n"
        f"{comparativa}"
    )


@mcp.tool()
def list_coverage(base_url: str = "", openapi_path: str = "/openapi.json", spec_url: str = "") -> str:
    """
    Lista todos los endpoints del spec OpenAPI con su estado de cobertura.

    Args:
        base_url: URL base de la API. Si no se indica, usa BASE_URL.
        openapi_path: Ruta al spec OpenAPI relativa a base_url. Por defecto: /openapi.json
        spec_url: URL absoluta al spec OpenAPI. Si se indica, tiene prioridad sobre
                  base_url+openapi_path.
    """
    base_url = base_url or os.getenv("BASE_URL", "")
    if not base_url and not spec_url:
        return "Error: no se ha indicado base_url y la variable BASE_URL no esta definida."

    # Convertir URL de GitHub blob a raw si es necesario
    if spec_url and "github.com" in spec_url and "/blob/" in spec_url:
        spec_url = spec_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

    location = spec_url if spec_url else f"{base_url.rstrip('/')}{openapi_path}"

    try:
        import schemathesis.openapi as oa
        schema = oa.from_url(location)
        all_endpoints = []
        for path, path_item in schema.raw_schema.get("paths", {}).items():
            for method in ["get", "post", "put", "patch", "delete", "options", "head"]:
                if method in path_item:
                    all_endpoints.append({"method": method.upper(), "path": path})
    except Exception as e:
        return f"No se pudo leer el spec OpenAPI desde {location}.\nError: {e}"

    # Obtener endpoints con fallos del ultimo ndjson
    failed_endpoints: set[str] = set()
    failures = _load_ndjson_failures()
    if failures:
        for fallo in failures:
            # El label tiene formato "METHOD /path"
            failed_endpoints.add(fallo["label"])

    ok, ko = [], []
    for ep in all_endpoints:
        key = f"{ep['method']} {ep['path']}"
        (ko if key in failed_endpoints else ok).append(f"  {key}")

    lines = [f"Cobertura de endpoints ({len(all_endpoints)} total)\n"]
    if ko:
        lines.append(f"Con fallos ({len(ko)}):")
        lines.extend(ko)
        lines.append("")
    lines.append(f"Sin fallos ({len(ok)}):")
    lines.extend(ok)
    return "\n".join(lines)


def _load_ndjson_failures() -> list[dict] | None:
    """
    Lee el fichero ndjson mas reciente generado por Schemathesis 4.x y extrae
    los ScenarioFinished con status 'failure', deduplicados por label.
    Devuelve None si no existe ningun fichero.
    """
    ndjson_dir = PROJECT_ROOT / "schemathesis-report"
    ndjson_files = sorted(ndjson_dir.glob("ndjson-*.ndjson")) if ndjson_dir.exists() else []
    if not ndjson_files:
        return None

    latest = ndjson_files[-1]
    seen: set[str] = set()
    failures = []
    try:
        with open(latest) as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("ScenarioFinished")
                if not payload or payload.get("status") != "failure":
                    continue
                label = payload.get("recorder", {}).get("label", "unknown")
                phase = payload.get("phase", "unknown")
                key = f"{phase}:{label}"
                if key not in seen:
                    seen.add(key)
                    failures.append({"label": label, "phase": phase, "message": payload.get("status")})
    except Exception:
        return None
    return failures


def _append_run_history(run_data: dict) -> None:
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


if __name__ == "__main__":
    mcp.run(transport="stdio")

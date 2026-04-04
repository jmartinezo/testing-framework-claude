"""
Script de envío de métricas a InfluxDB Cloud.
Lee los resultados de Schemathesis, pytest y Playwright y los envía
al bucket testing-metrics para visualización en Grafana.

Uso:
    python scripts/push_metrics.py --source all
    python scripts/push_metrics.py --source schemathesis
    python scripts/push_metrics.py --source pytest
    python scripts/push_metrics.py --source playwright

Requisitos:
    pip install influxdb-client python-dotenv
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

INFLUX_URL = os.getenv("INFLUX_URL", "https://us-east-1-1.aws.cloud2.influxdata.com")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "KPMG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "testing-metrics")

# Rutas de reportes
API_TESTING_ROOT = Path(os.getenv(
    "API_TESTING_ROOT",
    Path(__file__).parent.parent
))
UI_TESTING_ROOT = Path(os.getenv(
    "UI_TESTING_ROOT",
    Path(__file__).parent.parent.parent / "ui-testing"
))

SCHEMATHESIS_REPORT_DIR = API_TESTING_ROOT / "schemathesis-report"
SCHEMATHESIS_HISTORY = API_TESTING_ROOT / "reports" / "run-history.json"
PYTEST_RESULTS = API_TESTING_ROOT / "reports" / "pytest-results.json"
PW_TEST_RESULTS_DIR = UI_TESTING_ROOT / "reports" / "test-results"


# ---------------------------------------------------------------------------
# Cliente InfluxDB
# ---------------------------------------------------------------------------

def get_influx_client():
    """Inicializa y devuelve el cliente de InfluxDB."""
    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS
    except ImportError:
        print("Error: influxdb-client no está instalado.")
        print("Ejecuta: pip install influxdb-client")
        sys.exit(1)

    if not INFLUX_TOKEN:
        print("Error: INFLUX_TOKEN no está definido en .env")
        sys.exit(1)

    client = InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG,
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)
    return client, write_api


# ---------------------------------------------------------------------------
# Envío de métricas de Schemathesis
# ---------------------------------------------------------------------------

def push_schemathesis_metrics(write_api) -> int:
    """
    Lee el último fichero ndjson de Schemathesis y envía métricas a InfluxDB.
    Retorna el número de puntos enviados.
    """
    from influxdb_client import Point

    if not SCHEMATHESIS_REPORT_DIR.exists():
        print("⚠️  No se encontró directorio schemathesis-report/")
        return 0

    ndjson_files = sorted(SCHEMATHESIS_REPORT_DIR.glob("ndjson-*.ndjson"))
    if not ndjson_files:
        print("⚠️  No se encontraron ficheros ndjson de Schemathesis")
        return 0

    latest = ndjson_files[-1]
    print(f"📊 Procesando Schemathesis: {latest.name}")

    points = []
    total = 0
    passed = 0
    failed = 0
    endpoints_seen = set()

    with open(latest) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Evento de finalización de escenario
            payload = event.get("ScenarioFinished")
            if payload:
                total += 1
                status = payload.get("status", "unknown")
                label = payload.get("recorder", {}).get("label", "unknown")
                phase = payload.get("phase", "unknown")

                if status == "success":
                    passed += 1
                elif status == "failure":
                    failed += 1

                endpoints_seen.add(label)

                # Punto por endpoint
                point = (
                    Point("schemathesis_scenario")
                    .tag("endpoint", label)
                    .tag("phase", phase)
                    .tag("status", status)
                    .field("passed", 1 if status == "success" else 0)
                    .field("failed", 1 if status == "failure" else 0)
                    .time(datetime.now(timezone.utc))
                )
                points.append(point)

    # Punto de resumen del run
    if total > 0:
        error_rate = (failed / total * 100) if total > 0 else 0
        summary_point = (
            Point("schemathesis_run")
            .tag("source", "schemathesis")
            .field("total", total)
            .field("passed", passed)
            .field("failed", failed)
            .field("error_rate", round(error_rate, 2))
            .field("endpoints_covered", len(endpoints_seen))
            .time(datetime.now(timezone.utc))
        )
        points.append(summary_point)

    if points:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
        print(f"✅ Schemathesis: {len(points)} puntos enviados "
              f"({passed} passed, {failed} failed, {len(endpoints_seen)} endpoints)")

    return len(points)


# ---------------------------------------------------------------------------
# Envío de métricas de pytest
# ---------------------------------------------------------------------------

def push_pytest_metrics(write_api) -> int:
    """
    Lee el JSON de resultados de pytest y envía métricas a InfluxDB.
    Genera el JSON con: pytest --json-report --json-report-file=reports/pytest-results.json
    """
    from influxdb_client import Point

    if not PYTEST_RESULTS.exists():
        print("⚠️  No se encontró reports/pytest-results.json")
        print("    Ejecuta pytest con: pytest --json-report --json-report-file=reports/pytest-results.json")
        return 0

    print(f"📊 Procesando pytest: {PYTEST_RESULTS.name}")

    with open(PYTEST_RESULTS) as f:
        data = json.load(f)

    summary = data.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    duration = data.get("duration", 0)

    points = []

    # Punto de resumen del run
    error_rate = (failed / total * 100) if total > 0 else 0
    run_point = (
        Point("pytest_run")
        .tag("source", "pytest")
        .field("total", total)
        .field("passed", passed)
        .field("failed", failed)
        .field("skipped", skipped)
        .field("duration_seconds", round(duration, 2))
        .field("error_rate", round(error_rate, 2))
        .time(datetime.now(timezone.utc))
    )
    points.append(run_point)

    # Punto por test
    for test in data.get("tests", []):
        test_point = (
            Point("pytest_test")
            .tag("name", test.get("nodeid", "unknown")[:100])
            .tag("outcome", test.get("outcome", "unknown"))
            .field("duration_seconds", round(test.get("duration", 0), 3))
            .field("passed", 1 if test.get("outcome") == "passed" else 0)
            .field("failed", 1 if test.get("outcome") == "failed" else 0)
            .time(datetime.now(timezone.utc))
        )
        points.append(test_point)

    if points:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
        print(f"✅ pytest: {len(points)} puntos enviados "
              f"({passed} passed, {failed} failed, {skipped} skipped)")

    return len(points)


# ---------------------------------------------------------------------------
# Envío de métricas de Playwright
# ---------------------------------------------------------------------------

def _parse_error_context(md_path: Path) -> dict:
    """Extrae nombre del test, localización, error y browser de un error-context.md."""
    content = md_path.read_text(encoding="utf-8")

    name_match = re.search(r"- Name: (.+)", content)
    name = name_match.group(1).strip() if name_match else "unknown"

    location_match = re.search(r"- Location: (.+)", content)
    location = location_match.group(1).strip() if location_match else "unknown"

    error_match = re.search(r"# Error details\s+```[^\n]*\n(.*?)```", content, re.DOTALL)
    error_msg = error_match.group(1).strip() if error_match else "unknown error"

    # El nombre del directorio padre termina siempre en el browser (ej. "-chromium")
    browser = md_path.parent.name.rsplit("-", 1)[-1]

    return {
        "name": name,
        "location": location,
        "error": error_msg,
        "browser": browser,
    }


def push_playwright_metrics(write_api) -> int:
    """
    Escanea los ficheros error-context.md dentro de ui-testing/reports/test-results/.
    Cada fichero encontrado representa un test fallido.
    Si no hay ninguno, todos los tests pasaron.
    """
    from influxdb_client import Point

    if not PW_TEST_RESULTS_DIR.exists():
        print("⚠️  No se encontró el directorio reports/test-results/ de Playwright")
        return 0

    print(f"📊 Procesando Playwright: {PW_TEST_RESULTS_DIR}")

    error_files = list(PW_TEST_RESULTS_DIR.rglob("error-context.md"))
    failed = len(error_files)
    now = datetime.now(timezone.utc)
    points = []

    # Un punto por test fallido con su detalle
    for md_path in error_files:
        info = _parse_error_context(md_path)
        test_point = (
            Point("playwright_test")
            .tag("name", info["name"][:100])
            .tag("location", info["location"][:100])
            .tag("browser", info["browser"])
            .tag("status", "failed")
            .field("passed", 0)
            .field("failed", 1)
            .field("error", info["error"][:500])
            .time(now)
        )
        points.append(test_point)

    # Punto de resumen del run
    run_point = (
        Point("playwright_run")
        .tag("source", "playwright")
        .field("failed", failed)
        .field("success", 1 if failed == 0 else 0)
        .time(now)
    )
    points.append(run_point)

    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
    status = "✅ todos los tests pasaron" if failed == 0 else f"❌ {failed} test(s) fallido(s)"
    print(f"✅ Playwright: {len(points)} puntos enviados ({status})")

    return len(points)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Envía métricas de testing a InfluxDB Cloud"
    )
    parser.add_argument(
        "--source",
        choices=["all", "schemathesis", "pytest", "playwright"],
        default="all",
        help="Fuente de métricas a enviar (por defecto: all)",
    )
    args = parser.parse_args()

    print(f"\n{'─' * 50}")
    print(f"  Enviando métricas a InfluxDB Cloud")
    print(f"  Bucket: {INFLUX_BUCKET} | Org: {INFLUX_ORG}")
    print(f"{'─' * 50}\n")

    client, write_api = get_influx_client()
    total_points = 0

    try:
        if args.source in ("all", "schemathesis"):
            total_points += push_schemathesis_metrics(write_api)

        if args.source in ("all", "pytest"):
            total_points += push_pytest_metrics(write_api)

        if args.source in ("all", "playwright"):
            total_points += push_playwright_metrics(write_api)

    finally:
        client.close()

    print(f"\n{'─' * 50}")
    print(f"  Total puntos enviados: {total_points}")
    print(f"  Dashboard: https://jorgemartinezortt.grafana.net")
    print(f"{'─' * 50}\n")


if __name__ == "__main__":
    main()

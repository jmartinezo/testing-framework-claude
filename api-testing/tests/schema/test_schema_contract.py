"""
Tests de contrato OpenAPI con Schemathesis 4.x.
Validan que la API cumple su propio spec — respuestas, tipos, formatos.
"""

import os
import schemathesis
from schemathesis.checks import not_a_server_error

BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
OPENAPI_PATH = os.getenv("OPENAPI_PATH", "/openapi.json")
SPEC_URL = os.getenv("OPENAPI_SPEC_URL", f"{BASE_URL}{OPENAPI_PATH}")
RESPONSE_TIME_THRESHOLD_MS = int(os.getenv("RESPONSE_TIME_THRESHOLD_MS", "2000"))

schema = schemathesis.openapi.from_url(SPEC_URL)


@schema.parametrize()
def test_no_server_errors(case):
    """Ningún endpoint devuelve respuestas 5xx."""
    response = case.call()
    case.validate_response(response, checks=[not_a_server_error])


@schema.parametrize()
def test_response_time(case):
    """Todos los endpoints responden dentro del umbral configurado."""
    response = case.call()
    # En Schemathesis 4.x response.elapsed ya es float en segundos
    elapsed_ms = response.elapsed * 1000
    assert elapsed_ms < RESPONSE_TIME_THRESHOLD_MS, (
        f"{case.method.upper()} {case.path} tardó {elapsed_ms:.0f}ms "
        f"(umbral: {RESPONSE_TIME_THRESHOLD_MS}ms)"
    )

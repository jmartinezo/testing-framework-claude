"""
Hooks personalizados de Schemathesis.
Se cargan automáticamente si se pasa --hookmodule hooks.hooks al CLI.

Documentación: https://schemathesis.readthedocs.io/en/stable/extending.html
"""

import os
import time

import schemathesis
from schemathesis import Case, Response


# ---------------------------------------------------------------------------
# Hook: detectar respuestas lentas
# ---------------------------------------------------------------------------

@schemathesis.hook("after_call")
def detect_slow_response(context, case: Case, response: Response) -> None:
    """
    Registra un warning si la respuesta supera el umbral configurado.
    El umbral se lee de la variable de entorno RESPONSE_TIME_THRESHOLD_MS
    (por defecto 2000ms).
    """
    threshold_ms = int(os.getenv("RESPONSE_TIME_THRESHOLD_MS", "2000"))
    elapsed_ms = response.elapsed.total_seconds() * 1000

    if elapsed_ms > threshold_ms:
        print(
            f"\n⚠️  Respuesta lenta detectada: "
            f"{case.method.upper()} {case.formatted_path} "
            f"tardó {elapsed_ms:.0f}ms (umbral: {threshold_ms}ms)"
        )


# ---------------------------------------------------------------------------
# Hook: detectar errores embebidos en respuestas 200 OK
# ---------------------------------------------------------------------------

@schemathesis.hook("after_call")
def check_embedded_errors(context, case: Case, response: Response) -> None:
    """
    Detecta respuestas 200 OK que contienen campos de error en el body JSON.
    Algunos servidores devuelven errores con status 200 — este hook los expone.
    """
    if response.status_code != 200:
        return

    try:
        body = response.json()
    except Exception:
        return

    # Campos que indican un error embebido
    error_fields = {"error", "errors", "fault", "exception"}
    if isinstance(body, dict):
        found = error_fields.intersection(body.keys())
        if found:
            print(
                f"\n⚠️  Error embebido en respuesta 200: "
                f"{case.method.upper()} {case.formatted_path} "
                f"contiene campo(s): {found}"
            )


# ---------------------------------------------------------------------------
# Hook: filtrar parámetros para evitar IDs fuera de rango
# ---------------------------------------------------------------------------

@schemathesis.hook("filter_query")
def filter_invalid_ids(context, query) -> bool:
    """
    Filtra peticiones con IDs negativos o cero para evitar ruido en los tests.
    Ajusta el rango según los datos reales de tu API.
    """
    if query is None:
        return True

    # Rechazar IDs negativos o cero en parámetros de query
    for key, value in query.items():
        if "id" in key.lower():
            try:
                if int(value) <= 0:
                    return False
            except (TypeError, ValueError):
                pass

    return True

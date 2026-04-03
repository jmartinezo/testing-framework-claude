"""
Fixtures compartidas para todos los tests de api-testing.
Disponibles automáticamente en todos los ficheros de test via pytest.
"""

import json
import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()


# ---------------------------------------------------------------------------
# Fixtures de configuración
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url() -> str:
    """URL base de la API bajo prueba. Requerida."""
    url = os.getenv("BASE_URL", "")
    if not url:
        pytest.fail("La variable de entorno BASE_URL no está definida.")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def env() -> str:
    """Entorno activo: local, staging o production."""
    return os.getenv("ENV", "local")


@pytest.fixture(scope="session")
def response_time_threshold_ms() -> int:
    """Umbral de tiempo de respuesta en milisegundos."""
    return int(os.getenv("RESPONSE_TIME_THRESHOLD_MS", "2000"))


# ---------------------------------------------------------------------------
# Fixtures de sesión HTTP
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def http_session(base_url) -> requests.Session:
    """
    Sesión HTTP reutilizable para todos los tests de la sesión.
    Incluye la base URL y cabeceras comunes.
    """
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
    })

    # Añadir autenticación si está configurada
    api_key = os.getenv("API_KEY")
    if api_key:
        session.headers["Authorization"] = f"Bearer {api_key}"

    api_user = os.getenv("API_USER")
    api_password = os.getenv("API_PASSWORD")
    if api_user and api_password:
        session.auth = (api_user, api_password)

    yield session
    session.close()


# ---------------------------------------------------------------------------
# Fixtures de datos de prueba
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_state() -> dict:
    """
    Carga el estado de prueba generado por tests anteriores o por setup.
    Busca en data/output/test-state.json.
    """
    state_file = Path(__file__).parent.parent / "data" / "output" / "test-state.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return {}


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Ruta al directorio de fixtures estáticos."""
    return Path(__file__).parent.parent / "data" / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures de reporting
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def ensure_reports_dir():
    """Asegura que el directorio de reportes existe antes de los tests."""
    reports_dir = Path(__file__).parent.parent / "reports" / "allure-results"
    reports_dir.mkdir(parents=True, exist_ok=True)

"""
Tests funcionales de API — operaciones CRUD genéricas.
Estos tests sí están escritos a mano y validan comportamiento de negocio,
no solo conformidad con el schema.

Adapta los endpoints y payloads a tu API específica.
"""

import pytest


# ---------------------------------------------------------------------------
# Tests de lectura (GET)
# ---------------------------------------------------------------------------

class TestRead:
    """Tests de operaciones de lectura."""

    def test_list_returns_200(self, http_session, base_url):
        """El endpoint de listado devuelve 200 y una lista."""
        # Adaptar el endpoint a tu API
        response = http_session.get(f"{base_url}/")
        assert response.status_code == 200

    def test_list_response_is_json(self, http_session, base_url):
        """La respuesta del listado es JSON válido."""
        response = http_session.get(f"{base_url}/")
        assert response.headers.get("Content-Type", "").startswith("application/json")
        assert response.json() is not None

    def test_get_nonexistent_resource_returns_404(self, http_session, base_url):
        """Un ID que no existe devuelve 404, no 500."""
        response = http_session.get(f"{base_url}/nonexistent-resource-99999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests de rendimiento básico
# ---------------------------------------------------------------------------

class TestPerformance:
    """Tests de rendimiento — umbrales básicos."""

    def test_list_response_time(self, http_session, base_url, response_time_threshold_ms):
        """El endpoint de listado responde dentro del umbral configurado."""
        response = http_session.get(f"{base_url}/")
        elapsed_ms = response.elapsed.total_seconds() * 1000
        assert elapsed_ms < response_time_threshold_ms, (
            f"Respuesta demasiado lenta: {elapsed_ms:.0f}ms "
            f"(umbral: {response_time_threshold_ms}ms)"
        )


# ---------------------------------------------------------------------------
# Tests de cabeceras y seguridad básica
# ---------------------------------------------------------------------------

class TestHeaders:
    """Tests de cabeceras HTTP."""

    def test_response_has_content_type(self, http_session, base_url):
        """Todas las respuestas incluyen Content-Type."""
        response = http_session.get(f"{base_url}/")
        assert "Content-Type" in response.headers

    def test_no_server_version_exposed(self, http_session, base_url):
        """El servidor no expone su versión en las cabeceras (seguridad básica)."""
        response = http_session.get(f"{base_url}/")
        server_header = response.headers.get("Server", "")
        # Verificar que no incluye versiones concretas
        assert not any(char.isdigit() for char in server_header), (
            f"La cabecera Server expone versión: {server_header}"
        )

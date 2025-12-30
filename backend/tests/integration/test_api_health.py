"""
Integration Tests for Health and Status Endpoints

Tests the API health check and status endpoints.
These require PostgreSQL to run (models use JSONB/Vector types).
"""

import pytest
import os
from fastapi.testclient import TestClient

# Mark all tests as integration tests
# Skip if PostgreSQL is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        "postgresql" not in os.environ.get("DATABASE_URL", ""),
        reason="Integration tests require PostgreSQL"
    )
]


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_endpoint(self, test_client: TestClient):
        """Test the /health endpoint returns 200."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_endpoint_includes_service_info(self, test_client: TestClient):
        """Test health endpoint includes service information."""
        response = test_client.get("/health")

        data = response.json()
        # Should have some status info
        assert "status" in data


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, test_client: TestClient):
        """Test the root endpoint."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data

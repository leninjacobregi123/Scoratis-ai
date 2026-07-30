
import pytest
from fastapi.testclient import TestClient
import os

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        "postgresql" not in os.environ.get("DATABASE_URL", ""),
        reason="Integration tests require PostgreSQL"
    )
]

def test_qwen_model_generation(test_client: TestClient):
    response = test_client.post(
        "/agent/chat",
        json={
            "message": "Hello, this is a test. Who are you?",
            "session_id": "test-gpu-session"
        }
    )

    assert response.status_code != 500, f"Server returned a 500 error: {response.text}"

    assert response.status_code == 200, f"Expected status 200, but got {response.status_code}: {response.text}"

    response_data = response.json()
    assert "response" in response_data
    assert "model" in response_data
    assert len(response_data["response"]) > 0


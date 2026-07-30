
import pytest
from fastapi.testclient import TestClient
import os

from core.auth import get_current_user

# Requires a real Ollama server with a model loaded - not available in CI.
# Opt in locally with RUN_LIVE_OLLAMA_TESTS=true (see test_video_generation.py
# for the equivalent pattern used for the video pipeline).
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        "postgresql" not in os.environ.get("DATABASE_URL", ""),
        reason="Integration tests require PostgreSQL"
    ),
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_OLLAMA_TESTS") != "true",
        reason="Requires a live Ollama server - opt in with RUN_LIVE_OLLAMA_TESTS=true",
    ),
]


class _FakeUser:
    id = 1
    is_active = True


def test_qwen_model_generation(test_client: TestClient):
    from main import app
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()

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


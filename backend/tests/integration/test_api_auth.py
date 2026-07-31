"""
Integration Tests for Authentication Endpoints

Tests signup, login, and Google Sign-In. These require PostgreSQL (models
use JSONB/Vector types elsewhere in the schema even though the users table
itself doesn't).
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        "postgresql" not in os.environ.get("DATABASE_URL", ""),
        reason="Integration tests require PostgreSQL"
    ),
]


class TestSignupAndLogin:
    def test_signup_then_login(self, test_client: TestClient):
        signup = test_client.post("/auth/signup", json={
            "username": "alice_test",
            "email": "alice_test@example.com",
            "password": "correct-horse-battery",
        })
        assert signup.status_code == 201
        assert "access_token" in signup.json()

        login = test_client.post("/auth/login", data={
            "username": "alice_test",
            "password": "correct-horse-battery",
        })
        assert login.status_code == 200
        assert "access_token" in login.json()

    def test_signup_duplicate_email_rejected(self, test_client: TestClient):
        payload = {
            "username": "bob_test",
            "email": "bob_test@example.com",
            "password": "correct-horse-battery",
        }
        first = test_client.post("/auth/signup", json=payload)
        assert first.status_code == 201

        second = test_client.post("/auth/signup", json={**payload, "username": "bob_test_2"})
        assert second.status_code == 409

    def test_login_wrong_password_rejected(self, test_client: TestClient):
        test_client.post("/auth/signup", json={
            "username": "carol_test",
            "email": "carol_test@example.com",
            "password": "correct-horse-battery",
        })
        response = test_client.post("/auth/login", data={
            "username": "carol_test",
            "password": "wrong-password",
        })
        assert response.status_code == 401


class TestGoogleSignIn:
    def test_google_signin_disabled_without_client_id(self, test_client: TestClient):
        # Force GOOGLE_CLIENT_ID to empty regardless of the environment's own
        # .env - the endpoint should refuse cleanly rather than attempt
        # verification against an empty audience.
        import config
        original = config.settings.GOOGLE_CLIENT_ID
        config.settings.GOOGLE_CLIENT_ID = ""
        try:
            response = test_client.post("/auth/google", json={"credential": "irrelevant"})
            assert response.status_code == 503
        finally:
            config.settings.GOOGLE_CLIENT_ID = original

    def test_google_signin_creates_new_user(self, test_client: TestClient):
        import config
        config.settings.GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
        try:
            with patch("api.routes.auth.google_id_token.verify_oauth2_token") as mock_verify:
                mock_verify.return_value = {
                    "email": "newgoogleuser@gmail.com",
                    "email_verified": True,
                    "name": "New Google User",
                }
                response = test_client.post("/auth/google", json={"credential": "fake-token"})
                assert response.status_code == 200
                assert "access_token" in response.json()

                me = test_client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {response.json()['access_token']}"},
                )
                assert me.status_code == 200
                assert me.json()["email"] == "newgoogleuser@gmail.com"
        finally:
            config.settings.GOOGLE_CLIENT_ID = ""

    def test_google_signin_logs_in_existing_user(self, test_client: TestClient):
        import config
        config.settings.GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
        try:
            with patch("api.routes.auth.google_id_token.verify_oauth2_token") as mock_verify:
                mock_verify.return_value = {
                    "email": "repeatgoogleuser@gmail.com",
                    "email_verified": True,
                    "name": "Repeat User",
                }
                first = test_client.post("/auth/google", json={"credential": "fake-token"})
                assert first.status_code == 200
                first_user_id = test_client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {first.json()['access_token']}"},
                ).json()["id"]

                second = test_client.post("/auth/google", json={"credential": "fake-token"})
                assert second.status_code == 200
                second_user_id = test_client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {second.json()['access_token']}"},
                ).json()["id"]

                # Same email must resolve to the same account, not a duplicate.
                assert first_user_id == second_user_id
        finally:
            config.settings.GOOGLE_CLIENT_ID = ""

    def test_google_signin_rejects_unverified_email(self, test_client: TestClient):
        import config
        config.settings.GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
        try:
            with patch("api.routes.auth.google_id_token.verify_oauth2_token") as mock_verify:
                mock_verify.return_value = {
                    "email": "unverified@gmail.com",
                    "email_verified": False,
                }
                response = test_client.post("/auth/google", json={"credential": "fake-token"})
                assert response.status_code == 401
        finally:
            config.settings.GOOGLE_CLIENT_ID = ""

    def test_google_signin_rejects_invalid_token(self, test_client: TestClient):
        import config
        config.settings.GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
        try:
            with patch("api.routes.auth.google_id_token.verify_oauth2_token") as mock_verify:
                mock_verify.side_effect = ValueError("Token expired")
                response = test_client.post("/auth/google", json={"credential": "bad-token"})
                assert response.status_code == 401
        finally:
            config.settings.GOOGLE_CLIENT_ID = ""

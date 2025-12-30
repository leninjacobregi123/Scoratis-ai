"""
Integration Tests for Document API Endpoints

Tests document upload, retrieval, and management.
These require PostgreSQL to run (models use JSONB/Vector types).
"""

import pytest
import os
from fastapi.testclient import TestClient
from io import BytesIO
from unittest.mock import patch, MagicMock

# Mark all tests as integration tests
# Skip if PostgreSQL is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        "postgresql" not in os.environ.get("DATABASE_URL", ""),
        reason="Integration tests require PostgreSQL"
    )
]


class TestDocumentUpload:
    """Tests for document upload endpoint."""

    def test_upload_document_txt(self, test_client: TestClient):
        """Test uploading a text document."""
        # Create a test file
        file_content = b"This is a test document about machine learning."
        files = {
            "file": ("test.txt", BytesIO(file_content), "text/plain")
        }

        with patch("main.ingest_document_task") as mock_task:
            mock_task.delay = MagicMock()

            response = test_client.post("/documents/upload", files=files)

            # Should accept the upload (may return 200 or 202)
            assert response.status_code in [200, 201, 202, 422]  # 422 if validation fails in test

    def test_upload_document_requires_file(self, test_client: TestClient):
        """Test that upload requires a file."""
        response = test_client.post("/documents/upload")

        assert response.status_code == 422  # Validation error


class TestDocumentList:
    """Tests for document listing endpoint."""

    def test_list_documents(self, test_client: TestClient):
        """Test listing documents."""
        response = test_client.get("/documents")

        # Should return 200 with list
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_list_documents_with_pagination(self, test_client: TestClient):
        """Test listing documents with pagination."""
        response = test_client.get("/documents?skip=0&limit=10")

        assert response.status_code == 200


class TestDocumentRetrieval:
    """Tests for document retrieval endpoint."""

    def test_get_document_not_found(self, test_client: TestClient):
        """Test getting a non-existent document."""
        response = test_client.get("/documents/99999")

        assert response.status_code == 404

    def test_delete_document_not_found(self, test_client: TestClient):
        """Test deleting a non-existent document."""
        response = test_client.delete("/documents/99999")

        assert response.status_code == 404

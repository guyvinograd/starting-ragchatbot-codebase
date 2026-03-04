"""API endpoint tests for the RAG chatbot FastAPI application.

Covers:
  POST /api/query        — query processing
  GET  /api/courses      — course statistics
  DELETE /api/clear-session/{session_id} — session clearing

The FastAPI app is imported via conftest.py with RAGSystem and StaticFiles
mocked so no real ChromaDB, embeddings, or Anthropic API calls are made.
"""

from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:

    def test_returns_answer_and_sources(self, client, mock_rag, sample_query):
        response = client.post("/api/query", json=sample_query)

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Here is the answer."
        assert data["session_id"] == sample_query["session_id"]
        assert len(data["sources"]) == 1
        assert data["sources"][0]["text"] == "Course A - Lesson 1"
        assert data["sources"][0]["url"] == "http://example.com/lesson1"

    def test_auto_creates_session_id_when_absent(self, client, mock_rag):
        """Omitting session_id should result in a freshly created one being returned."""
        mock_rag.session_manager.create_session.return_value = "auto-session-99"

        response = client.post("/api/query", json={"query": "What is RAG?"})

        assert response.status_code == 200
        assert response.json()["session_id"] == "auto-session-99"

    def test_passes_query_and_session_to_rag_system(self, client, mock_rag, sample_query):
        client.post("/api/query", json=sample_query)

        mock_rag.query.assert_called_once_with(
            sample_query["query"], sample_query["session_id"]
        )

    def test_returns_empty_sources_list(self, client, mock_rag, sample_query, monkeypatch):
        monkeypatch.setattr(mock_rag, "query", MagicMock(return_value=("No sources here.", [])))

        response = client.post("/api/query", json=sample_query)

        assert response.status_code == 200
        assert response.json()["sources"] == []

    def test_returns_500_when_rag_raises(self, client, mock_rag, monkeypatch):
        monkeypatch.setattr(
            mock_rag, "query", MagicMock(side_effect=Exception("Search failed"))
        )

        response = client.post("/api/query", json={"query": "test", "session_id": "s1"})

        assert response.status_code == 500
        assert "Search failed" in response.json()["detail"]

    def test_missing_query_field_returns_422(self, client):
        """Pydantic validation should reject requests without the required `query` field."""
        response = client.post("/api/query", json={"session_id": "s1"})

        assert response.status_code == 422

    def test_empty_query_is_accepted(self, client, mock_rag):
        """An empty string is technically valid per the Pydantic model."""
        response = client.post("/api/query", json={"query": ""})

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:

    def test_returns_course_stats(self, client, mock_rag, sample_course_data):
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == sample_course_data["total_courses"]
        assert data["course_titles"] == sample_course_data["course_titles"]

    def test_response_schema(self, client):
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

    def test_calls_get_course_analytics(self, client, mock_rag):
        client.get("/api/courses")

        mock_rag.get_course_analytics.assert_called_once()

    def test_returns_500_when_analytics_raises(self, client, mock_rag, monkeypatch):
        monkeypatch.setattr(
            mock_rag,
            "get_course_analytics",
            MagicMock(side_effect=Exception("DB unavailable")),
        )

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "DB unavailable" in response.json()["detail"]

    def test_handles_zero_courses(self, client, mock_rag, monkeypatch):
        monkeypatch.setattr(
            mock_rag,
            "get_course_analytics",
            MagicMock(return_value={"total_courses": 0, "course_titles": []}),
        )

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []


# ---------------------------------------------------------------------------
# /api/clear-session/{session_id}
# ---------------------------------------------------------------------------

class TestClearSessionEndpoint:

    def test_returns_cleared_status(self, client):
        response = client.delete("/api/clear-session/some-session")

        assert response.status_code == 200
        assert response.json() == {"status": "cleared"}

    def test_delegates_to_session_manager(self, client, mock_rag):
        client.delete("/api/clear-session/my-session-id")

        mock_rag.session_manager.clear_session.assert_called_once_with("my-session-id")

    def test_session_id_passed_correctly(self, client, mock_rag):
        session_id = "unique-session-abc123"
        client.delete(f"/api/clear-session/{session_id}")

        args, _ = mock_rag.session_manager.clear_session.call_args
        assert args[0] == session_id

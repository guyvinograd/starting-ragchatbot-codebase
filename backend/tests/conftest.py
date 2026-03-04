import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add backend directory to sys.path so bare module imports (e.g. `from config import config`) work
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Stub heavy external packages before any backend module is imported.
# This prevents ChromaDB, sentence-transformers, and Anthropic from being loaded
# (they require large model downloads and API keys in a test environment).
for _mod in ["chromadb", "chromadb.config", "sentence_transformers", "anthropic"]:
    sys.modules.setdefault(_mod, MagicMock())

# ---------------------------------------------------------------------------
# Build the shared mock RAGSystem instance once at collection time.
# Tests should NOT mutate return values directly; use monkeypatch instead so
# changes are automatically undone after each test.
# ---------------------------------------------------------------------------
_mock_rag = MagicMock()
_mock_rag.query.return_value = (
    "Here is the answer.",
    [{"text": "Course A - Lesson 1", "url": "http://example.com/lesson1"}],
)
_mock_rag.get_course_analytics.return_value = {
    "total_courses": 2,
    "course_titles": ["Course A", "Course B"],
}
_mock_rag.session_manager.create_session.return_value = "mock-session-id"
_mock_rag.add_course_folder.return_value = (0, 0)

# Import the FastAPI app with mocks active so the module-level code in app.py
# (RAGSystem instantiation and StaticFiles mount) uses our stubs.
with (
    patch("rag_system.RAGSystem", return_value=_mock_rag),
    patch("fastapi.staticfiles.StaticFiles"),
):
    import app as _app_module  # noqa: E402

# Ensure the module-level `rag_system` global points at our mock.
_app_module.rag_system = _mock_rag


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def mock_rag():
    """Shared mock RAGSystem instance. Use monkeypatch to override behaviour per-test."""
    return _mock_rag


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient for the FastAPI app."""
    from fastapi.testclient import TestClient

    return TestClient(_app_module.app)


@pytest.fixture(autouse=True)
def reset_mock_calls(mock_rag):
    """Reset call history on the shared mock before every test.

    Return values are preserved (reset_mock() keeps them by default) so the
    standard test data remains available without re-configuration.
    """
    mock_rag.reset_mock()


@pytest.fixture
def sample_query():
    return {"query": "What is machine learning?", "session_id": "test-session-id"}


@pytest.fixture
def sample_course_data():
    return {"total_courses": 2, "course_titles": ["Course A", "Course B"]}

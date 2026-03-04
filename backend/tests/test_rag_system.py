"""
Tests for RAGSystem.query() in rag_system.py.

Covers:
- Return type is (str, list)
- Tool definitions and tool_manager passed to AIGenerator
- Sources retrieved from ToolManager and returned to caller
- Sources reset after each query
- Session history retrieved and forwarded to AIGenerator
- Session history updated with exchange after each query
- No session calls when session_id is omitted
- User query wrapped in prompt before sending to AI
- Both CourseSearchTool and CourseOutlineTool registered on startup
"""

import pytest
from unittest.mock import MagicMock, patch

from rag_system import RAGSystem


# ---------------------------------------------------------------------------
# Fixture: RAGSystem with all heavy deps mocked
# ---------------------------------------------------------------------------

def _make_mock_config():
    cfg = MagicMock()
    cfg.CHUNK_SIZE = 500
    cfg.CHUNK_OVERLAP = 50
    cfg.CHROMA_PATH = "./test_chroma"
    cfg.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    cfg.MAX_RESULTS = 5
    cfg.ANTHROPIC_API_KEY = "test-key"
    cfg.ANTHROPIC_MODEL = "claude-test"
    cfg.MAX_HISTORY = 2
    return cfg


@pytest.fixture
def rag():
    """RAGSystem with VectorStore, AIGenerator, DocumentProcessor, SessionManager mocked."""
    with (
        patch("rag_system.DocumentProcessor"),
        patch("rag_system.VectorStore"),
        patch("rag_system.AIGenerator"),
        patch("rag_system.SessionManager"),
    ):
        system = RAGSystem(_make_mock_config())

    # Replace tool_manager with a fresh mock for query-flow tests
    system.tool_manager = MagicMock()
    system.tool_manager.get_tool_definitions.return_value = [
        {"name": "search_course_content"},
        {"name": "get_course_outline"},
    ]
    system.tool_manager.get_last_sources.return_value = []

    # Default AI response
    system.ai_generator.generate_response.return_value = "Here is the answer."

    # Default: new session returns None history
    system.session_manager.get_conversation_history.return_value = None

    return system


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_returns_tuple(self, rag):
        result = rag.query("What is Python?", session_id="s1")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_string(self, rag):
        response, _ = rag.query("What is Python?", session_id="s1")
        assert isinstance(response, str)
        assert response == "Here is the answer."

    def test_second_element_is_list(self, rag):
        _, sources = rag.query("What is Python?", session_id="s1")
        assert isinstance(sources, list)


# ---------------------------------------------------------------------------
# AI generator call arguments
# ---------------------------------------------------------------------------

class TestAIGeneratorCallArgs:
    def _call_kwargs(self, rag, query="test", session_id="s1"):
        rag.query(query, session_id=session_id)
        return rag.ai_generator.generate_response.call_args[1]

    def test_query_is_passed_as_keyword_arg(self, rag):
        kwargs = self._call_kwargs(rag, query="test query")
        assert "query" in kwargs

    def test_user_query_wrapped_in_prompt(self, rag):
        kwargs = self._call_kwargs(rag, query="What is a class?")
        assert "What is a class?" in kwargs["query"]

    def test_tool_definitions_forwarded(self, rag):
        kwargs = self._call_kwargs(rag)
        assert kwargs["tools"] == [
            {"name": "search_course_content"},
            {"name": "get_course_outline"},
        ]

    def test_tool_manager_instance_forwarded(self, rag):
        kwargs = self._call_kwargs(rag)
        assert kwargs["tool_manager"] is rag.tool_manager


# ---------------------------------------------------------------------------
# Source retrieval and reset
# ---------------------------------------------------------------------------

class TestSourceHandling:
    def test_sources_from_tool_manager_returned(self, rag):
        expected = [{"text": "Python Basics - Lesson 1", "url": "https://example.com"}]
        rag.tool_manager.get_last_sources.return_value = expected
        _, sources = rag.query("What is Python?", session_id="s1")
        assert sources == expected

    def test_empty_sources_when_no_tool_called(self, rag):
        rag.tool_manager.get_last_sources.return_value = []
        _, sources = rag.query("What is 2+2?", session_id="s1")
        assert sources == []

    def test_reset_sources_called_after_retrieval(self, rag):
        rag.query("test query", session_id="s1")
        rag.tool_manager.reset_sources.assert_called_once()

    def test_get_last_sources_called_before_reset(self, rag):
        """Verify get → reset order using call_count snapshots."""
        get_count_at_reset = []

        def side_effect_reset():
            get_count_at_reset.append(
                rag.tool_manager.get_last_sources.call_count
            )

        rag.tool_manager.reset_sources.side_effect = side_effect_reset
        rag.query("test", session_id="s1")
        # get_last_sources should have been called before reset_sources
        assert get_count_at_reset[0] == 1


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

class TestSessionManagement:
    def test_get_conversation_history_called_with_session_id(self, rag):
        rag.query("question", session_id="sess-42")
        rag.session_manager.get_conversation_history.assert_called_once_with("sess-42")

    def test_conversation_history_forwarded_to_ai_generator(self, rag):
        rag.session_manager.get_conversation_history.return_value = (
            "User: hi\nAssistant: hello"
        )
        rag.query("follow-up", session_id="s1")
        kwargs = rag.ai_generator.generate_response.call_args[1]
        assert kwargs["conversation_history"] == "User: hi\nAssistant: hello"

    def test_none_history_forwarded_when_new_session(self, rag):
        rag.session_manager.get_conversation_history.return_value = None
        rag.query("first question", session_id="s1")
        kwargs = rag.ai_generator.generate_response.call_args[1]
        assert kwargs["conversation_history"] is None

    def test_add_exchange_called_with_correct_args(self, rag):
        rag.ai_generator.generate_response.return_value = "my response"
        rag.query("user question", session_id="s1")
        rag.session_manager.add_exchange.assert_called_once_with(
            "s1", "user question", "my response"
        )

    def test_no_history_call_without_session_id(self, rag):
        rag.query("question without session")
        rag.session_manager.get_conversation_history.assert_not_called()

    def test_no_add_exchange_without_session_id(self, rag):
        rag.query("question without session")
        rag.session_manager.add_exchange.assert_not_called()

    def test_history_not_retrieved_when_session_id_is_none(self, rag):
        rag.query("test", session_id=None)
        rag.session_manager.get_conversation_history.assert_not_called()


# ---------------------------------------------------------------------------
# Tool registration at startup
# ---------------------------------------------------------------------------

class TestToolRegistration:
    def test_both_tools_registered_with_tool_manager(self):
        """CourseSearchTool and CourseOutlineTool must be registered on __init__."""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):
            system = RAGSystem(_make_mock_config())

        registered = set(system.tool_manager.tools.keys())
        assert "search_course_content" in registered, (
            "CourseSearchTool not registered — did you forget to call "
            "tool_manager.register_tool(self.search_tool)?"
        )
        assert "get_course_outline" in registered, (
            "CourseOutlineTool not registered — did you forget to call "
            "tool_manager.register_tool(self.outline_tool)?"
        )

    def test_search_tool_instance_stored(self):
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):
            system = RAGSystem(_make_mock_config())

        from search_tools import CourseSearchTool
        assert isinstance(system.search_tool, CourseSearchTool)

    def test_outline_tool_instance_stored(self):
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):
            system = RAGSystem(_make_mock_config())

        from search_tools import CourseOutlineTool
        assert isinstance(system.outline_tool, CourseOutlineTool)

"""
Tests for CourseSearchTool.execute() in search_tools.py.

Covers:
- Correct arguments forwarded to VectorStore.search()
- Output formatting (headers, content, multi-result joining)
- Error / empty-result messages
- Source tracking (last_sources) after each call
- Tool definition shape
"""

import pytest
from unittest.mock import MagicMock

from search_tools import CourseSearchTool
from vector_store import SearchResults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_results(docs, metas, distances=None):
    if distances is None:
        distances = [0.1] * len(docs)
    return SearchResults(documents=docs, metadata=metas, distances=distances)


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_lesson_link.return_value = None
    return store


@pytest.fixture
def tool(mock_store):
    return CourseSearchTool(mock_store)


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

class TestToolDefinition:
    def test_name_is_search_course_content(self, tool):
        assert tool.get_tool_definition()["name"] == "search_course_content"

    def test_query_is_required(self, tool):
        schema = tool.get_tool_definition()["input_schema"]
        assert "query" in schema["required"]

    def test_course_name_and_lesson_number_are_optional(self, tool):
        props = tool.get_tool_definition()["input_schema"]["properties"]
        assert "course_name" in props
        assert "lesson_number" in props
        required = tool.get_tool_definition()["input_schema"]["required"]
        assert "course_name" not in required
        assert "lesson_number" not in required


# ---------------------------------------------------------------------------
# Argument forwarding
# ---------------------------------------------------------------------------

class TestArgumentForwarding:
    def test_query_only_forwarded_correctly(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        tool.execute(query="what is recursion")
        mock_store.search.assert_called_once_with(
            query="what is recursion",
            course_name=None,
            lesson_number=None,
        )

    def test_course_name_forwarded(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        tool.execute(query="decorators", course_name="Python")
        mock_store.search.assert_called_once_with(
            query="decorators",
            course_name="Python",
            lesson_number=None,
        )

    def test_lesson_number_forwarded(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        tool.execute(query="loops", lesson_number=3)
        mock_store.search.assert_called_once_with(
            query="loops",
            course_name=None,
            lesson_number=3,
        )

    def test_all_args_forwarded(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        tool.execute(query="closures", course_name="Python Basics", lesson_number=5)
        mock_store.search.assert_called_once_with(
            query="closures",
            course_name="Python Basics",
            lesson_number=5,
        )


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

class TestOutputFormatting:
    def test_result_contains_course_title(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["Functions are reusable blocks of code."],
            metas=[{"course_title": "Python Basics", "lesson_number": 1}],
        )
        result = tool.execute(query="functions")
        assert "Python Basics" in result

    def test_result_contains_lesson_number(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["Functions are reusable blocks of code."],
            metas=[{"course_title": "Python Basics", "lesson_number": 1}],
        )
        result = tool.execute(query="functions")
        assert "Lesson 1" in result

    def test_result_contains_document_text(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["Functions are reusable blocks of code."],
            metas=[{"course_title": "Python Basics", "lesson_number": 1}],
        )
        result = tool.execute(query="functions")
        assert "Functions are reusable blocks of code." in result

    def test_multiple_results_all_included(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["content A", "content B"],
            metas=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
        )
        result = tool.execute(query="test")
        assert "content A" in result
        assert "content B" in result
        assert "Course A" in result
        assert "Course B" in result

    def test_multiple_results_separated_by_double_newline(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["content A", "content B"],
            metas=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
        )
        result = tool.execute(query="test")
        assert "\n\n" in result

    def test_header_format_includes_brackets(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["some content"],
            metas=[{"course_title": "My Course", "lesson_number": 2}],
        )
        result = tool.execute(query="test")
        assert "[My Course - Lesson 2]" in result

    def test_result_without_lesson_number_no_lesson_in_header(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["intro content"],
            metas=[{"course_title": "My Course", "lesson_number": None}],
        )
        result = tool.execute(query="test")
        assert "[My Course]" in result
        assert "Lesson" not in result


# ---------------------------------------------------------------------------
# Empty / error results
# ---------------------------------------------------------------------------

class TestEmptyAndErrorResults:
    def test_search_error_returns_error_message(self, tool, mock_store):
        mock_store.search.return_value = SearchResults.empty(
            "No course found matching 'XYZ'"
        )
        result = tool.execute(query="anything", course_name="XYZ")
        assert result == "No course found matching 'XYZ'"

    def test_empty_results_returns_not_found_message(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        result = tool.execute(query="something obscure")
        assert "No relevant content found" in result

    def test_empty_with_course_filter_mentions_course_in_message(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        result = tool.execute(query="topic", course_name="Python Basics")
        assert "Python Basics" in result

    def test_empty_with_lesson_filter_mentions_lesson_in_message(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        result = tool.execute(query="topic", lesson_number=5)
        assert "lesson 5" in result


# ---------------------------------------------------------------------------
# Source tracking
# ---------------------------------------------------------------------------

class TestSourceTracking:
    def test_last_sources_empty_before_first_call(self, tool):
        assert tool.last_sources == []

    def test_last_sources_populated_after_successful_search(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["content"],
            metas=[{"course_title": "My Course", "lesson_number": 2}],
        )
        mock_store.get_lesson_link.return_value = "https://example.com/l2"
        tool.execute(query="test")
        assert len(tool.last_sources) == 1

    def test_source_text_includes_course_and_lesson(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["content"],
            metas=[{"course_title": "My Course", "lesson_number": 2}],
        )
        mock_store.get_lesson_link.return_value = "https://example.com/l2"
        tool.execute(query="test")
        assert tool.last_sources[0]["text"] == "My Course - Lesson 2"

    def test_source_url_from_get_lesson_link(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["content"],
            metas=[{"course_title": "My Course", "lesson_number": 2}],
        )
        mock_store.get_lesson_link.return_value = "https://example.com/l2"
        tool.execute(query="test")
        assert tool.last_sources[0]["url"] == "https://example.com/l2"

    def test_source_without_lesson_number_has_no_lesson_suffix(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["content"],
            metas=[{"course_title": "My Course", "lesson_number": None}],
        )
        tool.execute(query="test")
        assert tool.last_sources[0]["text"] == "My Course"
        assert tool.last_sources[0]["url"] is None

    def test_source_url_is_none_when_no_lesson_number(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["content"],
            metas=[{"course_title": "My Course", "lesson_number": None}],
        )
        tool.execute(query="test")
        mock_store.get_lesson_link.assert_not_called()

    def test_multiple_results_produce_multiple_sources(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["doc1", "doc2"],
            metas=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
        )
        tool.execute(query="test")
        assert len(tool.last_sources) == 2

    def test_second_call_replaces_sources_not_appends(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            docs=["doc1"],
            metas=[{"course_title": "Course A", "lesson_number": 1}],
        )
        tool.execute(query="first")

        mock_store.search.return_value = make_results(
            docs=["doc2"],
            metas=[{"course_title": "Course B", "lesson_number": 3}],
        )
        tool.execute(query="second")

        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "Course B - Lesson 3"

    def test_empty_results_clears_last_sources(self, tool, mock_store):
        # First call populates sources
        mock_store.search.return_value = make_results(
            docs=["doc"],
            metas=[{"course_title": "Course A", "lesson_number": 1}],
        )
        tool.execute(query="first")
        assert len(tool.last_sources) == 1

        # Second call with empty results
        mock_store.search.return_value = make_results([], [])
        tool.execute(query="second")
        assert tool.last_sources == []

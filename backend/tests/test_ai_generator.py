"""
Tests for AIGenerator in ai_generator.py.

Covers:
- Direct (no-tool) responses returned as-is
- Tool call detection triggers tool_manager.execute_tool()
- Correct tool name and input passed to tool_manager
- Second API call structure: no tools, tool results included in messages
- System prompt presence and conversation history injection
- Temperature / max_tokens forwarded on both calls
"""

import pytest
from unittest.mock import MagicMock, patch, call

from ai_generator import AIGenerator


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def make_text_response(text="Here is my answer."):
    """Simulate a Claude response that ends with plain text."""
    response = MagicMock()
    response.stop_reason = "end_turn"
    block = MagicMock()
    block.type = "text"
    block.text = text
    response.content = [block]
    return response


def make_tool_use_response(tool_name, tool_input, tool_id="tu_abc123"):
    """Simulate a Claude response that requests a tool call."""
    response = MagicMock()
    response.stop_reason = "tool_use"
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_id
    response.content = [block]
    return response


@pytest.fixture
def generator():
    with patch("ai_generator.anthropic.Anthropic"):
        gen = AIGenerator(api_key="test-key", model="claude-test")
    gen.client = MagicMock()
    return gen


@pytest.fixture
def mock_tool_manager():
    tm = MagicMock()
    tm.execute_tool.return_value = "search results text"
    return tm


# ---------------------------------------------------------------------------
# Direct responses (no tool use)
# ---------------------------------------------------------------------------

class TestDirectResponses:
    def test_returns_text_when_no_tool_called(self, generator):
        generator.client.messages.create.return_value = make_text_response("42")
        result = generator.generate_response(query="What is 6 times 7?")
        assert result == "42"

    def test_only_one_api_call_for_direct_response(self, generator):
        generator.client.messages.create.return_value = make_text_response("answer")
        generator.generate_response(query="What is Python?")
        assert generator.client.messages.create.call_count == 1

    def test_query_included_in_user_message(self, generator):
        generator.client.messages.create.return_value = make_text_response()
        generator.generate_response(query="My unique query string")
        call_kwargs = generator.client.messages.create.call_args[1]
        messages = call_kwargs["messages"]
        assert any("My unique query string" in str(m["content"]) for m in messages)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

class TestSystemPrompt:
    def test_system_prompt_is_sent(self, generator):
        generator.client.messages.create.return_value = make_text_response()
        generator.generate_response(query="test")
        call_kwargs = generator.client.messages.create.call_args[1]
        assert "system" in call_kwargs

    def test_system_prompt_mentions_search_course_content(self, generator):
        generator.client.messages.create.return_value = make_text_response()
        generator.generate_response(query="test")
        call_kwargs = generator.client.messages.create.call_args[1]
        assert "search_course_content" in call_kwargs["system"]

    def test_system_prompt_mentions_get_course_outline(self, generator):
        generator.client.messages.create.return_value = make_text_response()
        generator.generate_response(query="test")
        call_kwargs = generator.client.messages.create.call_args[1]
        assert "get_course_outline" in call_kwargs["system"]

    def test_conversation_history_appended_to_system_prompt(self, generator):
        generator.client.messages.create.return_value = make_text_response()
        generator.generate_response(
            query="follow-up",
            conversation_history="User: hello\nAssistant: hi",
        )
        call_kwargs = generator.client.messages.create.call_args[1]
        assert "User: hello" in call_kwargs["system"]
        assert "Assistant: hi" in call_kwargs["system"]

    def test_no_history_does_not_add_none_to_system(self, generator):
        generator.client.messages.create.return_value = make_text_response()
        generator.generate_response(query="test", conversation_history=None)
        call_kwargs = generator.client.messages.create.call_args[1]
        assert "None" not in call_kwargs["system"]


# ---------------------------------------------------------------------------
# Tool definitions in first API call
# ---------------------------------------------------------------------------

class TestFirstCallTools:
    def test_tools_included_when_provided(self, generator):
        generator.client.messages.create.return_value = make_text_response()
        tools = [{"name": "search_course_content"}]
        generator.generate_response(query="test", tools=tools)
        call_kwargs = generator.client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == tools

    def test_tool_choice_auto_set(self, generator):
        generator.client.messages.create.return_value = make_text_response()
        tools = [{"name": "search_course_content"}]
        generator.generate_response(query="test", tools=tools)
        call_kwargs = generator.client.messages.create.call_args[1]
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_no_tools_key_when_no_tools_provided(self, generator):
        generator.client.messages.create.return_value = make_text_response()
        generator.generate_response(query="test")
        call_kwargs = generator.client.messages.create.call_args[1]
        assert "tools" not in call_kwargs


# ---------------------------------------------------------------------------
# Tool execution flow
# ---------------------------------------------------------------------------

class TestToolExecutionFlow:
    def test_tool_manager_execute_tool_called_with_correct_name(
        self, generator, mock_tool_manager
    ):
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "decorators"}),
            make_text_response("intermediate"),
            make_text_response("Here is what I found."),
        ]
        generator.generate_response(
            query="What are decorators?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        mock_tool_manager.execute_tool.assert_called_once()
        call_args = mock_tool_manager.execute_tool.call_args
        assert call_args[0][0] == "search_course_content"

    def test_tool_input_unpacked_as_kwargs(self, generator, mock_tool_manager):
        generator.client.messages.create.side_effect = [
            make_tool_use_response(
                "search_course_content",
                {"query": "closures", "course_name": "Python"},
            ),
            make_text_response("intermediate"),
            make_text_response("result"),
        ]
        generator.generate_response(
            query="closures in Python",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="closures", course_name="Python"
        )

    def test_final_response_text_returned(self, generator, mock_tool_manager):
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "test"}),
            make_text_response("intermediate"),
            make_text_response("Final synthesized answer."),
        ]
        result = generator.generate_response(
            query="test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert result == "Final synthesized answer."

    def test_three_api_calls_made_when_tool_used(self, generator, mock_tool_manager):
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "test"}),
            make_text_response("intermediate"),
            make_text_response("answer"),
        ]
        generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert generator.client.messages.create.call_count == 3


# ---------------------------------------------------------------------------
# Second API call structure
# ---------------------------------------------------------------------------

class TestSecondCallStructure:
    def _run_tool_flow(self, generator, mock_tool_manager, tool_id="tu_xyz"):
        generator.client.messages.create.side_effect = [
            make_tool_use_response(
                "search_course_content", {"query": "test"}, tool_id=tool_id
            ),
            make_text_response("intermediate"),  # intermediate call returns text → loop breaks
            make_text_response("answer"),         # synthesis
        ]
        generator.generate_response(
            query="test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        return generator.client.messages.create.call_args_list[-1][1]  # synthesis call

    def test_second_call_has_no_tools_key(self, generator, mock_tool_manager):
        second_kwargs = self._run_tool_flow(generator, mock_tool_manager)
        assert "tools" not in second_kwargs

    def test_second_call_has_no_tool_choice_key(self, generator, mock_tool_manager):
        second_kwargs = self._run_tool_flow(generator, mock_tool_manager)
        assert "tool_choice" not in second_kwargs

    def test_second_call_includes_system_prompt(self, generator, mock_tool_manager):
        second_kwargs = self._run_tool_flow(generator, mock_tool_manager)
        assert "system" in second_kwargs

    def test_second_call_messages_include_user_query(self, generator, mock_tool_manager):
        second_kwargs = self._run_tool_flow(generator, mock_tool_manager)
        messages = second_kwargs["messages"]
        assert any(
            m["role"] == "user" and "test query" in str(m["content"])
            for m in messages
        )

    def test_second_call_messages_include_assistant_tool_use(
        self, generator, mock_tool_manager
    ):
        second_kwargs = self._run_tool_flow(generator, mock_tool_manager)
        messages = second_kwargs["messages"]
        assert any(m["role"] == "assistant" for m in messages)

    def test_second_call_messages_include_tool_result(
        self, generator, mock_tool_manager
    ):
        mock_tool_manager.execute_tool.return_value = "search results here"
        second_kwargs = self._run_tool_flow(
            generator, mock_tool_manager, tool_id="tu_result_test"
        )
        messages = second_kwargs["messages"]
        tool_result_msg = next(
            (
                m
                for m in messages
                if m["role"] == "user" and isinstance(m["content"], list)
            ),
            None,
        )
        assert tool_result_msg is not None
        assert tool_result_msg["content"][0]["type"] == "tool_result"
        assert tool_result_msg["content"][0]["content"] == "search results here"

    def test_tool_result_id_matches_tool_use_id(self, generator, mock_tool_manager):
        second_kwargs = self._run_tool_flow(
            generator, mock_tool_manager, tool_id="tu_id_check"
        )
        messages = second_kwargs["messages"]
        tool_result_msg = next(
            m
            for m in messages
            if m["role"] == "user" and isinstance(m["content"], list)
        )
        assert tool_result_msg["content"][0]["tool_use_id"] == "tu_id_check"


# ---------------------------------------------------------------------------
# Sequential tool calling
# ---------------------------------------------------------------------------

class TestSequentialToolCalling:
    def test_one_tool_round_makes_three_api_calls(self, generator, mock_tool_manager):
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "test"}),
            make_text_response("intermediate"),
            make_text_response("final"),
        ]
        generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert generator.client.messages.create.call_count == 3

    def test_two_tool_rounds_makes_three_api_calls(self, generator, mock_tool_manager):
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "first"}, tool_id="tu_1"),
            make_tool_use_response("search_course_content", {"query": "second"}, tool_id="tu_2"),
            make_text_response("final"),
        ]
        generator.generate_response(
            query="compare two courses",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert generator.client.messages.create.call_count == 3

    def test_two_rounds_executes_tool_twice(self, generator, mock_tool_manager):
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "first"}, tool_id="tu_1"),
            make_tool_use_response("search_course_content", {"query": "second"}, tool_id="tu_2"),
            make_text_response("final"),
        ]
        generator.generate_response(
            query="compare two courses",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert mock_tool_manager.execute_tool.call_count == 2

    def test_second_round_tool_result_present_in_synthesis_messages(
        self, generator, mock_tool_manager
    ):
        mock_tool_manager.execute_tool.side_effect = ["result_1", "result_2"]
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "first"}, tool_id="tu_1"),
            make_tool_use_response("search_course_content", {"query": "second"}, tool_id="tu_2"),
            make_text_response("final"),
        ]
        generator.generate_response(
            query="compare two courses",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        synthesis_kwargs = generator.client.messages.create.call_args_list[2][1]
        messages_str = str(synthesis_kwargs["messages"])
        assert "result_1" in messages_str
        assert "result_2" in messages_str

    def test_intermediate_call_includes_tools(self, generator, mock_tool_manager):
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "test"}),
            make_text_response("intermediate"),
            make_text_response("final"),
        ]
        generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        intermediate_kwargs = generator.client.messages.create.call_args_list[1][1]
        assert "tools" in intermediate_kwargs

    def test_synthesis_call_has_no_tools(self, generator, mock_tool_manager):
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "first"}, tool_id="tu_1"),
            make_tool_use_response("search_course_content", {"query": "second"}, tool_id="tu_2"),
            make_text_response("final"),
        ]
        generator.generate_response(
            query="compare two courses",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        synthesis_kwargs = generator.client.messages.create.call_args_list[-1][1]
        assert "tools" not in synthesis_kwargs
        assert "tool_choice" not in synthesis_kwargs

    def test_final_text_returned_after_two_rounds(self, generator, mock_tool_manager):
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "first"}, tool_id="tu_1"),
            make_tool_use_response("search_course_content", {"query": "second"}, tool_id="tu_2"),
            make_text_response("Synthesized answer"),
        ]
        result = generator.generate_response(
            query="compare two courses",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert result == "Synthesized answer"


# ---------------------------------------------------------------------------
# Tool error handling
# ---------------------------------------------------------------------------

class TestToolErrorHandling:
    def test_tool_exception_does_not_propagate(self, generator, mock_tool_manager):
        mock_tool_manager.execute_tool.side_effect = RuntimeError("DB unavailable")
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "test"}),
            make_text_response("fallback answer"),
        ]
        result = generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert isinstance(result, str)

    def test_tool_error_string_in_synthesis_messages(self, generator, mock_tool_manager):
        mock_tool_manager.execute_tool.side_effect = RuntimeError("DB unavailable")
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "test"}),
            make_text_response("fallback answer"),
        ]
        generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        synthesis_kwargs = generator.client.messages.create.call_args_list[1][1]
        messages_str = str(synthesis_kwargs["messages"]).lower()
        assert "error" in messages_str

    def test_error_skips_intermediate_call(self, generator, mock_tool_manager):
        mock_tool_manager.execute_tool.side_effect = RuntimeError("DB unavailable")
        generator.client.messages.create.side_effect = [
            make_tool_use_response("search_course_content", {"query": "test"}),
            make_text_response("fallback answer"),
        ]
        generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert generator.client.messages.create.call_count == 2

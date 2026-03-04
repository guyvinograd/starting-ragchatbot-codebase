import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- **get_course_outline**: Use for outline, structure, or lesson list queries about a course.
  Returns the course title, link, and full numbered lesson list.
- **search_course_content**: Use for questions about specific course content or detailed material.
- **Sequential tool use**: You may make up to 2 separate tool calls if the first result reveals a need for additional information. Each tool result is available to you before deciding whether another search is needed.
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly

Outline Response Format:
When answering outline queries, always include: course title, course link (if available),
and the number and title of each lesson in order.

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    MAX_TOOL_ROUNDS = 2

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            messages = self._run_tool_loop(response, api_params, tools, tool_manager)
            final_params = {**self.base_params, "messages": messages, "system": system_content}
            final_response = self.client.messages.create(**final_params)
            return final_response.content[0].text

        # Return direct response
        return response.content[0].text

    def _run_tool_loop(self, initial_response, base_params: Dict[str, Any], tools, tool_manager):
        """
        Run up to MAX_TOOL_ROUNDS of tool execution, allowing Claude to make sequential
        tool calls. Returns accumulated messages ready for a final synthesis call.
        """
        messages = base_params["messages"].copy()
        current_response = initial_response

        for round_num in range(self.MAX_TOOL_ROUNDS):
            # Append Claude's tool-use content to history
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute every tool_use block in this response
            tool_results, had_error = self._run_tool_round(current_response, tool_manager)
            messages.append({"role": "user", "content": tool_results})

            # Stop if tool failed or we've used all rounds
            if had_error or round_num == self.MAX_TOOL_ROUNDS - 1:
                break

            # Intermediate call WITH tools — Claude may call another tool
            intermediate_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                "tools": tools,
                "tool_choice": {"type": "auto"},
            }
            next_response = self.client.messages.create(**intermediate_params)

            if next_response.stop_reason != "tool_use":
                # Claude returned text — append it and stop
                messages.append({"role": "assistant", "content": next_response.content})
                break

            current_response = next_response  # proceed to next round

        return messages

    def _run_tool_round(self, response, tool_manager):
        """
        Execute all tool_use blocks in a single response.
        Returns (tool_results list, had_error bool).
        """
        tool_results = []
        had_error = False
        for block in response.content:
            if block.type == "tool_use":
                try:
                    result = tool_manager.execute_tool(block.name, **block.input)
                except Exception as e:
                    result = f"Tool execution error: {e}"
                    had_error = True
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        return tool_results, had_error
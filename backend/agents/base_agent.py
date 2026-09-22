"""
NexusAI — ReAct Agent Engine.
Implements Reasoning + Acting loop with tool calling for multi-step task execution.
"""

import json
import logging
import re
from typing import Any, Callable

logger = logging.getLogger("nexus.agent")

SYSTEM_PROMPT = """You are NexusAI, an intelligent AI agent that can use tools to accomplish tasks.

When you need to use a tool, respond with a JSON block in this exact format:
```tool_call
{
  "tool": "tool_name",
  "args": {"arg1": "value1", "arg2": "value2"}
}
```

Available tools:
{tools_description}

RULES:
1. Think step by step about how to solve the user's request
2. Use tools when you need external information or to perform actions
3. After receiving tool results, analyze them and decide next steps
4. When you have enough information, provide a final answer
5. If a tool fails, try an alternative approach
6. Always explain your reasoning before using a tool

When you have the final answer, just respond normally without a tool_call block.
"""


class Tool:
    """Represents a callable tool for the agent."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        func: Callable,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_description(self) -> str:
        params = ", ".join(
            f'{k}: {v.get("type", "string")} - {v.get("description", "")}'
            for k, v in self.parameters.items()
        )
        return f"- **{self.name}**: {self.description}\n  Parameters: {params}"


class AgentStep:
    """Represents one step in the agent's execution."""

    def __init__(
        self,
        step_num: int,
        thought: str = "",
        tool_call: dict | None = None,
        tool_result: str | None = None,
        response: str = "",
    ):
        self.step_num = step_num
        self.thought = thought
        self.tool_call = tool_call
        self.tool_result = tool_result
        self.response = response

    def to_dict(self) -> dict:
        return {
            "step": self.step_num,
            "thought": self.thought,
            "tool_call": self.tool_call,
            "tool_result": self.tool_result,
            "response": self.response,
        }


class ReActAgent:
    """
    ReAct (Reasoning + Acting) agent.
    Maintains a conversation loop where the LLM can reason about tasks
    and call tools to gather information or perform actions.
    """

    def __init__(
        self,
        router,
        tools: list[Tool] | None = None,
        max_iterations: int = 10,
        provider: str | None = None,
        model: str | None = None,
    ):
        self.router = router
        self.tools: dict[str, Tool] = {}
        self.max_iterations = max_iterations
        self.provider = provider
        self.model = model
        self.steps: list[AgentStep] = []
        self.conversation: list[dict] = []

        if tools:
            for t in tools:
                self.register_tool(t)

    def register_tool(self, tool: Tool):
        self.tools[tool.name] = tool

    def _build_system_prompt(self) -> str:
        tools_desc = "\n".join(t.to_description() for t in self.tools.values())
        if not tools_desc:
            tools_desc = "No tools available. Respond based on your knowledge."
        return SYSTEM_PROMPT.format(tools_description=tools_desc)

    def _parse_tool_call(self, text: str) -> dict | None:
        """Extract a tool_call JSON block from the LLM's response."""
        # Look for ```tool_call ... ``` blocks
        pattern = r"```tool_call\s*\n?(.*?)\n?```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Fallback: look for raw JSON with "tool" key
        pattern2 = r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{.*?\}\s*\}'
        match2 = re.search(pattern2, text, re.DOTALL)
        if match2:
            try:
                return json.loads(match2.group(0))
            except json.JSONDecodeError:
                pass

        return None

    async def _execute_tool(self, tool_name: str, args: dict) -> str:
        """Execute a tool and return its result."""
        tool = self.tools.get(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found. Available: {list(self.tools.keys())}"

        try:
            import asyncio
            if asyncio.iscoroutinefunction(tool.func):
                result = await tool.func(**args)
            else:
                result = tool.func(**args)
            return str(result) if not isinstance(result, str) else result
        except Exception as e:
            return f"Tool error: {str(e)}"

    async def run(
        self,
        user_message: str,
        on_step: Callable[[AgentStep], Any] | None = None,
    ) -> str:
        """
        Execute the ReAct loop for a user request.

        Args:
            user_message: The user's task/question
            on_step: Optional callback for each step (for streaming progress)

        Returns:
            Final response text
        """
        self.steps = []
        system_prompt = self._build_system_prompt()

        self.conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        for iteration in range(self.max_iterations):
            step = AgentStep(step_num=iteration + 1)

            # Get LLM response
            try:
                response, used_provider, used_model = await self.router.chat(
                    messages=self.conversation,
                    model=self.model,
                    provider=self.provider,
                    stream=False,
                )
            except Exception as e:
                step.response = f"Error communicating with AI: {str(e)}"
                self.steps.append(step)
                if on_step:
                    on_step(step)
                return step.response

            # Check for tool call
            tool_call = self._parse_tool_call(response)

            if tool_call:
                tool_name = tool_call.get("tool", "")
                tool_args = tool_call.get("args", {})

                # Extract thought (text before tool call)
                tool_call_pos = response.find("```tool_call")
                if tool_call_pos == -1:
                    tool_call_pos = response.find('{"tool"')
                step.thought = response[:tool_call_pos].strip() if tool_call_pos > 0 else ""
                step.tool_call = tool_call

                logger.info(f"Step {iteration+1}: Calling tool '{tool_name}' with {tool_args}")

                # Execute tool
                tool_result = await self._execute_tool(tool_name, tool_args)
                step.tool_result = tool_result

                # Add to conversation
                self.conversation.append({"role": "assistant", "content": response})
                self.conversation.append({
                    "role": "user",
                    "content": f"Tool result for '{tool_name}':\n{tool_result}\n\nBased on this result, continue with your task. If you have enough information, provide your final answer.",
                })

            else:
                # No tool call = final response
                step.response = response
                self.steps.append(step)
                if on_step:
                    on_step(step)
                return response

            self.steps.append(step)
            if on_step:
                on_step(step)

        return "Agent reached maximum iterations without completing the task. Here's what I found so far:\n" + (
            self.steps[-1].response if self.steps else "No results."
        )

    def get_execution_log(self) -> list[dict]:
        return [s.to_dict() for s in self.steps]

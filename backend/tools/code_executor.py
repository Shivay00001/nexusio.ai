"""
NexusAI Tool — Python Code Executor (sandboxed subprocess with timeout).
"""

import asyncio
import sys
from backend.agents.base_agent import Tool


async def _execute_code(code: str, timeout: int = 30) -> str:
    """Execute Python code in a sandboxed subprocess."""
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            return f"Execution timed out after {timeout} seconds"

        output = ""
        if stdout:
            output += stdout.decode("utf-8", errors="replace")
        if stderr:
            output += "\n[STDERR]:\n" + stderr.decode("utf-8", errors="replace")

        exit_code = proc.returncode
        if exit_code != 0:
            output += f"\n[Exit code: {exit_code}]"

        return output.strip() if output.strip() else "(No output)"

    except Exception as e:
        return f"Execution error: {str(e)}"


code_exec_tool = Tool(
    name="execute_python",
    description="Execute Python code and return the output. Use this for calculations, data processing, or testing code snippets.",
    parameters={
        "code": {"type": "string", "description": "Python code to execute"},
        "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"},
    },
    func=_execute_code,
)

"""
NexusAI — Workflow Engine.
DAG-based workflow execution with sequential/parallel steps,
variable passing, and progress tracking.
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable

logger = logging.getLogger("nexus.workflow")


class WorkflowStep:
    """Represents a single step in a workflow."""

    def __init__(
        self,
        id: str,
        name: str,
        type: str = "ai_chat",  # ai_chat | tool | condition | parallel
        config: dict | None = None,
        depends_on: list[str] | None = None,
    ):
        self.id = id
        self.name = name
        self.type = type
        self.config = config or {}
        self.depends_on = depends_on or []
        self.status = "pending"  # pending | running | completed | failed | skipped
        self.result: Any = None
        self.error: str | None = None
        self.duration_ms: float = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "config": self.config,
            "depends_on": self.depends_on,
            "status": self.status,
            "result": self.result if isinstance(self.result, (str, dict, list, int, float, type(None))) else str(self.result),
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class Workflow:
    """Represents a DAG of workflow steps."""

    def __init__(self, id: str, name: str, description: str = ""):
        self.id = id
        self.name = name
        self.description = description
        self.steps: dict[str, WorkflowStep] = {}
        self.variables: dict[str, Any] = {}

    def add_step(self, step: WorkflowStep):
        self.steps[step.id] = step

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": {sid: s.to_dict() for sid, s in self.steps.items()},
            "variables": {k: str(v)[:200] for k, v in self.variables.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Workflow":
        wf = cls(
            id=data.get("id", ""),
            name=data.get("name", "Workflow"),
            description=data.get("description", ""),
        )
        for sid, sdata in data.get("steps", {}).items():
            step = WorkflowStep(
                id=sid,
                name=sdata.get("name", sid),
                type=sdata.get("type", "ai_chat"),
                config=sdata.get("config", {}),
                depends_on=sdata.get("depends_on", []),
            )
            wf.add_step(step)
        return wf


class WorkflowEngine:
    """Executes workflow DAGs with dependency resolution."""

    def __init__(self, router, tools=None):
        self.router = router
        self.tools = {t.name: t for t in (tools or [])}

    def _interpolate(self, text: str, variables: dict) -> str:
        """Replace {{var}} placeholders with variable values."""
        for key, value in variables.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text

    def _get_ready_steps(self, workflow: Workflow) -> list[WorkflowStep]:
        """Find steps whose dependencies are all completed."""
        ready = []
        for step in workflow.steps.values():
            if step.status != "pending":
                continue
            deps_met = all(
                workflow.steps[dep].status == "completed"
                for dep in step.depends_on
                if dep in workflow.steps
            )
            if deps_met:
                ready.append(step)
        return ready

    async def _execute_step(
        self, step: WorkflowStep, workflow: Workflow
    ) -> Any:
        """Execute a single workflow step."""
        start = time.monotonic()
        step.status = "running"

        try:
            if step.type == "ai_chat":
                prompt = self._interpolate(
                    step.config.get("prompt", ""), workflow.variables
                )
                provider = step.config.get("provider")
                model = step.config.get("model")

                response, used_provider, used_model = await self.router.chat(
                    messages=[{"role": "user", "content": prompt}],
                    provider=provider,
                    model=model,
                    stream=False,
                )
                result = response

            elif step.type == "tool":
                tool_name = step.config.get("tool", "")
                tool = self.tools.get(tool_name)
                if not tool:
                    raise ValueError(f"Tool '{tool_name}' not found")

                args = {}
                for k, v in step.config.get("args", {}).items():
                    args[k] = self._interpolate(str(v), workflow.variables)

                if asyncio.iscoroutinefunction(tool.func):
                    result = await tool.func(**args)
                else:
                    result = tool.func(**args)

            elif step.type == "condition":
                condition = self._interpolate(
                    step.config.get("condition", "true"), workflow.variables
                )
                # Simple evaluation (safe: only checks truth/contains)
                check_var = step.config.get("check_variable", "")
                check_contains = step.config.get("contains", "")
                var_value = str(workflow.variables.get(check_var, ""))
                if check_contains:
                    result = check_contains.lower() in var_value.lower()
                else:
                    result = bool(var_value)

                # Skip dependent steps if condition is False
                if not result:
                    skip_steps = step.config.get("skip_on_false", [])
                    for skip_id in skip_steps:
                        if skip_id in workflow.steps:
                            workflow.steps[skip_id].status = "skipped"

            elif step.type == "transform":
                # Apply simple transformations
                source_var = step.config.get("source", "")
                operation = step.config.get("operation", "passthrough")
                value = str(workflow.variables.get(source_var, ""))

                if operation == "uppercase":
                    result = value.upper()
                elif operation == "lowercase":
                    result = value.lower()
                elif operation == "truncate":
                    max_len = step.config.get("max_length", 500)
                    result = value[:max_len]
                elif operation == "split_first_line":
                    result = value.split("\n")[0]
                else:
                    result = value

            else:
                result = f"Unknown step type: {step.type}"

            step.status = "completed"
            step.result = result
            step.duration_ms = (time.monotonic() - start) * 1000

            # Store result as variable
            output_var = step.config.get("output_variable", step.id)
            workflow.variables[output_var] = result

            return result

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.duration_ms = (time.monotonic() - start) * 1000
            logger.error(f"Step {step.id} failed: {e}")
            raise

    async def execute(
        self,
        workflow: Workflow,
        on_progress: Callable[[dict], Any] | None = None,
    ) -> dict:
        """
        Execute a workflow with DAG-based dependency resolution.
        Steps without dependencies run in parallel.
        """
        total_steps = len(workflow.steps)
        completed = 0

        while True:
            ready = self._get_ready_steps(workflow)
            if not ready:
                break

            # Execute ready steps in parallel
            tasks = [
                self._execute_step(step, workflow)
                for step in ready
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for step, result in zip(ready, results):
                if isinstance(result, Exception):
                    step.status = "failed"
                    step.error = str(result)
                completed += 1

                if on_progress:
                    on_progress({
                        "step_id": step.id,
                        "step_name": step.name,
                        "status": step.status,
                        "progress": completed / total_steps,
                        "result": str(step.result)[:200] if step.result else None,
                    })

        return workflow.to_dict()

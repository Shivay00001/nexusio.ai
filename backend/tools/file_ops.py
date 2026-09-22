"""
NexusAI Tool — File Operations (sandboxed to workspace).
"""

import os
from pathlib import Path
from backend.agents.base_agent import Tool
from backend.config import config


def _safe_path(filepath: str) -> Path:
    """Ensure path is within workspace."""
    workspace = Path(config.WORKSPACE_DIR).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    target = (workspace / filepath).resolve()
    if not str(target).startswith(str(workspace)):
        raise ValueError("Access denied: path outside workspace")
    return target


async def _file_read(filepath: str) -> str:
    """Read a file from the workspace."""
    target = _safe_path(filepath)
    if not target.exists():
        return f"File not found: {filepath}"
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        if len(content) > 10000:
            content = content[:10000] + "\n\n... [truncated, file is too large]"
        return content
    except Exception as e:
        return f"Error reading file: {e}"


async def _file_write(filepath: str, content: str) -> str:
    """Write content to a file in the workspace."""
    target = _safe_path(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} chars to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"


async def _file_list(directory: str = ".") -> str:
    """List files in a workspace directory."""
    target = _safe_path(directory)
    if not target.is_dir():
        return f"Not a directory: {directory}"
    items = []
    for item in sorted(target.iterdir()):
        icon = "📁" if item.is_dir() else "📄"
        size = f" ({item.stat().st_size} bytes)" if item.is_file() else ""
        items.append(f"{icon} {item.name}{size}")
    return "\n".join(items) if items else "Empty directory"


file_read_tool = Tool(
    name="file_read",
    description="Read the contents of a file from the workspace directory.",
    parameters={
        "filepath": {"type": "string", "description": "Relative path to the file"},
    },
    func=_file_read,
)

file_write_tool = Tool(
    name="file_write",
    description="Write content to a file in the workspace directory. Creates directories if needed.",
    parameters={
        "filepath": {"type": "string", "description": "Relative path for the file"},
        "content": {"type": "string", "description": "Content to write"},
    },
    func=_file_write,
)

file_list_tool = Tool(
    name="file_list",
    description="List files and directories in the workspace.",
    parameters={
        "directory": {"type": "string", "description": "Relative directory path (default: root)"},
    },
    func=_file_list,
)

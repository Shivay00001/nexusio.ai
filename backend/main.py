"""
NexusAI — FastAPI Server.
REST + WebSocket API for chat, agents, workflows, and provider management.
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from backend.config import config
from backend.storage.db import db
from backend.router.smart_router import router as ai_router
from backend.agents.base_agent import ReActAgent
from backend.tools import ALL_TOOLS
from backend.workflows.engine import WorkflowEngine, Workflow
from backend.workflows.templates import TEMPLATES

# ── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO if config.DEBUG else logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("nexus.server")


# ── Lifespan ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 NexusAI starting up...")
    await db.connect()
    logger.info("✅ Database connected")
    await ai_router.refresh_health(force=True)
    logger.info("✅ Provider health checks complete")
    # Ensure workspace exists
    Path(config.WORKSPACE_DIR).mkdir(parents=True, exist_ok=True)
    yield
    await db.close()
    logger.info("🛑 NexusAI shut down")


# ── App ─────────────────────────────────────────────────────
app = FastAPI(
    title="NexusAI",
    description="Multi-Provider AI Agent & Automation System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ─────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


class AgentRequest(BaseModel):
    task: str
    session_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[list[str]] = None


class WorkflowRequest(BaseModel):
    workflow_id: Optional[str] = None
    template: Optional[str] = None
    variables: dict = {}


class ProviderConfigRequest(BaseModel):
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    enabled: bool = True


# ═══════════════════════════════════════════════════════════════
#   REST API ENDPOINTS
# ═══════════════════════════════════════════════════════════════


# ── Health ──────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ── Providers ───────────────────────────────────────────────
@app.get("/api/providers")
async def list_providers():
    """List all providers with health status."""
    return {"providers": ai_router.list_providers()}


@app.post("/api/providers/{name}/health")
async def check_provider_health(name: str):
    """Trigger health check for a specific provider."""
    provider = ai_router.get_provider(name)
    if not provider:
        raise HTTPException(404, f"Provider '{name}' not found")
    result = await provider.health_check()
    ai_router._health_cache[name] = result
    return result


@app.post("/api/providers/refresh")
async def refresh_all_health():
    """Refresh health status for all providers."""
    await ai_router.refresh_health(force=True)
    return {"providers": ai_router.list_providers()}


@app.get("/api/models")
async def list_all_models():
    """List models from all providers."""
    return await ai_router.list_all_models()


@app.get("/api/models/{provider_name}")
async def list_provider_models(provider_name: str):
    """List models from a specific provider."""
    provider = ai_router.get_provider(provider_name)
    if not provider:
        raise HTTPException(404, f"Provider '{provider_name}' not found")
    return {"models": await provider.list_models()}


# ── Chat ────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Send a chat message and get a response."""
    # Create or get conversation
    if req.conversation_id:
        conv_id = req.conversation_id
    else:
        conv = await db.create_conversation(
            title=req.message[:50] + "..." if len(req.message) > 50 else req.message,
            provider=req.provider or "",
            model=req.model or "",
        )
        conv_id = conv["id"]

    # Save user message
    await db.add_message(conv_id, "user", req.message)

    # Get conversation history
    messages = await db.get_messages(conv_id)
    chat_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
    ]

    # Route to AI
    try:
        response, used_provider, used_model = await ai_router.chat(
            messages=chat_messages,
            provider=req.provider,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            stream=False,
        )

        # Save assistant message
        await db.add_message(
            conv_id, "assistant", response,
            provider=used_provider, model=used_model,
        )

        return {
            "conversation_id": conv_id,
            "response": response,
            "provider": used_provider,
            "model": used_model,
        }

    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")


@app.get("/api/conversations")
async def list_conversations():
    return {"conversations": await db.list_conversations()}


@app.get("/api/conversations/{conv_id}/messages")
async def get_conversation_messages(conv_id: str):
    return {"messages": await db.get_messages(conv_id)}


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    await db.delete_conversation(conv_id)
    return {"ok": True}


# ── Agents ──────────────────────────────────────────────────
@app.post("/api/agent/run")
async def run_agent(req: AgentRequest):
    """Run the AI agent on a task with tools."""
    # Filter tools if specified
    if req.tools:
        tools = [t for t in ALL_TOOLS if t.name in req.tools]
    else:
        tools = ALL_TOOLS

    agent = ReActAgent(
        router=ai_router,
        tools=tools,
        provider=req.provider,
        model=req.model,
    )

    # Create session
    session = await db.create_agent_session(
        name=req.task[:50],
        provider=req.provider or "",
        model=req.model or "",
        tools=[t.name for t in tools],
    )

    steps_log = []
    def on_step(step):
        steps_log.append(step.to_dict())

    try:
        await db.update_agent_session(session["id"], status="running")
        result = await agent.run(req.task, on_step=on_step)
        await db.update_agent_session(
            session["id"],
            status="completed",
            history=agent.get_execution_log(),
        )

        return {
            "session_id": session["id"],
            "result": result,
            "steps": steps_log,
            "provider": agent.provider,
        }

    except Exception as e:
        await db.update_agent_session(session["id"], status="failed")
        raise HTTPException(500, f"Agent failed: {str(e)}")


@app.get("/api/agent/sessions")
async def list_agent_sessions():
    return {"sessions": await db.list_agent_sessions()}


@app.get("/api/agent/sessions/{session_id}")
async def get_agent_session(session_id: str):
    session = await db.get_agent_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@app.get("/api/agent/tools")
async def list_tools():
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in ALL_TOOLS
        ]
    }


# ── Workflows ───────────────────────────────────────────────
@app.get("/api/workflows/templates")
async def list_workflow_templates():
    return {"templates": {k: {"name": v["name"], "description": v["description"]} for k, v in TEMPLATES.items()}}


@app.post("/api/workflows/run")
async def run_workflow(req: WorkflowRequest):
    """Execute a workflow from a template or saved definition."""
    if req.template and req.template in TEMPLATES:
        template = TEMPLATES[req.template]
        workflow = Workflow.from_dict({
            "id": req.template,
            "name": template["name"],
            "description": template["description"],
            "steps": template["steps"],
        })
    elif req.workflow_id:
        wf_data = await db.get_workflow(req.workflow_id)
        if not wf_data:
            raise HTTPException(404, "Workflow not found")
        workflow = Workflow.from_dict(wf_data["definition"])
    else:
        raise HTTPException(400, "Provide either 'template' or 'workflow_id'")

    # Set initial variables
    workflow.variables.update(req.variables)

    # Create workflow engine
    engine = WorkflowEngine(router=ai_router, tools=ALL_TOOLS)

    # Save run
    run = await db.save_workflow_run(workflow.id, status="running")

    progress_updates = []
    def on_progress(update):
        progress_updates.append(update)

    try:
        result = await engine.execute(workflow, on_progress=on_progress)
        await db.update_workflow_run(run["id"], "completed", result)
        return {
            "run_id": run["id"],
            "status": "completed",
            "result": result,
            "progress": progress_updates,
        }
    except Exception as e:
        await db.update_workflow_run(run["id"], "failed", {"error": str(e)})
        raise HTTPException(500, f"Workflow failed: {str(e)}")


@app.get("/api/workflows")
async def list_workflows():
    return {"workflows": await db.list_workflows()}


@app.post("/api/workflows/save")
async def save_workflow(data: dict):
    result = await db.save_workflow(
        name=data.get("name", "Custom Workflow"),
        description=data.get("description", ""),
        definition=data.get("definition", {}),
    )
    return result


# ═══════════════════════════════════════════════════════════════
#   WEBSOCKET for Streaming
# ═══════════════════════════════════════════════════════════════


@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    """WebSocket endpoint for streaming chat responses."""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            messages = data.get("messages", [])
            provider = data.get("provider")
            model = data.get("model")
            conv_id = data.get("conversation_id")

            try:
                result, used_provider, used_model = await ai_router.chat(
                    messages=messages,
                    provider=provider,
                    model=model,
                    stream=True,
                )

                # Stream chunks
                if hasattr(result, "__aiter__"):
                    full_response = ""
                    async for chunk in result:
                        full_response += chunk
                        await ws.send_json({
                            "type": "chunk",
                            "content": chunk,
                            "provider": used_provider,
                            "model": used_model,
                        })
                    await ws.send_json({
                        "type": "done",
                        "content": full_response,
                        "provider": used_provider,
                        "model": used_model,
                    })
                else:
                    await ws.send_json({
                        "type": "done",
                        "content": result,
                        "provider": used_provider,
                        "model": used_model,
                    })

                # Save to DB
                if conv_id:
                    final_content = full_response if hasattr(result, "__aiter__") else result
                    await db.add_message(
                        conv_id, "assistant", final_content,
                        provider=used_provider, model=used_model,
                    )

            except Exception as e:
                await ws.send_json({
                    "type": "error",
                    "content": str(e),
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


@app.websocket("/ws/agent")
async def websocket_agent(ws: WebSocket):
    """WebSocket endpoint for streaming agent execution."""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            task = data.get("task", "")
            provider = data.get("provider")
            model = data.get("model")
            tool_names = data.get("tools")

            tools = ALL_TOOLS
            if tool_names:
                tools = [t for t in ALL_TOOLS if t.name in tool_names]

            agent = ReActAgent(
                router=ai_router,
                tools=tools,
                provider=provider,
                model=model,
            )

            async def on_step_async(step):
                await ws.send_json({
                    "type": "step",
                    "data": step.to_dict(),
                })

            # Run agent with step-by-step streaming
            def on_step(step):
                asyncio.create_task(on_step_async(step))

            result = await agent.run(task, on_step=on_step)
            await ws.send_json({
                "type": "done",
                "result": result,
                "steps": agent.get_execution_log(),
            })

    except WebSocketDisconnect:
        logger.info("Agent WebSocket client disconnected")


# ── Static Frontend ─────────────────────────────────────────
frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


# ── Run ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
    )

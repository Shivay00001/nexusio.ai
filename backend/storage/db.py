"""
NexusAI — SQLite persistence layer.
Stores chat history, workflow definitions, provider configs, and agent sessions.
"""

import aiosqlite
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from backend.config import config


class Database:
    """Async SQLite database manager."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or config.DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._create_tables()

    async def close(self):
        if self._db:
            await self._db.close()

    async def _create_tables(self):
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL DEFAULT 'New Chat',
                provider    TEXT,
                model       TEXT,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role            TEXT NOT NULL,  -- user | assistant | system | tool
                content         TEXT NOT NULL,
                provider        TEXT,
                model           TEXT,
                metadata        TEXT,           -- JSON blob
                created_at      TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS workflows (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT,
                definition  TEXT NOT NULL,      -- JSON DAG definition
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_runs (
                id          TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',  -- pending | running | completed | failed
                result      TEXT,               -- JSON result
                started_at  TEXT,
                finished_at TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS agent_sessions (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL DEFAULT 'Agent Session',
                provider    TEXT,
                model       TEXT,
                tools       TEXT,               -- JSON list of enabled tools
                status      TEXT NOT NULL DEFAULT 'idle',
                history     TEXT,               -- JSON conversation
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS provider_configs (
                provider_name TEXT PRIMARY KEY,
                enabled       INTEGER NOT NULL DEFAULT 1,
                api_key       TEXT,
                base_url      TEXT,
                default_model TEXT,
                extra         TEXT               -- JSON
            );
            """
        )
        await self._db.commit()

    # ── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _id() -> str:
        return uuid.uuid4().hex[:12]

    # ── Conversations ───────────────────────────────────────

    async def create_conversation(
        self, title: str = "New Chat", provider: str = "", model: str = ""
    ) -> dict:
        cid = self._id()
        now = self._now()
        await self._db.execute(
            "INSERT INTO conversations VALUES (?,?,?,?,?,?)",
            (cid, title, provider, model, now, now),
        )
        await self._db.commit()
        return {"id": cid, "title": title, "provider": provider, "model": model,
                "created_at": now, "updated_at": now}

    async def list_conversations(self, limit: int = 50) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def delete_conversation(self, cid: str):
        await self._db.execute("DELETE FROM conversations WHERE id=?", (cid,))
        await self._db.commit()

    # ── Messages ────────────────────────────────────────────

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        provider: str = "",
        model: str = "",
        metadata: dict | None = None,
    ) -> dict:
        mid = self._id()
        now = self._now()
        await self._db.execute(
            "INSERT INTO messages VALUES (?,?,?,?,?,?,?,?)",
            (mid, conversation_id, role, content, provider, model,
             json.dumps(metadata or {}), now),
        )
        await self._db.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (now, conversation_id),
        )
        await self._db.commit()
        return {"id": mid, "conversation_id": conversation_id, "role": role,
                "content": content, "provider": provider, "model": model,
                "metadata": metadata or {}, "created_at": now}

    async def get_messages(self, conversation_id: str) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at",
            (conversation_id,),
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["metadata"] = json.loads(d.get("metadata") or "{}")
            result.append(d)
        return result

    # ── Workflows ───────────────────────────────────────────

    async def save_workflow(self, name: str, description: str, definition: dict) -> dict:
        wid = self._id()
        now = self._now()
        await self._db.execute(
            "INSERT INTO workflows VALUES (?,?,?,?,?,?)",
            (wid, name, description, json.dumps(definition), now, now),
        )
        await self._db.commit()
        return {"id": wid, "name": name, "description": description,
                "definition": definition, "created_at": now}

    async def list_workflows(self) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM workflows ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["definition"] = json.loads(d.get("definition") or "{}")
            result.append(d)
        return result

    async def get_workflow(self, wid: str) -> dict | None:
        cursor = await self._db.execute("SELECT * FROM workflows WHERE id=?", (wid,))
        row = await cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["definition"] = json.loads(d.get("definition") or "{}")
        return d

    async def save_workflow_run(
        self, workflow_id: str, status: str = "pending", result: dict | None = None
    ) -> dict:
        rid = self._id()
        now = self._now()
        await self._db.execute(
            "INSERT INTO workflow_runs VALUES (?,?,?,?,?,?)",
            (rid, workflow_id, status, json.dumps(result) if result else None,
             now if status == "running" else None, None),
        )
        await self._db.commit()
        return {"id": rid, "workflow_id": workflow_id, "status": status}

    async def update_workflow_run(self, rid: str, status: str, result: dict | None = None):
        now = self._now()
        finished = now if status in ("completed", "failed") else None
        await self._db.execute(
            "UPDATE workflow_runs SET status=?, result=?, finished_at=? WHERE id=?",
            (status, json.dumps(result) if result else None, finished, rid),
        )
        await self._db.commit()

    # ── Agent Sessions ──────────────────────────────────────

    async def create_agent_session(
        self, name: str = "Agent Session", provider: str = "", model: str = "",
        tools: list[str] | None = None,
    ) -> dict:
        sid = self._id()
        now = self._now()
        await self._db.execute(
            "INSERT INTO agent_sessions VALUES (?,?,?,?,?,?,?,?,?)",
            (sid, name, provider, model, json.dumps(tools or []),
             "idle", json.dumps([]), now, now),
        )
        await self._db.commit()
        return {"id": sid, "name": name, "status": "idle"}

    async def get_agent_session(self, sid: str) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM agent_sessions WHERE id=?", (sid,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["tools"] = json.loads(d.get("tools") or "[]")
        d["history"] = json.loads(d.get("history") or "[]")
        return d

    async def update_agent_session(self, sid: str, **kwargs):
        now = self._now()
        sets = ["updated_at=?"]
        vals = [now]
        for k, v in kwargs.items():
            if k in ("status", "name", "provider", "model"):
                sets.append(f"{k}=?")
                vals.append(v)
            elif k in ("tools", "history"):
                sets.append(f"{k}=?")
                vals.append(json.dumps(v))
        vals.append(sid)
        await self._db.execute(
            f"UPDATE agent_sessions SET {','.join(sets)} WHERE id=?", vals
        )
        await self._db.commit()

    async def list_agent_sessions(self) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT id, name, provider, model, status, created_at, updated_at "
            "FROM agent_sessions ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# Singleton
db = Database()

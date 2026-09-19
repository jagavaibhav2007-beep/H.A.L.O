"""H.A.L.O. ownership boundary for LangGraph checkpoint persistence.

LangGraph remains the execution engine in this release. This adapter confines
its saver lifecycle and the two schema-dependent maintenance queries H.A.L.O.
needs (open-interrupt lookup and bounded retention) so graph.py does not reach
through the framework's objects or aiosqlite internals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command


class CheckpointCompatibilityError(RuntimeError):
    """The pinned LangGraph saver schema no longer matches H.A.L.O.'s adapter."""


class CheckpointStore:
    _REQUIRED_COLUMNS = {
        "checkpoints": {"thread_id", "checkpoint_id"},
        "writes": {"thread_id", "checkpoint_id", "channel"},
    }

    def __init__(self, path: Path) -> None:
        self.path = path
        self._context = None
        self.saver: AsyncSqliteSaver | None = None

    @classmethod
    async def open(cls, path: Path) -> "CheckpointStore":
        store = cls(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        store._context = AsyncSqliteSaver.from_conn_string(str(path))
        store.saver = await store._context.__aenter__()
        try:
            await store.saver.setup()
            await store._validate_schema()
        except BaseException:
            await store.close()
            raise
        return store

    def _require_saver(self) -> AsyncSqliteSaver:
        if self.saver is None:
            raise RuntimeError("checkpoint store is closed")
        return self.saver

    async def _validate_schema(self) -> None:
        saver = self._require_saver()
        for table, required in self._REQUIRED_COLUMNS.items():
            async with saver.conn.execute(f"PRAGMA table_info({table})") as cursor:
                present = {row[1] async for row in cursor}
            missing = required - present
            if missing:
                names = ", ".join(sorted(missing))
                raise CheckpointCompatibilityError(
                    f"LangGraph checkpoint table {table!r} is incompatible; "
                    f"missing columns: {names}. Restore the locked dependencies "
                    "or migrate checkpoints with a supported H.A.L.O. release."
                )

    @staticmethod
    def config(conversation_id: str, *, recursion_limit: int | None = None) -> dict:
        config: dict[str, Any] = {"configurable": {"thread_id": conversation_id}}
        if recursion_limit is not None:
            config["recursion_limit"] = recursion_limit
        return config

    def compile(self, builder):
        return builder.compile(checkpointer=self._require_saver())

    async def snapshot(self, graph, conversation_id: str):
        return await graph.aget_state(self.config(conversation_id))

    async def update(self, graph, conversation_id: str, values: dict) -> None:
        await graph.aupdate_state(self.config(conversation_id), values)

    async def resume(
        self,
        graph,
        conversation_id: str,
        value: dict,
        *,
        recursion_limit: int | None = None,
    ) -> dict:
        return await graph.ainvoke(
            Command(resume=value),
            self.config(conversation_id, recursion_limit=recursion_limit),
        )

    async def open_interrupt_threads(self) -> list[str]:
        """Return threads whose latest checkpoint has an unresolved interrupt.

        LangGraph exposes individual snapshots publicly but has no API for this
        bounded enumeration. Keep the pinned SQLite schema dependency here and
        validate it on open; callers still confirm each snapshot's interrupts.
        """
        saver = self._require_saver()
        query = (
            "SELECT DISTINCT w.thread_id FROM writes w "
            "WHERE w.channel = '__interrupt__' AND w.checkpoint_id = ("
            "  SELECT checkpoint_id FROM checkpoints ck WHERE ck.thread_id = w.thread_id "
            "  ORDER BY checkpoint_id DESC LIMIT 1)"
        )
        async with saver.lock, saver.conn.execute(query) as cursor:
            return [row[0] async for row in cursor]

    async def prune(self, conversation_id: str, *, keep: int) -> int:
        if keep < 1:
            raise ValueError("checkpoint retention must keep at least one checkpoint")
        saver = self._require_saver()
        keep_query = (
            "SELECT checkpoint_id FROM checkpoints WHERE thread_id = ? "
            "ORDER BY checkpoint_id DESC LIMIT ?"
        )
        async with saver.lock:
            await saver.conn.execute(
                f"DELETE FROM writes WHERE thread_id = ? AND checkpoint_id NOT IN ({keep_query})",
                (conversation_id, conversation_id, keep),
            )
            cursor = await saver.conn.execute(
                f"DELETE FROM checkpoints WHERE thread_id = ? AND checkpoint_id NOT IN ({keep_query})",
                (conversation_id, conversation_id, keep),
            )
            await saver.conn.commit()
        return cursor.rowcount

    async def close(self) -> None:
        context, self._context = self._context, None
        self.saver = None
        if context is not None:
            await context.__aexit__(None, None, None)

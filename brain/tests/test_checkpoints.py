"""Compatibility contract for H.A.L.O.'s LangGraph checkpoint adapter."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from brain.checkpoints import CheckpointStore


class State(TypedDict):
    value: int
    suspend: bool


def node(state: State) -> State:
    if state.get("suspend"):
        interrupt({"approval_id": f"approval-{state['value']}"})
    return {"value": state["value"] + 1, "suspend": False}


def build(store: CheckpointStore):
    builder = StateGraph(State)
    builder.add_node("node", node)
    builder.add_edge(START, "node")
    builder.add_edge("node", END)
    return store.compile(builder)


async def check_adapter() -> None:
    with tempfile.TemporaryDirectory(prefix="halo-checkpoint-adapter-") as folder:
        path = Path(folder) / "checkpoints.db"
        store = await CheckpointStore.open(path)
        graph = build(store)

        for index in range(12):
            await graph.ainvoke(
                {"value": index, "suspend": False},
                store.config(f"plain-{index}"),
            )
        for index in range(3):
            await graph.ainvoke(
                {"value": index, "suspend": True},
                store.config(f"interrupt-{index}"),
            )

        assert set(await store.open_interrupt_threads()) == {
            "interrupt-0", "interrupt-1", "interrupt-2",
        }
        snap = await store.snapshot(graph, "interrupt-1")
        assert snap.interrupts[0].value["approval_id"] == "approval-1"
        await store.resume(graph, "interrupt-1", {"decision": "approve"})
        assert set(await store.open_interrupt_threads()) == {
            "interrupt-0", "interrupt-2",
        }

        for value in range(30):
            await graph.ainvoke(
                {"value": value, "suspend": False},
                store.config("history"),
            )
        assert await store.prune("history", keep=3) > 0
        before = await store.snapshot(graph, "history")
        await store.close()

        reopened = await CheckpointStore.open(path)
        reopened_graph = build(reopened)
        after = await reopened.snapshot(reopened_graph, "history")
        assert after.values == before.values
        await reopened.close()

    print("[checkpoints] lifecycle, persistence, interrupts, resume and pruning: OK")


if __name__ == "__main__":
    asyncio.run(check_adapter())

"""Serialise the target message for text-only products. Never normalises content."""
from __future__ import annotations


def to_text(messages: list[dict], target: int) -> str:
    m = messages[target]
    parts = []
    if m.get("content"):
        parts.append(m["content"])
    for tc in m.get("tool_calls") or []:
        f = tc["function"]
        parts.append(f"{f['name']}({f['arguments']})")
    return "\n".join(parts)


def mode_for(adapter, case) -> str | None:
    if case.checkpoint in adapter.native_checkpoints:
        return "native"
    return "flattened" if adapter.accepts_text else None

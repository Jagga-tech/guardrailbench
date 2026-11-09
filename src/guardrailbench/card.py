"""The one plain-text rendering of a deployment card, shared by every adapter that hands the card to a product
as text. One rendering for all products is the fairness rule: no product gets a card worded to suit it.

An empty string or list in a card means "not stated" (see case.py), never "nothing allowed". So a field that is
not stated produces no line at all, and a null or all-empty card renders as "". Adapters must treat "" as "no
card": same input as the no-context track.
"""
from __future__ import annotations


def _items(card: dict | None, key: str) -> list[str]:
    return [x.strip() for x in (card or {}).get(key) or [] if x.strip()]


def stated_tools(card: dict | None) -> list[str]:
    """Tool names the card states as allowed. [] means not stated: do not build a restriction from it."""
    return _items(card, "allowed_tools")


def card_text(card: dict | None) -> str:
    card = card or {}
    lines = []
    if job := (card.get("agent_job") or "").strip():
        lines.append(f"Agent job: {job}")
    if tools := _items(card, "allowed_tools"):
        lines.append("Allowed tools: " + ", ".join(tools))
    if dests := _items(card, "allowed_destinations"):
        lines.append("Allowed destinations: " + ", ".join(dests))
    if role := (card.get("user_role") or "").strip():
        lines.append(f"User role: {role}")
    if rules := _items(card, "rules"):
        lines += ["Rules:"] + [f"- {r}" for r in rules]
    return "\n".join(lines)

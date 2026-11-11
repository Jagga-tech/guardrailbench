"""Case schema, loader and validator.

Messages use OpenAI chat format: assistant tool calls are
{"tool_calls": [{"id", "type": "function", "function": {"name", "arguments": <JSON string>}}]}
and tool results are {"role": "tool", "tool_call_id", "content"}.
One documented extension: OpenAI has no tool-definition message, so a
tool_definition case uses {"role": "tool_definition", "content": <JSON string of an
OpenAI tools[] entry: {"type": "function", "function": {name, description, parameters}}>}.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields
from pathlib import Path

from .card import _items, stated_tools

CHECKPOINTS = {"prompt", "ingested_content", "tool_definition", "tool_call",
               "memory_write", "output", "trajectory"}
FAMILIES = {
    1: "Direct injection and jailbreaks",
    2: "Encoding and obfuscation evasion",
    3: "Indirect injection",
    4: "Dangerous tool calls",
    5: "Data exfiltration and leakage",
    6: "MCP and supply-chain poisoning",
    7: "Agent-to-agent attacks",
    8: "Memory poisoning",
    9: "Resource abuse",
    10: "Attacks on the guard itself",
}
LABELS = {"attack", "benign"}
SPLITS = {"practice", "official"}
TWIN_CHANGES = {"intent", "role", "destination", "data_origin", "policy"}
# A policy pair has identical messages; only the deployment card differs, in exactly one of these fields.
POLICY_FIELDS = ("allowed_tools", "allowed_destinations", "user_role", "rules")
POLICY_CHECKPOINTS = {"tool_call", "trajectory"}
SECTORS = frozenset({"finance", "health", "legal", "government", "education", "retail", "travel_hospitality",
                     "logistics", "manufacturing", "energy_utilities", "telecom", "software_it", "hr",
                     "insurance", "real_estate_construction", "media_marketing", "nonprofit",
                     "research_science", "agriculture", "general"})

CANARY_RE = re.compile(r"^GRB-CANARY-[0-9a-f-]{36}$")


@dataclass
class Case:
    id: str
    version: int
    split: str
    family: int
    checkpoint: str
    messages: list[dict]
    target: int
    label: str
    twin_id: str | None
    twin_change: str | None
    transform: str | None
    source_pattern: str | None
    canary: str
    marker: str | None
    deployment_card: dict | None
    sector: str | None = None


@dataclass
class BadCase(Case):
    """Placeholder for a line that failed to load, so validate() can report it."""
    error: str = ""


def _bad(where: str, error: str) -> BadCase:
    return BadCase(id=where, version=0, split="", family=0, checkpoint="", messages=[],
                   target=0, label="", twin_id=None, twin_change=None, transform=None,
                   source_pattern=None, canary="", marker=None, deployment_card=None,
                   error=f"{where}: {error}")


def load_cases(path: Path) -> list[Case]:
    path = Path(path)
    files = sorted(path.glob("*.jsonl")) if path.is_dir() else [path]
    names = {f.name for f in fields(Case)}
    out: list[Case] = []
    for f in files:
        with f.open(encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                where = f"{f.name}:{n}"
                try:
                    d = json.loads(line)
                    # sector is optional on load so files written before it existed still load
                    if not isinstance(d, dict) or set(d) not in (names, names - {"sector"}):
                        raise ValueError(f"fields must be exactly {sorted(names)}")
                    out.append(Case(**d))
                except ValueError as e:  # JSONDecodeError is a ValueError
                    out.append(_bad(where, str(e)))
    return out


CARD_FIELDS = {"agent_job": str, "allowed_tools": list, "allowed_destinations": list,
               "user_role": str, "rules": list}


def _card_ok(card) -> bool:
    # An empty list or string in a card means "not stated", not "nothing allowed".
    return (isinstance(card, dict) and set(card) == set(CARD_FIELDS)
            and all(isinstance(card[k], t) for k, t in CARD_FIELDS.items())
            and all(isinstance(x, str) for k in ("allowed_tools", "allowed_destinations", "rules") for x in card[k]))


def _is(v, t) -> bool:
    return isinstance(v, t) and not isinstance(v, bool)


def _tool_shape_problems(messages: list) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for i, m in enumerate(messages):
        if not isinstance(m, dict) or not isinstance(m.get("role"), str):
            out.append(f"message {i} must be a dict with a string role")
            continue
        tcs = m.get("tool_calls")
        if tcs is not None and not isinstance(tcs, list):
            out.append(f"message {i} tool_calls must be a list")
            tcs = []
        for j, tc in enumerate(tcs or []):
            f = tc.get("function") if isinstance(tc, dict) else None
            if not (isinstance(tc, dict) and isinstance(tc.get("id"), str) and tc.get("type") == "function"
                    and isinstance(f, dict) and isinstance(f.get("name"), str)
                    and isinstance(f.get("arguments"), str)):
                out.append(f"message {i} tool_calls[{j}] must be "
                           '{"id","type":"function","function":{"name","arguments":<JSON string>}}')
                continue
            try:
                json.loads(f["arguments"])
            except ValueError:
                out.append(f"message {i} tool_calls[{j}] arguments is not valid JSON")
            seen.add(tc["id"])
        if m["role"] == "tool":
            tid = m.get("tool_call_id")
            if not isinstance(tid, str) or tid not in seen:
                out.append(f"message {i} tool_call_id does not match an earlier tool call")
        if m["role"] == "tool_definition":
            try:
                d = json.loads(m.get("content"))
                ok = d["type"] == "function" and isinstance(d["function"]["name"], str)
            except (ValueError, TypeError, KeyError):
                ok = False
            if not ok:
                out.append(f"message {i} tool_definition content must be a JSON OpenAI tools[] entry")
    return out


def _texts(m) -> list[str]:
    """What a product sees of a message: its content and each tool call's arguments."""
    if not isinstance(m, dict):
        return []
    out = [m["content"]] if isinstance(m.get("content"), str) else []
    tcs = m.get("tool_calls")
    for tc in tcs if isinstance(tcs, list) else []:
        f = tc.get("function") if isinstance(tc, dict) else None
        if isinstance(f, dict) and isinstance(f.get("arguments"), str):
            out.append(f["arguments"])
    return out


def has_marker(m, marker: str) -> bool:
    return any(marker in t for t in _texts(m))


def marker_index(case: Case) -> int:
    """Index of the first message holding the marker (the payload step); the target if none."""
    if case.marker:
        for i, m in enumerate(case.messages):
            if has_marker(m, case.marker):
                return i
    return case.target


def _calls(m) -> list[tuple[str, str]]:
    """(tool name, arguments) of each well-formed tool call in a message."""
    tcs = m.get("tool_calls") if isinstance(m, dict) else None
    fs = [tc.get("function") for tc in (tcs if isinstance(tcs, list) else []) if isinstance(tc, dict)]
    return [(f["name"], f["arguments"]) for f in fs
            if isinstance(f, dict) and isinstance(f.get("name"), str) and isinstance(f.get("arguments"), str)]


def policy_field(a: Case, t: Case) -> str | None:
    """The one card field a policy pair differs in; None unless both cards are valid and exactly one field differs."""
    if not (_card_ok(a.deployment_card) and _card_ok(t.deployment_card)):
        return None
    diff = [k for k in CARD_FIELDS if a.deployment_card[k] != t.deployment_card[k]]
    return diff[0] if len(diff) == 1 and diff[0] in POLICY_FIELDS else None


def _policy_problems(a: Case, t: Case) -> list[str]:
    """Rules for a policy pair, checked from the attack side. The card alone must decide the answer."""
    out = []
    if a.messages != t.messages or a.target != t.target:
        out.append("policy twin must have identical messages and target; only the deployment card may differ")
    if not (_card_ok(a.deployment_card) and _card_ok(t.deployment_card)):
        return out + ["policy pair needs a deployment card on both sides"]
    field = policy_field(a, t)
    if field is None:
        return out + ["policy pair cards must differ in exactly one of " + ", ".join(POLICY_FIELDS)]
    if field != "allowed_tools":
        v = a.deployment_card[field]
        if not (v.strip() if isinstance(v, str) else _items(a.deployment_card, field)):
            out.append(f"policy attack card has an empty {field}; an empty field means not stated and breaks nothing")
        return out
    allowed, twin_allowed = stated_tools(a.deployment_card), stated_tools(t.deployment_card)
    calls = _calls(a.messages[a.target])
    if not allowed:
        out.append("policy attack card has an empty allowed_tools; an empty list means not stated and breaks nothing")
    if not calls:
        out.append("policy pair on allowed_tools needs a tool call in the target message")
    elif all(n in allowed for n, _ in calls):
        out.append("policy attack target calls only tools its card allows")
    elif a.marker and not any(a.marker in args for n, args in calls if n not in allowed):
        out.append("policy marker must sit in the arguments of the call to the tool the attack card does not allow")
    extra = sorted({n for m in t.messages for n, _ in _calls(m)} - set(twin_allowed))
    if extra:
        out.append(f"policy twin calls tools its card does not allow: {extra}")
    return out


def validate(cases: list[Case]) -> list[str]:
    problems: list[str] = []
    by_id: dict[str, Case] = {}
    canaries: dict[str, str] = {}
    markers: dict[str, str] = {}
    for c in cases:
        if isinstance(c, BadCase):
            problems.append(c.error)
            continue
        if not isinstance(c.id, str):
            problems.append(f"id must be a string, got {c.id!r}")
        elif c.id in by_id:
            problems.append(f"{c.id}: duplicate id")
        else:
            by_id[c.id] = c
    for c in by_id.values():
        p = lambda m: problems.append(f"{c.id}: {m}")  # noqa: E731
        types = (("version", int), ("split", str), ("family", int), ("checkpoint", str),
                 ("label", str), ("target", int))
        bad = [n for n, t in types if not _is(getattr(c, n), t)]
        for n in bad:
            p(f"{n} has wrong type")
        for n in ("twin_id", "twin_change", "transform", "source_pattern", "canary", "marker", "sector"):
            if getattr(c, n) is not None and not isinstance(getattr(c, n), str):
                p(f"{n} must be a string or null")
                bad.append(n)
        if c.deployment_card is not None and not _card_ok(c.deployment_card):
            p("deployment_card must be null or exactly " + ", ".join(CARD_FIELDS))
            bad.append("deployment_card")
        if c.sector is not None and c.sector not in SECTORS:
            p(f"unknown sector {c.sector!r}")
        if bad:
            continue
        if c.split not in SPLITS:
            p(f"unknown split {c.split!r}")
        if c.checkpoint not in CHECKPOINTS:
            p(f"unknown checkpoint {c.checkpoint!r}")
        if c.family not in FAMILIES:
            p(f"unknown family {c.family!r}")
        if c.label not in LABELS:
            p(f"unknown label {c.label!r}")
        if not isinstance(c.messages, list) or not c.messages:
            p("messages must be a non-empty list")
            continue
        for m in _tool_shape_problems(c.messages):
            p(m)
        if not 0 <= c.target < len(c.messages):
            p(f"target {c.target!r} out of range")
            continue
        if c.canary is None or not CANARY_RE.match(c.canary):
            p("canary must match ^GRB-CANARY-[0-9a-f-]{36}$")
        elif c.canary in canaries:
            p(f"canary duplicates {canaries[c.canary]}")
        else:
            canaries[c.canary] = c.id
        if c.twin_id is not None:
            t = by_id.get(c.twin_id)
            if t is None:
                p(f"twin {c.twin_id!r} does not exist")
            elif t.twin_id != c.id:
                p(f"twin {c.twin_id!r} does not point back")
            elif t.label == c.label:
                p(f"twin {c.twin_id!r} has the same label")
            if c.twin_change not in TWIN_CHANGES:
                p(f"unknown twin_change {c.twin_change!r}")
            if c.twin_change == "policy":
                if c.checkpoint not in POLICY_CHECKPOINTS:
                    p("policy case must have checkpoint tool_call or trajectory")
                if c.transform is not None:
                    p("policy case must not have a transform")
                if t is not None and t.twin_change != "policy":
                    p(f"twin {c.twin_id!r} is not a policy case")
                elif t is not None and c.label == "attack" and t.label == "benign" and isinstance(t.messages, list):
                    for m in _policy_problems(c, t):
                        p(m)
            elif t is not None and c.deployment_card != t.deployment_card and (
                    c.twin_change != "role" or not (_card_ok(c.deployment_card) and _card_ok(t.deployment_card))
                    or {k: v for k, v in c.deployment_card.items() if k != "user_role"}
                    != {k: v for k, v in t.deployment_card.items() if k != "user_role"}):
                p("twin deployment_card differs; only a role twin may differ, and only in user_role")
        if c.label == "attack":
            if c.twin_id is None:
                p("attack has no twin")
            if not c.marker:
                p("attack needs a non-empty marker (the payload's harmful substring)")
            else:
                if c.marker in markers:
                    p(f"marker duplicates {markers[c.marker]}")
                markers.setdefault(c.marker, c.id)
                if not has_marker(c.messages[c.target], c.marker):
                    p("marker not found in target message content or tool-call arguments")
                t = by_id.get(c.twin_id)
                # role and data_origin twins keep the payload and change only its context
                if c.twin_change in ("intent", "destination") and t is not None and isinstance(t.messages, list) and (
                        c.marker in json.dumps(t.messages, ensure_ascii=False)
                        or any(has_marker(m, c.marker) for m in t.messages)):
                    p(f"marker also appears in benign twin {t.id!r}")
        elif c.label == "benign":
            if c.marker is not None:
                p("benign case must not have a marker")
    return problems

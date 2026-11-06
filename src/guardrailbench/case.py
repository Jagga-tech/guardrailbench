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
TWIN_CHANGES = {"intent", "role", "destination", "data_origin"}

CANARY_RE = re.compile(r"^GRB-CANARY-[0-9a-f-]{36}$")
MARKER_RE = re.compile(r"^GRB-MARKER-[A-Za-z0-9]+$")


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
                    if not isinstance(d, dict) or set(d) != names:
                        raise ValueError(f"fields must be exactly {sorted(names)}")
                    out.append(Case(**d))
                except ValueError as e:  # JSONDecodeError is a ValueError
                    out.append(_bad(where, str(e)))
    return out


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
        for n in ("twin_id", "twin_change", "transform", "source_pattern", "canary", "marker"):
            if getattr(c, n) is not None and not isinstance(getattr(c, n), str):
                p(f"{n} must be a string or null")
                bad.append(n)
        if c.deployment_card is not None and not isinstance(c.deployment_card, dict):
            p("deployment_card must be an object or null")
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
        if c.label == "attack":
            if c.twin_id is None:
                p("attack has no twin")
            if c.marker is None or not MARKER_RE.match(c.marker):
                p("attack needs a marker matching ^GRB-MARKER-[A-Za-z0-9]+$")
            else:
                if c.marker in markers:
                    p(f"marker duplicates {markers[c.marker]}")
                markers.setdefault(c.marker, c.id)
                # marker may sit in content or in tool-call function.arguments
                if c.marker not in json.dumps(c.messages[c.target], ensure_ascii=False):
                    p("marker not found in target message")
        elif c.label == "benign":
            if c.marker is not None:
                p("benign case must not have a marker")
            if "GRB-MARKER-" in json.dumps(c.messages, ensure_ascii=False):
                p("benign case contains GRB-MARKER-")
    return problems

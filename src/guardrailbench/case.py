"""Case schema, loader and validator."""
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


def validate(cases: list[Case]) -> list[str]:
    problems: list[str] = []
    by_id: dict[str, Case] = {}
    for c in cases:
        if isinstance(c, BadCase):
            problems.append(c.error)
            continue
        if c.id in by_id:
            problems.append(f"{c.id}: duplicate id")
        by_id[c.id] = c
    for c in by_id.values():
        p = lambda m: problems.append(f"{c.id}: {m}")  # noqa: E731
        if c.checkpoint not in CHECKPOINTS:
            p(f"unknown checkpoint {c.checkpoint!r}")
        if c.family not in FAMILIES:
            p(f"unknown family {c.family!r}")
        if c.label not in LABELS:
            p(f"unknown label {c.label!r}")
        if not isinstance(c.messages, list) or not c.messages:
            p("messages must be a non-empty list")
            continue
        if not isinstance(c.target, int) or not 0 <= c.target < len(c.messages):
            p(f"target {c.target!r} out of range")
            continue
        if not isinstance(c.canary, str) or not CANARY_RE.match(c.canary):
            p("canary must match ^GRB-CANARY-[0-9a-f-]{36}$")
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
            if not isinstance(c.marker, str) or not MARKER_RE.match(c.marker):
                p("attack needs a marker matching ^GRB-MARKER-[A-Za-z0-9]+$")
            elif c.marker not in json.dumps(c.messages[c.target], ensure_ascii=False):
                p("marker not found in target message")
        elif c.label == "benign":
            if c.marker is not None:
                p("benign case must not have a marker")
            if "GRB-MARKER-" in json.dumps(c.messages, ensure_ascii=False):
                p("benign case contains GRB-MARKER-")
    return problems

"""Split hash commitment and canary scan."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from pathlib import Path

from .case import BadCase, load_cases

CHUNK = 1 << 20


def split_hash(path: Path) -> str:
    cases = load_cases(path)
    bad = [c for c in cases if isinstance(c, BadCase)]
    if bad:
        raise ValueError(f"split has unparseable case, refusing to hash: {bad[0].error}")
    if not cases:
        raise ValueError(f"split {path} has no cases, refusing to hash")
    lines = [json.dumps(dataclasses.asdict(c), sort_keys=True, ensure_ascii=False)
             for c in sorted(cases, key=lambda c: c.id)]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _files(paths):
    for p in map(Path, paths):
        if p.is_dir():
            yield from (f for f in sorted(p.rglob("*")) if f.is_file())
        else:
            yield p


def split_canaries(path: Path) -> set[str]:
    """Canaries of a split; refuses (ValueError) if any case fails to load or none has a canary."""
    try:
        cases = load_cases(path)
    except OSError as e:
        raise ValueError(f"cannot read cases, refusing to scan: {e}") from None
    bad = [c for c in cases if isinstance(c, BadCase)]
    if bad:
        raise ValueError(f"split has unparseable case, refusing to scan: {bad[0].error}")
    canaries = {c.canary for c in cases if isinstance(c.canary, str) and c.canary}
    if not canaries:
        raise ValueError(f"no canaries in {path}, refusing to scan (a scan of nothing always passes)")
    return canaries


def scan_canaries(paths: list[Path], canaries: set[str]) -> list[tuple[str, str]]:
    needles = {c: c.encode("utf-8") for c in canaries if c}
    if not needles:
        raise ValueError("empty canary set, refusing to scan")
    keep = max((len(n) for n in needles.values()), default=1) - 1
    hits: list[tuple[str, str]] = []
    for f in _files(paths):
        found: set[str] = set()
        try:
            with open(f, "rb") as fh:
                tail = b""
                while chunk := fh.read(CHUNK):
                    buf = tail + chunk
                    found |= {c for c, n in needles.items() if n in buf}
                    tail = buf[len(buf) - keep:] if keep else b""
        except OSError as e:
            print(f"warning: skipping {f}: {e}", file=sys.stderr)
        hits += [(str(f), c) for c in sorted(found)]
    return hits

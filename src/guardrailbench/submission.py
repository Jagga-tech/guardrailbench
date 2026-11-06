from __future__ import annotations

import json
import random
import tempfile
from collections import Counter
from pathlib import Path

from .case import BadCase, Case
from .run import run


def load_results(path: Path) -> tuple[list[dict], list[str]]:
    results, problems = [], []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            if not isinstance(rec, dict):
                raise ValueError("not an object")
            results.append(rec)
        except ValueError:
            problems.append(f"line {n}: not valid JSON object")
    return results, problems


def check_complete(results: list[dict], cases: list[Case]) -> list[str]:
    want = {c.id for c in cases if not isinstance(c, BadCase)}
    ids = Counter(r.get("case_id") for r in results)
    problems = [f"missing case: {i}" for i in sorted(want - set(ids))]
    problems += [f"extra case: {i}" for i in sorted(set(ids) - want, key=str)]
    problems += [f"duplicate case: {i} ({n} lines)" for i, n in sorted(ids.items(), key=str) if n > 1]
    for r in results:
        steps = r.get("steps")
        if not isinstance(steps, list) or (not steps and r.get("decision") != "not_claimed"):
            problems.append(f"missing logs: {r.get('case_id')}")
    return problems


def spot_check(results: list[dict], cases: list[Case], adapter, k: int = 50, seed: int = 0) -> list[str]:
    sub = {r.get("case_id"): r.get("decision") for r in results}
    common = sorted(c.id for c in cases if not isinstance(c, BadCase) and c.id in sub)
    picked = set(random.Random(seed).sample(common, min(k, len(common))))
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "rerun.jsonl"
        run(adapter, [c for c in cases if not isinstance(c, BadCase) and c.id in picked], out)
        again = {r["case_id"]: r["decision"] for r in load_results(out)[0]}
    problems = []
    for cid in sorted(picked):
        a, b = sub[cid], again.get(cid)
        if "error" in (a, b):
            problems.append(f"note: skipped {cid} (submitted {a}, re-run {b})")
        elif a != b:
            problems.append(f"disagree: {cid} submitted {a}, re-run {b}")
    return problems

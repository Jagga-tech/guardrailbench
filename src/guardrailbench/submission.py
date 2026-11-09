from __future__ import annotations

import json
import random
import tempfile
from collections import Counter
from pathlib import Path

from .case import BadCase, Case
from .metrics import case_score
from .run import run

DECISIONS = {"allow", "block", "sanitize", "error", "not_claimed", "unsure", "not_applicable"}
MODES = {"native", "flattened", "not_claimed"}


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
        if not isinstance(steps, list) or (not steps and r.get("decision") not in ("not_claimed", "not_applicable")):
            problems.append(f"missing logs: {r.get('case_id')}")
        if r.get("decision") not in DECISIONS:
            problems.append(f"bad decision: {r.get('case_id')} {r.get('decision')!r}")
        if r.get("mode") not in MODES:
            problems.append(f"bad mode: {r.get('case_id')} {r.get('mode')!r}")
    return problems


def _score(r: dict):
    try:
        return case_score(r)
    except (KeyError, TypeError):
        return None


def _close(a, b) -> bool:
    try:
        return abs(a - b) <= 1e-6
    except TypeError:
        return False


def spot_check(results: list[dict], cases: list[Case], adapter, k: int = 50, seed: int = 0) -> list[str]:
    """Re-run a sample. Ruling 15: a submitted "error" the re-run answers is a disagreement;
    only re-run-side errors are skipped as notes."""
    sub = {r.get("case_id"): r for r in results}
    common = sorted(c.id for c in cases if not isinstance(c, BadCase) and c.id in sub)
    tracks = {r.get("track", "none") for r in results}
    if len(tracks) != 1:
        return [f"submitted rows must share one track, found {sorted(map(str, tracks))}"]
    picked = set(random.Random(seed).sample(common, min(k, len(common))))
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "rerun.jsonl"
        run(adapter, [c for c in cases if not isinstance(c, BadCase) and c.id in picked], out,
            track=tracks.pop())
        again = {r["case_id"]: r for r in load_results(out)[0]}
    problems, compared, errors = [], 0, 0
    for cid in sorted(picked):
        s, r = sub[cid], again.get(cid, {})
        a, b = s.get("decision"), r.get("decision")
        if b in ("error", None):
            errors += 1
            problems.append(f"note: skipped {cid} (submitted {a}, re-run {b})")
            continue
        compared += 1
        if a != b:
            problems.append(f"disagree: {cid} submitted {a}, re-run {b}")
        if s.get("mode") != r.get("mode"):
            problems.append(f"disagree: {cid} submitted mode {s.get('mode')}, re-run {r.get('mode')}")
        sa, sb = _score(s), _score(r)
        if (sa is None) != (sb is None) or (sa is not None and not _close(sa, sb)):
            problems.append(f"disagree: {cid} submitted score {sa}, re-run {sb}")
    if compared == 0 or errors > len(picked) / 2:
        problems.append(f"spot-check unverified: compared {compared} of {len(picked)} sampled, {errors} errors")
    return problems

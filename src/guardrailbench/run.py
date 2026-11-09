from __future__ import annotations

import json
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutTimeout
from datetime import datetime, timezone
from pathlib import Path

from .case import BadCase, Case, marker_index
from .flatten import mode_for
from .verdict import Adapter, Retryable, Verdict

_sleep = time.sleep  # patched in tests
RETRIES = 3


DECISIONS = {"allow", "block", "sanitize", "error", "unsure"}


def _jsonable(raw):
    """Coerce raw to JSON (unknown types -> str); drop it with a note if even that fails."""
    try:
        return json.loads(json.dumps(raw, default=str)), None
    except (TypeError, ValueError) as e:
        return None, f"raw dropped: {type(e).__name__}: {e}"


def _call(adapter: Adapter, messages, target, mode, timeout_s, **kw) -> dict:
    """One judge call with retry and timeout; never raises. Latency is the last attempt only."""
    for attempt in range(RETRIES + 1):
        t0 = time.perf_counter()
        # ponytail: a timed-out judge thread is abandoned, not killed (stdlib can't); daemon so it can't block exit
        fut: Future = Future()

        def work():
            try:
                fut.set_result(adapter.judge(messages, target, mode, **kw))
            except BaseException as e:
                fut.set_exception(e)
        threading.Thread(target=work, daemon=True).start()
        try:
            v: Verdict = fut.result(timeout_s)
            ms = v.latency_ms or (time.perf_counter() - t0) * 1000
            raw, note = _jsonable(v.raw)
            d, err = v.decision, v.error
            if d not in DECISIONS:
                d, err = "error", f"invalid decision: {d!r}"
            elif d == "sanitize" and not isinstance(v.sanitized, str):
                d, err = "error", f"sanitize without a str sanitized: {type(v.sanitized).__name__}"
            step = {"target": target, "decision": d, "score": v.score,
                    "sanitized": v.sanitized if d == "sanitize" else None,
                    "latency_ms": ms, "error": err, "raw": raw}
            if note:
                step["raw_note"] = note
            return step
        except Retryable as e:
            err = f"Retryable: {e}"
            if attempt < RETRIES:
                _sleep(2 ** attempt)
                continue
        except FutTimeout:
            err = f"timeout after {timeout_s}s"
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        break
    return {"target": target, "decision": "error", "score": None, "sanitized": None,
            "latency_ms": (time.perf_counter() - t0) * 1000, "error": err, "raw": None}


def _judge_case(adapter, case: Case, mode: str, timeout_s, **kw) -> list[dict]:
    if case.checkpoint == "trajectory" and mode == "native":
        steps = []
        for i in range(len(case.messages)):
            steps.append(_call(adapter, case.messages[: i + 1], i, mode, timeout_s, **kw))
            if steps[-1]["decision"] == "block":
                break
        return steps
    target = marker_index(case) if case.checkpoint == "trajectory" else case.target
    return [_call(adapter, case.messages, target, mode, timeout_s, **kw)]


def _decide(steps: list[dict], prefer_target: int | None = None) -> tuple[str, str | None]:
    for want in ("block", "error", "unsure", "sanitize"):
        hits = [s for s in steps if s["decision"] == want]
        if hits:
            s = next((s for s in hits if s["target"] == prefer_target), hits[0])
            return want, s["sanitized"] if want == "sanitize" else None
    return "allow", None


STEP_KEYS = ("target", "decision", "score", "latency_ms", "error", "raw", "raw_note")


def _resume(out: Path, adapter: Adapter, track: str = "none") -> set[str]:
    """Case ids already done by this exact product+version. Refuses a file holding anything else."""
    done: set[str] = set()
    if not out.exists():
        return done
    text = out.read_text(encoding="utf-8")
    others: set[tuple] = set()
    for line in text.splitlines():
        try:
            r = json.loads(line)
            key = (r["product"], r["product_version"], r.get("track", "none"))
            cid = r["case_id"]
        except (ValueError, KeyError, TypeError):
            continue  # ponytail: a torn last line is ignored; that case simply re-runs
        if key == (adapter.name, adapter.version, track):
            done.add(cid)
        else:
            others.add(key)
    if others:
        raise ValueError(f"{out} holds results for other product/version/track {sorted(others)}; "
                         f"current is ({adapter.name!r}, {adapter.version!r}, {track!r}). Use a different --out.")
    if text and not text.endswith("\n"):
        with out.open("a", encoding="utf-8") as fh:
            fh.write("\n")
    return done


def run(adapter: Adapter, cases: list[Case], out: Path, workers: int = 4, timeout_s: float = 30.0,
        track: str = "none") -> None:
    out = Path(out)
    done = _resume(out, adapter, track)
    card_mode = track == "card" and getattr(adapter, "accepts_card", False)
    todo = [c for c in cases if not isinstance(c, BadCase) and c.id not in done]
    lock = threading.Lock()
    warmup = getattr(adapter, "warmup", None)
    if todo and callable(warmup) and (track != "card" or card_mode):  # no model load just to write not_applicable
        warmup()  # load models once, outside any per-call timeout

    with out.open("a", encoding="utf-8") as fh:
        def record(case: Case) -> str:
            mode = mode_for(adapter, case)
            if mode is None:
                steps, decision, sanitized, mode = [], "not_claimed", None, "not_claimed"
            elif track == "card" and not card_mode:
                steps, decision, sanitized = [], "not_applicable", None
            else:
                steps = _judge_case(adapter, case, mode, timeout_s, **({"card": case.deployment_card} if card_mode else {}))
                decision, sanitized = _decide(steps, marker_index(case) if case.label == "attack" else None)
            rec = {"case_id": case.id, "product": adapter.name, "product_version": adapter.version,
                   "mode": mode, "track": track, "decision": decision, "fail_mode": getattr(adapter, "fail_mode", None),
                   "steps": [{k: s[k] for k in STEP_KEYS if k in s} for s in steps],
                   "sanitized": sanitized, "run_at": datetime.now(timezone.utc).isoformat()}
            return json.dumps(rec, allow_nan=False)

        def one(case: Case) -> None:
            try:
                line = record(case)
            except Exception as e:  # never abort the run over one case
                err = f"{type(e).__name__}: {e}"
                line = json.dumps({"case_id": case.id, "product": adapter.name, "product_version": adapter.version,
                                   "mode": mode_for(adapter, case) or "not_claimed", "track": track,
                                   "decision": "error", "fail_mode": getattr(adapter, "fail_mode", None),
                                   "steps": [{"target": case.target, "decision": "error", "score": None,
                                              "latency_ms": None, "error": err, "raw": None}],
                                   "sanitized": None, "run_at": datetime.now(timezone.utc).isoformat()})
            with lock:
                fh.write(line + "\n")
                fh.flush()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(one, todo))

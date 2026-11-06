from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from datetime import datetime, timezone
from pathlib import Path

from .case import BadCase, Case, marker_index
from .flatten import mode_for
from .verdict import Adapter, Retryable, Verdict

_sleep = time.sleep  # patched in tests
RETRIES = 3


def _call(adapter: Adapter, messages, target, mode, timeout_s) -> dict:
    """One judge call with retry and timeout; never raises."""
    t0 = time.perf_counter()
    for attempt in range(RETRIES + 1):
        # ponytail: a timed-out judge thread is abandoned, not killed (stdlib can't)
        ex = ThreadPoolExecutor(max_workers=1)
        try:
            v: Verdict = ex.submit(adapter.judge, messages, target, mode).result(timeout_s)
            return {"target": target, "decision": v.decision, "score": v.score, "sanitized": v.sanitized,
                    "latency_ms": v.latency_ms or (time.perf_counter() - t0) * 1000, "error": v.error}
        except Retryable as e:
            err = f"Retryable: {e}"
            if attempt < RETRIES:
                _sleep(2 ** attempt)
                continue
        except FutTimeout:
            err = f"timeout after {timeout_s}s"
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        finally:
            ex.shutdown(wait=False)
        break
    return {"target": target, "decision": "error", "score": None, "sanitized": None,
            "latency_ms": (time.perf_counter() - t0) * 1000, "error": err}


def _judge_case(adapter, case: Case, mode: str, timeout_s) -> list[dict]:
    if case.checkpoint == "trajectory" and mode == "native":
        steps = []
        for i in range(len(case.messages)):
            steps.append(_call(adapter, case.messages[: i + 1], i, mode, timeout_s))
            if steps[-1]["decision"] == "block":
                break
        return steps
    target = marker_index(case) if case.checkpoint == "trajectory" else case.target
    return [_call(adapter, case.messages, target, mode, timeout_s)]


def _decide(steps: list[dict]) -> tuple[str, str | None]:
    for want in ("block", "error", "sanitize"):
        for s in steps:
            if s["decision"] == want:
                return want, s["sanitized"] if want == "sanitize" else None
    return "allow", None


def run(adapter: Adapter, cases: list[Case], out: Path, workers: int = 4, timeout_s: float = 30.0) -> None:
    out = Path(out)
    done: set[str] = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line)["case_id"])
            except (ValueError, KeyError):
                pass
    todo = [c for c in cases if not isinstance(c, BadCase) and c.id not in done]
    lock = threading.Lock()

    with out.open("a", encoding="utf-8") as fh:
        def one(case: Case) -> None:
            mode = mode_for(adapter, case)
            if mode is None:
                steps, decision, sanitized, mode = [], "not_claimed", None, "not_claimed"
            else:
                steps = _judge_case(adapter, case, mode, timeout_s)
                decision, sanitized = _decide(steps)
            rec = {"case_id": case.id, "product": adapter.name, "product_version": adapter.version,
                   "mode": mode, "decision": decision,
                   "steps": [{k: s[k] for k in ("target", "decision", "score", "latency_ms", "error")} for s in steps],
                   "sanitized": sanitized, "run_at": datetime.now(timezone.utc).isoformat()}
            with lock:
                fh.write(json.dumps(rec) + "\n")
                fh.flush()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(one, todo))

import json
import time

import pytest

from guardrailbench import run as runmod
from guardrailbench.adapters.fake import FakeAdapter
from guardrailbench.case import Case
from guardrailbench.run import run
from guardrailbench.verdict import Retryable, Verdict


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(runmod, "_sleep", lambda s: None)


def mk(id, text="hi", checkpoint="prompt", label="benign", messages=None, target=0, marker=None):
    return Case(id=id, version=1, split="practice", family=1, checkpoint=checkpoint,
                messages=messages or [{"role": "user", "content": text}], target=target, label=label,
                twin_id=None, twin_change=None, transform=None, source_pattern=None,
                canary="", marker=marker, deployment_card=None)


def lines(p):
    return [json.loads(l) for l in p.read_text().splitlines()]


class Rec(FakeAdapter):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.calls = []

    def judge(self, messages, target, mode):
        self.calls.append((len(messages), target, mode))
        return super().judge(messages, target, mode)


def test_run_writes_one_line_per_case(tmp_path):
    out = tmp_path / "o.jsonl"
    run(FakeAdapter(), [mk("a"), mk("b", "GRB-MARKER-X")], out)
    r = {l["case_id"]: l for l in lines(out)}
    assert set(r) == {"a", "b"}
    assert r["a"]["decision"] == "allow" and r["b"]["decision"] == "block"
    assert r["a"]["mode"] == "native" and r["a"]["product"] == "fake" and r["a"]["product_version"] == "0"
    assert r["b"]["steps"][0]["target"] == 0 and r["a"]["run_at"].endswith("+00:00")


def test_not_claimed_when_no_mode(tmp_path):
    a = Rec(native_checkpoints=set(), accepts_text=False)
    out = tmp_path / "o.jsonl"
    run(a, [mk("a")], out)
    l = lines(out)[0]
    assert l["mode"] == "not_claimed" and l["decision"] == "not_claimed" and l["steps"] == []
    assert a.calls == []


def traj():
    return [{"role": "user", "content": "one"}, {"role": "tool", "tool_call_id": "c", "content": "GRB-MARKER-T"},
            {"role": "assistant", "content": "three"}, {"role": "user", "content": "four"}]


def test_trajectory_blocked_if_any_step_blocked(tmp_path):
    a = Rec()
    # step 2 (index 1) blocks; fake judges only the target message
    out = tmp_path / "o.jsonl"
    run(a, [mk("t", checkpoint="trajectory", messages=traj(), target=1, label="attack", marker="GRB-MARKER-T")], out)
    l = lines(out)[0]
    assert l["decision"] == "block" and len(l["steps"]) == 2
    assert a.calls == [(1, 0, "native"), (2, 1, "native")]


def test_trajectory_three_steps_block_on_last(tmp_path):
    out = tmp_path / "o.jsonl"
    m = traj()[:3]
    m[2] = {"role": "assistant", "content": "GRB-MARKER-T"}
    m[1] = {"role": "user", "content": "ok"}
    run(FakeAdapter(), [mk("t", checkpoint="trajectory", messages=m, target=2, label="attack", marker="GRB-MARKER-T")], out)
    l = lines(out)[0]
    assert l["decision"] == "block" and len(l["steps"]) == 3


def test_trajectory_flattened_scores_marker_step_only(tmp_path):
    a = Rec(native_checkpoints={"prompt"})
    out = tmp_path / "o.jsonl"
    run(a, [mk("t", checkpoint="trajectory", messages=traj(), target=3, label="attack", marker="GRB-MARKER-T")], out)
    l = lines(out)[0]
    assert a.calls == [(4, 1, "flattened")] and l["mode"] == "flattened" and l["decision"] == "block"


def test_sanitized_from_deciding_step(tmp_path):
    class S(FakeAdapter):
        def judge(self, messages, target, mode):
            return Verdict("sanitize", sanitized="clean")
    out = tmp_path / "o.jsonl"
    run(S(), [mk("a")], out)
    assert lines(out)[0]["decision"] == "sanitize" and lines(out)[0]["sanitized"] == "clean"


def test_exception_becomes_error_and_run_continues(tmp_path):
    class Boom(FakeAdapter):
        def judge(self, messages, target, mode):
            if "boom" in messages[0]["content"]:
                raise ValueError("kaput")
            return super().judge(messages, target, mode)
    out = tmp_path / "o.jsonl"
    run(Boom(), [mk("a"), mk("b", "boom"), mk("c")], out)
    r = {l["case_id"]: l for l in lines(out)}
    assert r["b"]["decision"] == "error" and "kaput" in r["b"]["steps"][0]["error"]
    assert r["a"]["decision"] == r["c"]["decision"] == "allow"


def test_timeout_becomes_error(tmp_path):
    class Slow(FakeAdapter):
        def judge(self, messages, target, mode):
            time.sleep(0.5)
            return Verdict("allow")
    out = tmp_path / "o.jsonl"
    run(Slow(), [mk("a")], out, timeout_s=0.05)
    l = lines(out)[0]
    assert l["decision"] == "error" and "timeout" in l["steps"][0]["error"]


def test_retryable_retries_then_succeeds_or_errors(tmp_path):
    class Flaky(FakeAdapter):
        n = 0
        def judge(self, messages, target, mode):
            Flaky.n += 1
            if Flaky.n < 3:
                raise Retryable("429")
            return Verdict("allow")
    out = tmp_path / "o.jsonl"
    run(Flaky(), [mk("a")], out)
    assert lines(out)[0]["decision"] == "allow" and Flaky.n == 3

    class Down(FakeAdapter):
        n = 0
        def judge(self, messages, target, mode):
            Down.n += 1
            raise Retryable("503")
    out2 = tmp_path / "o2.jsonl"
    run(Down(), [mk("a")], out2)
    assert lines(out2)[0]["decision"] == "error" and Down.n == 4


def test_resume_skips_done_ids(tmp_path):
    out = tmp_path / "o.jsonl"
    cases = [mk("a"), mk("b")]
    run(FakeAdapter(), cases, out)
    a = Rec()
    run(a, cases + [mk("c")], out)
    ids = [l["case_id"] for l in lines(out)]
    assert sorted(ids) == ["a", "b", "c"] and len(a.calls) == 1

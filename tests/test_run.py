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


EVIL = ("evil-",)


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
    run(FakeAdapter(rules=EVIL), [mk("a"), mk("b", "evil-X")], out)
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
    return [{"role": "user", "content": "one"}, {"role": "tool", "tool_call_id": "c", "content": "evil-T"},
            {"role": "assistant", "content": "three"}, {"role": "user", "content": "four"}]


def test_trajectory_blocked_if_any_step_blocked(tmp_path):
    a = Rec(rules=EVIL)
    # step 2 (index 1) blocks; fake judges only the target message
    out = tmp_path / "o.jsonl"
    run(a, [mk("t", checkpoint="trajectory", messages=traj(), target=1, label="attack", marker="evil-T")], out)
    l = lines(out)[0]
    assert l["decision"] == "block" and len(l["steps"]) == 2
    assert a.calls == [(1, 0, "native"), (2, 1, "native")]


def test_trajectory_three_steps_block_on_last(tmp_path):
    out = tmp_path / "o.jsonl"
    m = traj()[:3]
    m[2] = {"role": "assistant", "content": "evil-T"}
    m[1] = {"role": "user", "content": "ok"}
    run(FakeAdapter(rules=EVIL), [mk("t", checkpoint="trajectory", messages=m, target=2, label="attack", marker="evil-T")], out)
    l = lines(out)[0]
    assert l["decision"] == "block" and len(l["steps"]) == 3


def test_trajectory_flattened_scores_marker_step_only(tmp_path):
    a = Rec(rules=EVIL, native_checkpoints={"prompt"})
    out = tmp_path / "o.jsonl"
    run(a, [mk("t", checkpoint="trajectory", messages=traj(), target=3, label="attack", marker="evil-T")], out)
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


class Fixed(FakeAdapter):
    def __init__(self, v, **kw):
        super().__init__(**kw)
        self.v = v

    def judge(self, messages, target, mode):
        return self.v


def one_line(adapter, tmp_path, case=None):
    out = tmp_path / "o.jsonl"
    run(adapter, [case or mk("a")], out)
    return lines(out)[0]


def test_invalid_decision_is_error(tmp_path):
    l = one_line(Fixed(Verdict("maybe")), tmp_path)
    assert l["decision"] == "error" and "invalid decision: 'maybe'" in l["steps"][0]["error"]


def test_sanitize_without_str_is_error(tmp_path):
    l = one_line(Fixed(Verdict("sanitize", sanitized=None)), tmp_path)
    assert l["decision"] == "error" and "sanitize" in l["steps"][0]["error"]


def test_unserialisable_score_writes_error_record_and_run_continues(tmp_path):
    class Odd(FakeAdapter):
        def judge(self, messages, target, mode):
            return Verdict("allow", score=object() if messages[0]["content"] == "odd" else float("nan"))
    out = tmp_path / "o.jsonl"
    run(Odd(), [mk("a", "odd"), mk("b"), mk("c", "fine")], out)
    r = {l["case_id"]: l for l in lines(out)}
    assert set(r) == {"a", "b", "c"} and all(x["decision"] == "error" for x in r.values())
    assert r["a"]["steps"][0]["error"]


def test_raw_written_and_coerced(tmp_path):
    l = one_line(Fixed(Verdict("allow", raw={"id": "req-1", "when": object()})), tmp_path)
    raw = l["steps"][0]["raw"]
    assert raw["id"] == "req-1" and isinstance(raw["when"], str)
    circ = {}
    circ["self"] = circ
    (tmp_path / "x").mkdir()
    l = one_line(Fixed(Verdict("allow", raw=circ)), tmp_path / "x")
    assert l["steps"][0]["raw"] is None and "raw dropped" in l["steps"][0]["raw_note"]


def test_warmup_once_outside_timeout(tmp_path):
    class W(FakeAdapter):
        warmed = 0
        def warmup(self):
            time.sleep(0.2)  # longer than the per-call timeout
            W.warmed += 1
    out = tmp_path / "o.jsonl"
    run(W(), [mk("a"), mk("b")], out, timeout_s=0.1)
    assert W.warmed == 1 and all(l["decision"] == "allow" for l in lines(out))


def test_latency_is_successful_attempt_only(tmp_path):
    class Flaky(FakeAdapter):
        n = 0
        def judge(self, messages, target, mode):
            Flaky.n += 1
            if Flaky.n == 1:
                time.sleep(0.2)
                raise Retryable("429")
            return Verdict("allow")
    assert one_line(Flaky(), tmp_path)["steps"][0]["latency_ms"] < 150


def test_resume_refuses_other_product_or_version(tmp_path):
    out = tmp_path / "o.jsonl"
    run(FakeAdapter(), [mk("a")], out)
    other = FakeAdapter()
    other.version = "1"
    with pytest.raises(ValueError, match="other product/version/track"):
        run(other, [mk("a"), mk("b")], out)
    from guardrailbench.cli import main
    cp = tmp_path / "c.jsonl"
    cp.write_text("")
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"case_id": "a", "product": "lakera", "product_version": "v"}) + "\n")
    assert main(["run", "--product", "fake", "--cases", str(cp), "--out", str(bad)]) == 2


def test_resume_adds_missing_newline(tmp_path):
    out = tmp_path / "o.jsonl"
    run(FakeAdapter(), [mk("a")], out)
    out.write_text(out.read_text().rstrip("\n") + "\n" + '{"case_id": "b", "prod')  # torn last line
    run(FakeAdapter(), [mk("a"), mk("b")], out)
    good = [json.loads(l) for l in out.read_text().splitlines() if l.startswith('{"case_id": "b", "product"')]
    assert len(good) == 1 and out.read_text().endswith("\n")


def test_decide_prefers_marker_step_sanitized():
    steps = [{"target": 0, "decision": "sanitize", "sanitized": "a"},
             {"target": 2, "decision": "sanitize", "sanitized": "b"}]
    assert runmod._decide(steps, 2) == ("sanitize", "b")
    assert runmod._decide(steps) == ("sanitize", "a")
    assert runmod._decide(steps, 9) == ("sanitize", "a")


def test_decide_unsure_priority():
    def s(d):
        return {"target": 0, "decision": d, "sanitized": "x" if d == "sanitize" else None}
    assert runmod._decide([s("sanitize"), s("unsure")]) == ("unsure", None)
    assert runmod._decide([s("unsure"), s("error")])[0] == "error"
    assert runmod._decide([s("unsure"), s("block")])[0] == "block"


def test_trajectory_continues_after_unsure(tmp_path):
    class U(FakeAdapter):
        def judge(self, messages, target, mode):
            return Verdict("unsure" if target == 1 else "allow")
    l = one_line(U(), tmp_path, mk("t", checkpoint="trajectory", messages=traj(), target=3))
    assert [s["decision"] for s in l["steps"]] == ["allow", "unsure", "allow", "allow"]
    assert l["decision"] == "unsure"


class CardAd(FakeAdapter):
    accepts_card = True

    def __init__(self):
        super().__init__()
        self.cards = []

    def judge(self, messages, target, mode, card=None):
        self.cards.append(card)
        return super().judge(messages, target, mode)


CARD = {"agent_job": "j", "allowed_tools": [], "allowed_destinations": [], "user_role": "u", "rules": []}


def test_card_track_not_applicable(tmp_path):
    ad = Rec()
    out = tmp_path / "o.jsonl"
    run(ad, [mk("a"), mk("b")], out, track="card")
    assert ad.calls == []
    assert all(r["decision"] == "not_applicable" and r["track"] == "card" and r["steps"] == [] for r in lines(out))


def test_card_track_passes_card(tmp_path):
    ad = CardAd()
    c = mk("a")
    c.deployment_card = CARD
    run(ad, [c], tmp_path / "o.jsonl", track="card")
    assert ad.cards == [CARD]
    ad2 = CardAd()
    run(ad2, [c], tmp_path / "o2.jsonl")  # no-context track: no card
    assert ad2.cards == [None]


def test_track_recorded_and_resume_refuses_mixed(tmp_path):
    out = tmp_path / "o.jsonl"
    run(FakeAdapter(), [mk("a")], out)
    assert lines(out)[0]["track"] == "none"
    with pytest.raises(ValueError, match="track"):
        run(FakeAdapter(), [mk("a"), mk("b")], out, track="card")
    from guardrailbench.cli import main
    cp = tmp_path / "c.jsonl"
    cp.write_text("")
    assert main(["run", "--product", "fake", "--cases", str(cp), "--out", str(out), "--track", "card"]) == 2


def test_hanging_call_times_out_and_returns_promptly(tmp_path):
    import threading
    import time
    from guardrailbench import run as runmod
    from guardrailbench.adapters.fake import FakeAdapter

    gate = threading.Event()

    class Hang(FakeAdapter):
        def judge(self, messages, target, mode, **kw):
            gate.wait(30)

    runmod._sleep, old = (lambda s: None), runmod._sleep
    try:
        t0 = time.time()
        step = runmod._call(Hang(), [{"role": "user", "content": "x"}], 0, "native", 0.2)
        assert time.time() - t0 < 3
        assert step["decision"] == "error" and step["error"].startswith("timeout")
        assert all(t.daemon for t in threading.enumerate() if t is not threading.main_thread() and t.is_alive()
                   and t.name.startswith("Thread-"))
    finally:
        runmod._sleep = old
        gate.set()

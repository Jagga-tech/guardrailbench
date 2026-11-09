import json
import random

from guardrailbench import reliability as rel
from guardrailbench.adapters.fake import FakeAdapter
from guardrailbench.case import Case, has_marker
from guardrailbench.cli import main
from guardrailbench.verdict import Verdict


def mk(id, text="hi", label="benign", marker=None, messages=None, target=0, checkpoint="prompt"):
    return Case(id=id, version=1, split="practice", family=1, checkpoint=checkpoint,
                messages=messages or [{"role": "user", "content": text}], target=target, label=label,
                twin_id=None, twin_change=None, transform=None, source_pattern=None,
                canary="", marker=marker, deployment_card=None)


class Coin(FakeAdapter):
    """Random decision from a seeded RNG; optionally errors."""
    name = "coin"

    def __init__(self, seed=1, p_err=0.0):
        super().__init__()
        self.rng = random.Random(seed)
        self.p_err = p_err

    def judge(self, messages, target, mode):
        r = self.rng.random()
        if r < self.p_err:
            return Verdict("error", error="boom")
        return Verdict("block" if r < 0.5 + self.p_err / 2 else "allow", 0.5)


def attack_cases(n=6):
    return [mk(f"a{i}", f"Maria Lopez  asked\nfor  the secret-{i} now", "attack", f"secret-{i}") for i in range(n)] + \
           [mk(f"b{i}", f"ok  Wei Zhang") for i in range(n)]


def test_variants_never_touch_marker_or_args():
    args = '{"to":  "x  y\\nz"}'
    msgs = [{"role": "user", "content": "Hi there friend"},
            {"role": "assistant", "content": "do  it\nnow", "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "f", "arguments": args}}]}]
    c = mk("t", messages=msgs, target=1, label="attack", marker="do  it\nnow", checkpoint="tool_call")
    for kind in ("reflow", "prefix", "rename"):
        v = rel.variants(c, kind, 1)
        if v is not None:
            assert has_marker(v.messages[1], c.marker)
            assert v.messages[1]["tool_calls"][0]["function"]["arguments"] == args
    assert rel.variants(c, "reflow", 1) is None  # nothing outside the marker to change
    c2 = mk("u", "a  b  SECRET  c", "attack", "SECRET")
    v = rel.variants(c2, "reflow", 1)
    assert v.messages[0]["content"] == "a b SECRET c"
    assert rel.variants(c2, "prefix", 1).messages[0]["content"].startswith("Thanks in advance.")
    assert c2.messages[0]["content"] == "a  b  SECRET  c"  # original untouched


def test_rename_fires_on_common_names_and_is_consistent():
    c = mk("r", "Dear Maria Lopez and Wei Zhang, hello. Maria Lopez agrees. Monday Morning is not a name.")
    a, b = rel.variants(c, "rename", 5), rel.variants(c, "rename", 5)
    assert a == b and a.id == c.id
    t = a.messages[0]["content"]
    assert "Maria Lopez" not in t and "Wei Zhang" not in t and "Monday Morning" in t
    assert t.count(t.split(" and ")[0][5:]) == 2  # same replacement for both mentions
    assert rel.variants(mk("n", "no names"), "rename", 5) is None
    assert rel.variants(mk("n", "Zzyzx Lopez"), "rename", 5) is None  # first word not in the list


def test_rename_spares_marker_and_arguments():
    args = '{"to": "Maria Lopez"}'
    msgs = [{"role": "user", "content": "Ask John Smith. Then Maria Lopez says: send it to Maria Lopez"},
            {"role": "assistant", "content": "", "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "f", "arguments": args}}]}]
    c = mk("t", messages=msgs, label="attack", marker="send it to Maria Lopez", checkpoint="prompt")
    v = rel.variants(c, "rename", 3)
    assert "John Smith" not in v.messages[0]["content"] and "send it to Maria Lopez" in v.messages[0]["content"]
    assert v.messages[1]["tool_calls"][0]["function"]["arguments"] == args


def test_per_section_rng_is_independent(tmp_path):
    cs = attack_cases(30)
    seen = {}
    for flag in (0, 8):
        r = rel.run_reliability(FakeAdapter(rules=["secret"]), cs, tmp_path / str(flag), load_n=flag, lengths=(4000,),
                                length_n=5, variants=(), repeats=1, concurrency=(1,))
        seen[flag] = sorted(json.loads(l)["case_id"] for l in (tmp_path / str(flag) / "long_4000.jsonl").read_text().splitlines())
    assert seen[0] == seen[8]


def test_flip_counts_error_flips():
    f = rel._flips([["allow", "allow"], ["allow", "block"], ["block", "error"], ["error", "error"], ["allow", "error"]])
    assert f == {"n": 5, "flips": 3, "flip_rate": 0.6, "error_flips": 2}


def test_consistency_zero_for_deterministic_adapter(tmp_path):
    r = rel.run_reliability(FakeAdapter(rules=["secret"]), attack_cases(), tmp_path, load_n=0, lengths=())
    assert r["consistency"]["overall"]["flip_rate"] == 0
    assert set(r["consistency"]) >= {"overall", "by_checkpoint", "by_label"}
    assert json.loads((tmp_path / "reliability.json").read_text())["consistency"] == r["consistency"]
    assert len(list(tmp_path.glob("*.jsonl"))) >= 3
    c = rel.run_reliability(Coin(), attack_cases(20), tmp_path / "c", load_n=0, lengths=())
    assert c["consistency"]["overall"]["flip_rate"] > 0


def test_stability_reports_attack_and_benign(tmp_path):
    r = rel.run_reliability(FakeAdapter(rules=["secret"]), attack_cases(), tmp_path, load_n=0, lengths=())
    s = r["stability"]
    assert set(s) == {"reflow", "prefix", "rename"}
    for k in s:
        assert s[k]["attack"]["n"] == 6 and s[k]["benign"]["n"] == 6
        assert s[k]["attack"]["instability"] == 0


def test_long_input_same_sample_and_benign_control(tmp_path):
    seen = []

    class Len(FakeAdapter):
        def judge(self, messages, target, mode):
            seen.append(len(messages[target]["content"]))
            return super().judge(messages, target, mode)

    cs = attack_cases(4) + [mk("x", [], "attack", "m", messages=[{"role": "user", "content": None}]),
                            mk("big", "z" * 5000 + " secret-9", "attack", "secret-9")]
    r = rel.run_reliability(Len(rules=["secret"]), cs, tmp_path, load_n=0, lengths=(4000, 16000), length_n=3,
                            variants=(), repeats=1)
    assert set(r["long_input"]) == {"4000", "16000"}
    for L in ("4000", "16000"):
        assert r["long_input"][L]["n"] == 3 and r["long_input"][L]["detection"] == 1.0  # "big" never sampled
        assert r["long_input"][L]["control"]["n"] == 3 and r["long_input"][L]["control"]["false_block"] == 0.0
    ids = [{json.loads(l)["case_id"] for l in (tmp_path / f"long_{L}.jsonl").read_text().splitlines()} for L in (4000, 16000)]
    assert ids[0] == ids[1]
    assert 4000 in seen and 16000 in seen


def test_load_levels_reported(tmp_path):
    r = rel.run_reliability(Coin(p_err=0.3), attack_cases(), tmp_path, load_n=8, concurrency=(1, 4), lengths=(),
                            variants=(), repeats=1)
    assert set(r["load"]) == {"1", "4"}
    for lv in r["load"].values():
        assert lv["n"] == 8 and lv["p95_ms"] >= lv["p50_ms"] and 0 <= lv["error_rate"] <= 1
    assert r["failure"]["errors"] > 0 and "operational" in r["failure"]


def test_cli_reliability_writes_json(tmp_path):
    cases = tmp_path / "c.jsonl"
    from dataclasses import asdict
    cases.write_text("\n".join(json.dumps(asdict(c)) for c in attack_cases()))
    out = tmp_path / "out"
    assert main(["reliability", "--product", "fake", "--cases", str(cases), "--out", str(out),
                 "--repeats", "2", "--no-load", "--no-long"]) == 0
    d = json.loads((out / "reliability.json").read_text())
    assert set(d) == {"consistency", "stability", "load", "long_input", "failure", "meta"}


def test_failure_counts_all_subruns(tmp_path):
    r = rel.run_reliability(Coin(p_err=0.5), attack_cases(), tmp_path, load_n=6, concurrency=(1,), lengths=(4000,),
                            length_n=3, repeats=2)
    f = r["failure"]
    assert set(f["by_section"]) == {"base", "variants", "load", "long_input"}
    assert f["errors"] == sum(t["errors"] for t in f["by_section"].values())
    assert f["by_section"]["variants"]["errors"] > 0 and f["by_section"]["long_input"]["rows"] > 0


def test_cli_timeout_passed(tmp_path, monkeypatch):
    got = {}
    monkeypatch.setattr(rel, "run_reliability", lambda *a, **k: got.update(k) or {})
    cases = tmp_path / "c.jsonl"
    from dataclasses import asdict
    cases.write_text("\n".join(json.dumps(asdict(c)) for c in attack_cases(1)))
    assert main(["reliability", "--product", "fake", "--cases", str(cases), "--out", str(tmp_path / "o"),
                 "--timeout", "7"]) == 0
    assert got["timeout_s"] == 7.0


class Keyword(FakeAdapter):
    """Test-only: blocks when the text STARTS with the keyword, so a prefix changes the decision."""
    name = "kw"

    def judge(self, messages, target, mode):
        return Verdict("block" if str(messages[target]["content"]).startswith("secret") else "allow", 1.0)


class Alternating(FakeAdapter):
    """Test-only: flips its answer on every call."""
    name = "alt"

    def __init__(self):
        super().__init__()
        self.n = 0

    def judge(self, messages, target, mode):
        self.n += 1
        return Verdict("block" if self.n % 2 else "allow", 1.0)


def test_stability_and_consistency_detect_change(tmp_path):
    cs = [mk(f"k{i}", f"secret thing {i}", "attack", "thing") for i in range(4)]
    r = rel.run_reliability(Keyword(), cs, tmp_path, load_n=0, lengths=(), variants=("prefix", "reflow"), repeats=2)
    assert r["stability"]["prefix"]["attack"]["instability"] == 1.0
    assert r["consistency"]["overall"]["flip_rate"] == 0
    r = rel.run_reliability(Alternating(), cs[:3], tmp_path / "alt", load_n=0, lengths=(), variants=(), repeats=2, workers=1)
    assert r["consistency"]["overall"]["flip_rate"] == 1.0


def test_rerun_same_dir_resumes_and_different_seed_refused(tmp_path):
    cs = attack_cases()
    kw = dict(load_n=4, concurrency=(1,), lengths=(), variants=(), repeats=1)
    a = rel.run_reliability(FakeAdapter(rules=["secret"]), cs, tmp_path, **kw)
    b = rel.run_reliability(FakeAdapter(rules=["secret"]), cs, tmp_path, **kw)
    assert b["load"]["1"]["n"] == 4 and b["consistency"] == a["consistency"]
    import pytest
    with pytest.raises(ValueError, match="different settings"):
        rel.run_reliability(FakeAdapter(rules=["secret"]), cs, tmp_path, seed=1, **kw)
    cases = tmp_path / "c.jsonl"
    from dataclasses import asdict
    cases.write_text("\n".join(json.dumps(asdict(c)) for c in cs))
    assert main(["reliability", "--product", "fake", "--cases", str(cases), "--out", str(tmp_path),
                 "--no-load", "--no-long", "--seed", "5"]) == 2


def test_stale_rows_from_larger_run_not_counted(tmp_path):
    cs = attack_cases()
    kw = dict(load_n=0, lengths=(), variants=(), repeats=1)
    rel.run_reliability(FakeAdapter(rules=["secret"]), cs, tmp_path, **kw)
    (tmp_path / "reliability.json").unlink()  # same repeat0.jsonl, now a smaller case list
    r = rel.run_reliability(FakeAdapter(rules=["secret"]), cs[:2], tmp_path, **kw)
    assert r["consistency"]["overall"]["n"] == 2 and r["failure"]["by_section"]["base"]["rows"] == 2


def test_load_count_stays_after_resume(tmp_path):
    cs = [mk(f"b{i}", "hello") for i in range(300)]
    kw = dict(load_n=200, concurrency=(1,), lengths=(), variants=(), repeats=1)
    for _ in range(2):
        r = rel.run_reliability(FakeAdapter(), cs, tmp_path, **kw)
        assert r["load"]["1"]["n"] == 200


def test_operational_excludes_unclaimed(tmp_path):
    r = rel.run_reliability(FakeAdapter(rules=["secret"], native_checkpoints=[], accepts_text=False), attack_cases(), tmp_path,
                            load_n=0, lengths=(), variants=(), repeats=1)
    assert r["failure"]["operational"] == {"detection": None, "false_block": None}


class ErrOnPrefix(FakeAdapter):
    def judge(self, messages, target, mode):
        if str(messages[target]["content"]).startswith("Thanks"):
            return Verdict("error", error="boom")
        return super().judge(messages, target, mode)


def test_stability_errors_not_changed(tmp_path):
    r = rel.run_reliability(ErrOnPrefix(rules=["secret"]), attack_cases(), tmp_path, load_n=0, lengths=(),
                            variants=("prefix",), repeats=1)
    s = r["stability"]["prefix"]["attack"]
    assert s["errors"] == 6 and s["changed"] == 0 and s["instability"] is None


def test_rename_distinct_names_within_case():
    c = mk("m", "Maria Lopez, John Smith, Wei Zhang, Anna Berg, Paul Kane, Emma Hall, Olga Rus, Ivan Pop")
    t = rel.variants(c, "rename", 3).messages[0]["content"]
    assert len(set(t.split(", "))) == 8

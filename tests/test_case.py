import dataclasses
import json
import subprocess
import sys
from pathlib import Path

from guardrailbench.case import Case, load_cases, validate

SEED = Path(__file__).parent.parent / "cases" / "practice" / "seed.jsonl"
CANARY = "GRB-CANARY-12345678-1234-4234-8234-123456789abc"


def mk(**kw):
    d = dict(
        id="a", version=1, split="practice", family=1, checkpoint="prompt",
        messages=[{"role": "user", "content": "hi GRB-MARKER-x1"}], target=0,
        label="attack", twin_id=None, twin_change=None, transform=None,
        source_pattern=None, canary=CANARY, marker="GRB-MARKER-x1",
        deployment_card=None,
    )
    d.update(kw)
    return Case(**d)


def pair():
    a = mk(id="a", twin_id="b", twin_change="intent")
    b = mk(id="b", label="benign", marker=None, twin_id="a", twin_change="intent",
           messages=[{"role": "user", "content": "hi"}])
    return a, b


def test_load_seed():
    cases = load_cases(SEED)
    assert len(cases) >= 20 and all(isinstance(c, Case) for c in cases)


def test_valid_seed_has_no_problems():
    assert validate(load_cases(SEED)) == []


def test_seed_coverage_and_unicode():
    cases = load_cases(SEED)
    assert {1, 3, 4, 5, 6} <= {c.family for c in cases}
    assert {"prompt", "ingested_content", "tool_call", "trajectory"} <= {c.checkpoint for c in cases}
    assert any(0xE0000 <= ord(ch) <= 0xE007F for c in cases for ch in json.dumps(c.messages, ensure_ascii=False))


def test_pair_is_valid():
    assert validate(list(pair())) == []


def test_attack_without_marker():
    a, b = pair()
    a = dataclasses.replace(a, marker=None)
    assert any("marker" in p for p in validate([a, b]))


def test_marker_not_in_target():
    a, b = pair()
    a = dataclasses.replace(a, marker="GRB-MARKER-zzz")
    assert any("marker" in p for p in validate([a, b]))


def test_benign_with_marker_string():
    a, b = pair()
    b = dataclasses.replace(b, messages=[{"role": "user", "content": "GRB-MARKER-x1"}])
    assert any("GRB-MARKER-" in p for p in validate([a, b]))


def test_twin_must_exist_and_point_back():
    a, b = pair()
    assert any("twin" in p for p in validate([a]))
    b = dataclasses.replace(b, twin_id=None, twin_change=None)
    assert any("twin" in p for p in validate([a, b]))


def test_unknown_checkpoint():
    a, b = pair()
    assert any("checkpoint" in p for p in validate([dataclasses.replace(a, checkpoint="nope"), b]))


def test_duplicate_id():
    a, b = pair()
    assert any("duplicate" in p for p in validate([a, b, b]))


def test_target_out_of_range():
    a, b = pair()
    assert any("target" in p for p in validate([dataclasses.replace(a, target=5), b]))


def test_canary_format():
    a, b = pair()
    assert any("canary" in p for p in validate([dataclasses.replace(a, canary="GRB-CANARY-x"), b]))


def test_bad_json_line_reports_line_number(tmp_path):
    a, b = pair()
    p = tmp_path / "seed.jsonl"
    p.write_text("\n".join([json.dumps(dataclasses.asdict(a)), json.dumps(dataclasses.asdict(b)), "{broken"]))
    problems = validate(load_cases(p))
    assert any("seed.jsonl:3" in x for x in problems)


def test_unicode_roundtrip(tmp_path):
    txt = "a\U000e0041​b GRB-MARKER-x1"
    a, b = pair()
    a = dataclasses.replace(a, messages=[{"role": "user", "content": txt}])
    p = tmp_path / "u.jsonl"
    p.write_text(json.dumps(dataclasses.asdict(a), ensure_ascii=False) + "\n", encoding="utf-8")
    assert load_cases(p)[0].messages[0]["content"] == txt


def test_cli():
    r = subprocess.run([sys.executable, "-m", "guardrailbench.cli", "validate", str(SEED.parent)])
    assert r.returncode == 0

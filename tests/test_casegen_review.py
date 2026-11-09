import json

from guardrailbench.cli import main
from guardrailbench.case import load_cases
from guardrailbench.casegen import agree, assemble, blind, lint
from test_casegen import cases_from, fixture, pair, single, write
import pytest


def test_blind_keys_opaque_and_agree_works(tmp_path):
    d = fixture(tmp_path)
    out = tmp_path / "b.jsonl"
    blind(d, out, 3)
    keys = [json.loads(l)["key"] for l in out.read_text().splitlines()]
    assert len(set(keys)) == 9
    assert all(":" not in k and "a.jsonl" not in k for k in keys)
    v = tmp_path / "v.jsonl"
    v.write_text("\n".join(json.dumps({"key": k, "label": "attack", "problems": []}) for k in keys))
    bad = agree(d, v)
    # 3 attacks agree; 3 pair-benign and 3 single-benign disagree
    assert len(bad) == 6 and {b["true_label"] for b in bad} == {"benign"}


def test_lint_allows_reserved_hosts_and_flags_real(tmp_path):
    def probs(host):
        p = pair(1)
        p["benign"]["messages"][0]["content"] += f" http://{host}/x"
        p["attack"]["messages"][0]["content"] += f" http://{host}/x"
        return lint(cases_from(tmp_path, [p]))
    for h in ("localhost", "10.0.0.1:8080", "example.com", "api.example.org", "example.net"):
        assert probs(h) == [], h
    for h in ("notexample.com", "evil.org", "example.com.evil.io"):
        assert probs(h), h


def test_cli_lint_reports_load_errors(tmp_path, capsys):
    f = tmp_path / "bad.jsonl"
    f.write_text("not json\n")
    assert main(["casegen", "lint", str(f)]) == 1


def test_agree_missing_key_and_no_verdict(tmp_path):
    d = write(tmp_path, [pair(1), single("prompt")])
    v = tmp_path / "v.jsonl"
    v.write_text(json.dumps({"label": "attack"}))
    with pytest.raises(ValueError):
        agree(d, v)
    assert main(["casegen", "agree", "--drafts", str(d), "--verdicts", str(v)]) == 2
    v.write_text("")
    bad = agree(d, v)
    assert len(bad) == 3 and all(b["problems"] == ["no verdict"] for b in bad)

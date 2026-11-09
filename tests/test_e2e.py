import json
import re
from pathlib import Path

from guardrailbench.cli import main

CASES = Path(__file__).parent.parent / "cases" / "practice"


def test_seed_end_to_end_with_fake(tmp_path, capsys):
    raw = tmp_path / "raw.jsonl"
    rep_dir = tmp_path / "results" / "fake" / "practice"
    report = rep_dir / "report.json"
    site = tmp_path / "site"
    assert main(["validate", str(CASES)]) == 0
    assert main(["run", "--product", "fake", "--cases", str(CASES), "--out", str(raw)]) == 0
    assert main(["score", "--results", str(raw), "--cases", str(CASES), "--out", str(report)]) == 0
    assert main(["leaderboard", "--results", str(tmp_path / "results"), "--out", str(site)]) == 0
    capsys.readouterr()
    assert main(["hash", str(CASES)]) == 0
    assert re.fullmatch(r"[0-9a-f]{64}", capsys.readouterr().out.strip())
    assert "fake" in (site / "index.html").read_text(encoding="utf-8")
    g = json.loads(report.read_text(encoding="utf-8"))["native"]["all"]
    # registered fake allows everything (Ruling 14): this is a plumbing check only
    assert g["detection"] == 0.0 and g["false_block"] == 0.0


def test_fake_with_seed_markers_is_perfect(tmp_path):
    from guardrailbench.adapters.fake import FakeAdapter
    from guardrailbench.case import load_cases
    from guardrailbench.metrics import report
    from guardrailbench.run import run
    cases = load_cases(CASES / "seed.jsonl")
    out = tmp_path / "raw.jsonl"
    run(FakeAdapter(rules=[c.marker for c in cases if c.marker]), cases, out)
    results = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    g = report(results, cases)["native"]["all"]
    assert g["detection"] == 1.0 and g["false_block"] == 0.0 and g["n_attack"] == 10 and g["n_benign"] == 10

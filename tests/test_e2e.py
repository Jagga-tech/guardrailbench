import json
import re
from pathlib import Path

from guardrailbench.cli import main

CASES = Path(__file__).parent.parent / "cases" / "practice"


def test_seed_end_to_end_with_fake(tmp_path, capsys):
    raw = tmp_path / "raw.jsonl"
    rep_dir = tmp_path / "results" / "fake" / "practice"
    rep_dir.mkdir(parents=True)
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
    # fake adapter is a perfect detector on the seed
    assert g["detection"] == 1.0 and g["false_block"] == 0.0

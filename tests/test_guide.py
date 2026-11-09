import json
import re
import shutil
from pathlib import Path

from guardrailbench.case import load_cases, validate
from guardrailbench.casegen import assemble, lint

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "guide_pairs.jsonl"
GUIDE = ROOT / "docs" / "case-writing-guide.md"


def fixture_pairs():
    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_guide_examples_assemble_and_lint(tmp_path):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    shutil.copy(FIXTURE, drafts / "guide.jsonl")
    counts = assemble(drafts, tmp_path / "p.jsonl", tmp_path / "o.jsonl")
    assert counts["pairs"] == 7
    cases = load_cases(tmp_path / "p.jsonl") + load_cases(tmp_path / "o.jsonl")
    assert validate(cases) == []
    assert lint(cases) == []


def test_guide_pairs_cover_each_checkpoint_with_good_markers():
    pairs = fixture_pairs()
    assert sorted(p["checkpoint"] for p in pairs) == sorted(
        ["prompt", "ingested_content", "tool_definition", "tool_call", "memory_write", "output", "trajectory"])
    for p in pairs:
        assert 4 <= len(p["attack"]["marker"].split()) <= 12, p["attack"]["marker"]


def test_guide_json_matches_fixture():
    text = GUIDE.read_text(encoding="utf-8")
    blocks = re.findall(r"<!-- worked-pair -->\n```json\n(.*?)\n```", text, re.S)
    assert [json.loads(b) for b in blocks] == fixture_pairs()

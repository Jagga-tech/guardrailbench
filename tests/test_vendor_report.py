"""vendor-report: totals and practice ids only. Nothing from a hidden case may reach the output."""
import json
import uuid
from dataclasses import replace
from pathlib import Path

import pytest

from guardrailbench.adapters.fake import FakeAdapter
from guardrailbench.case import load_cases
from guardrailbench.cli import main
from guardrailbench.metrics import report
from guardrailbench.run import run
from guardrailbench.vendor_report import build, render

ROOT = Path(__file__).resolve().parent.parent
RULES = ["ignore", "password", "send", "delete"]  # a crude product: some misses, some over-blocks


def hidden_copy(cases):
    """A stand-in hidden split: the practice cases with new ids, canaries and text."""
    out = []
    for n, c in enumerate(cases):
        msgs = [{**m, "content": f"{m['content']} HIDDENTEXT-{n}"} if isinstance(m.get("content"), str) else m
                for m in c.messages]
        out.append(replace(c, id=f"hid-{c.id}", twin_id=c.twin_id and f"hid-{c.twin_id}", split="official",
                           canary=f"GRB-CANARY-{uuid.uuid4()}", messages=msgs,
                           marker=c.marker and f"{c.marker} HIDDENMARK-{n}"))
    return out


def rows(adapter, cases, path):
    run(adapter, cases, path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("vr")
    practice = load_cases(ROOT / "cases" / "practice" / "v1.jsonl")
    hidden = hidden_copy(practice)
    return {"practice": practice, "hidden": hidden, "tmp": tmp,
            "p_rows": rows(FakeAdapter(RULES), practice, tmp / "practice.jsonl"),
            "h_rows": rows(FakeAdapter(RULES), hidden, tmp / "hidden.jsonl")}


def test_report_has_totals_and_practice_ids_but_nothing_hidden(data):
    rep = build(data["h_rows"], data["hidden"], data["p_rows"], data["practice"])
    text = json.dumps(rep) + render(rep)

    for c in data["hidden"]:
        assert c.id not in text and c.canary not in text
        assert not c.marker or c.marker not in text
        for m in c.messages:
            assert not m.get("content") or m["content"] not in text
    assert "hid-" not in text and "HIDDENTEXT" not in text and "HIDDENMARK" not in text and "GRB-CANARY" not in text
    for row_key in ('"case_id"', '"steps"', '"raw"', '"messages"', '"deployment_card"', '"marker"'):
        assert row_key not in text

    # same numbers as `score`
    assert rep["by_mode"]["native"] == report(data["h_rows"], data["hidden"])["native"]["all"]
    assert set(rep["breakdowns"]) == {"checkpoint", "family", "sector", "twin_change"}
    assert rep["breakdowns"]["twin_change"]["native"]["intent"]["pairs"]["n"] > 0

    # weak groups name practice cases, and only practice cases
    weak = rep["weak_groups"]
    assert weak and all(g["miss"] + g["over_block"] + g["inverted"] > 0 for g in weak)
    named = {i for g in weak for ids in g["practice_cases"].values() for i in ids}
    assert named and named <= {c.id for c in data["practice"] if c.label == "attack"}
    assert all(f"`{i}`" in render(rep) or i in json.dumps(rep) for i in named)
    assert sorted(named)[0] in render(rep)


def test_group_without_a_practice_failure_says_so(data):
    one_family = [c for c in data["practice"] if c.family == 1]
    ids = {c.id for c in one_family}
    rep = build(data["h_rows"], data["hidden"], [r for r in data["p_rows"] if r["case_id"] in ids], one_family)
    other = [g for g in rep["weak_groups"] if g["family"] != 1]
    assert other and all(ids == [] for g in other for ids in g["practice_cases"].values())
    assert "none in the practice run" in render(rep)
    # and with no practice run at all, no ids
    rep = build(data["h_rows"], data["hidden"])
    assert not rep["practice_run_given"] and all("practice_cases" not in g for g in rep["weak_groups"])
    assert "no practice run given" in render(rep)


def test_hidden_cases_are_refused_as_examples(data):
    with pytest.raises(ValueError, match="split 'practice'"):  # hidden cases passed as the practice set
        build(data["h_rows"], data["hidden"], data["h_rows"], data["hidden"])
    with pytest.raises(ValueError, match="share ids"):  # same ids on both sides
        build(data["p_rows"], data["practice"], data["p_rows"], data["practice"])
    other = [{**r, "product": "someone-else"} for r in data["p_rows"]]
    with pytest.raises(ValueError, match="practice run is"):
        build(data["h_rows"], data["hidden"], other, data["practice"])


def test_cli_writes_json_and_markdown(data, tmp_path, capsys):
    tmp = data["tmp"]
    (tmp / "hidden_cases.jsonl").write_text("".join(json.dumps(c.__dict__) + "\n" for c in data["hidden"]),
                                            encoding="utf-8")
    args = ["vendor-report", "--results", str(tmp / "hidden.jsonl"), "--cases", str(tmp / "hidden_cases.jsonl"),
            "--out", str(tmp_path)]
    practice = ["--practice-results", str(tmp / "practice.jsonl"),
                "--practice-cases", str(ROOT / "cases" / "practice" / "v1.jsonl")]
    assert main(args + practice[:2]) == 2  # practice results without practice cases
    assert main(args + practice) == 0
    rep = json.loads((tmp_path / "vendor-report.json").read_text(encoding="utf-8"))
    md = (tmp_path / "vendor-report.md").read_text(encoding="utf-8")
    assert rep["product"] == "fake" and md.startswith("# GuardrailBench vendor report: fake")
    assert "hid-" not in json.dumps(rep) + md
    # the practice set given as the hidden one, and the hidden one as practice: refused
    assert main(["vendor-report", "--results", str(tmp / "practice.jsonl"),
                 "--cases", str(ROOT / "cases" / "practice" / "v1.jsonl"),
                 "--practice-results", str(tmp / "hidden.jsonl"),
                 "--practice-cases", str(tmp / "hidden_cases.jsonl"), "--out", str(tmp_path / "x")]) == 2
    assert not (tmp_path / "x").exists()

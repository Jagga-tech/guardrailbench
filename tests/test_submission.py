import json

from guardrailbench.adapters.fake import FakeAdapter
from guardrailbench.cli import main
from guardrailbench.run import run
from guardrailbench.submission import check_complete, load_results, spot_check
from test_run import mk


def cases():
    return [mk("a", "GRB-MARKER-1", label="attack"), mk("b"), mk("c")]


def good(tmp_path):
    out = tmp_path / "r.jsonl"
    run(FakeAdapter(), cases(), out)
    return out, [json.loads(l) for l in out.read_text().splitlines()]


def test_complete_ok(tmp_path):
    _, res = good(tmp_path)
    assert check_complete(res, cases()) == []


def test_missing_case_rejected(tmp_path):
    _, res = good(tmp_path)
    p = check_complete(res[:-1], cases())
    assert len(p) == 1 and "missing" in p[0]


def test_extra_and_duplicate_rejected(tmp_path):
    _, res = good(tmp_path)
    p = check_complete(res + [res[0], {**res[0], "case_id": "zzz"}], cases())
    assert any("duplicate" in x and res[0]["case_id"] in x for x in p)
    assert any("extra" in x and "zzz" in x for x in p)


def test_missing_logs_rejected(tmp_path):
    _, res = good(tmp_path)
    del res[0]["steps"]
    res[1]["steps"] = []
    res[2]["decision"] = "not_claimed"
    res[2]["steps"] = []
    p = check_complete(res, cases())
    assert len(p) == 2 and all("logs" in x for x in p)


def test_bad_json_line_reported(tmp_path):
    f = tmp_path / "r.jsonl"
    f.write_text('{"case_id": "a"}\nnot json\n')
    res, p = load_results(f)
    assert len(res) == 1 and "line 2" in p[0]


def test_spot_check_catches_edited_verdict(tmp_path):
    _, res = good(tmp_path)
    res[0]["decision"] = "allow"  # was block
    p = spot_check(res, cases(), FakeAdapter(), k=3)
    assert len(p) == 1 and "a" in p[0] and "allow" in p[0] and "block" in p[0]


def test_spot_check_ignores_errors(tmp_path):
    _, res = good(tmp_path)
    res[0]["decision"] = "error"
    p = spot_check(res, cases(), FakeAdapter(), k=3)
    assert not any("disagree" in x for x in p) and any("error" in x for x in p)


def test_cli(tmp_path, capsys):
    out, res = good(tmp_path)
    cp = tmp_path / "cases"
    cp.mkdir()
    (cp / "x.jsonl").write_text("")
    # cli loads cases from a path; reuse load_cases monkeypatch-free by checking unknown product
    assert main(["verify-submission", "--results", str(out), "--cases", str(cp), "--rerun", "nope"]) == 2

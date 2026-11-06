import json

from guardrailbench.adapters.fake import FakeAdapter
from guardrailbench.cli import main
from guardrailbench.run import run
from guardrailbench.submission import check_complete, load_results, spot_check
from test_run import EVIL, mk


def cases():
    return [mk("a", "evil-1", label="attack"), mk("b"), mk("c")]


def rec(res, cid):
    return next(r for r in res if r["case_id"] == cid)


def good(tmp_path):
    out = tmp_path / "r.jsonl"
    run(FakeAdapter(rules=EVIL), cases(), out)
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
    del rec(res, "a")["steps"]
    rec(res, "b")["steps"] = []
    rec(res, "c")["decision"] = "not_claimed"
    rec(res, "c")["steps"] = []
    p = check_complete(res, cases())
    assert len(p) == 2 and all("logs" in x for x in p)


def test_bad_json_line_reported(tmp_path):
    f = tmp_path / "r.jsonl"
    f.write_text('{"case_id": "a"}\nnot json\n')
    res, p = load_results(f)
    assert len(res) == 1 and "line 2" in p[0]


def test_spot_check_catches_edited_verdict(tmp_path):
    _, res = good(tmp_path)
    rec(res, "a")["decision"] = "allow"  # was block
    p = spot_check(res, cases(), FakeAdapter(rules=EVIL), k=3)
    assert len(p) == 1 and "a" in p[0] and "allow" in p[0] and "block" in p[0]


def test_spot_check_submitted_error_is_disagreement(tmp_path):
    # Ruling 15: padding with "error" to dodge comparison is caught
    _, res = good(tmp_path)
    rec(res, "a")["decision"] = "error"
    p = spot_check(res, cases(), FakeAdapter(rules=EVIL), k=3)
    assert p == ["disagree: a submitted error, re-run block"]


def test_cli(tmp_path, capsys):
    out, res = good(tmp_path)
    cp = tmp_path / "cases"
    cp.mkdir()
    (cp / "x.jsonl").write_text("")
    # cli loads cases from a path; reuse load_cases monkeypatch-free by checking unknown product
    assert main(["verify-submission", "--results", str(out), "--cases", str(cp), "--rerun", "nope"]) == 2


class Boom(FakeAdapter):
    def judge(self, messages, target, mode):
        raise RuntimeError("no key")


def test_spot_check_all_rerun_errors_is_problem(tmp_path):
    _, res = good(tmp_path)
    p = spot_check(res, cases(), Boom(), k=3)
    assert any(x.startswith("spot-check unverified") for x in p)


def test_spot_check_all_submitted_errors_are_disagreements(tmp_path):
    _, res = good(tmp_path)
    for r in res:
        r["decision"] = "error"
    p = spot_check(res, cases(), FakeAdapter(rules=EVIL), k=3)
    assert sum(x.startswith("disagree") for x in p) == 3


def test_spot_check_one_error_among_many_is_note(tmp_path):
    cs = [mk(f"c{i}") for i in range(6)]
    out = tmp_path / "r.jsonl"
    run(FakeAdapter(rules=EVIL), cs, out)
    res = [json.loads(l) for l in out.read_text().splitlines()]

    class OneDown(FakeAdapter):
        def judge(self, messages, target, mode):
            if messages[0]["content"] == "boom":
                raise RuntimeError("down")
            return super().judge(messages, target, mode)
    cs[0] = mk("c0", "boom")
    p = spot_check(res, cs, OneDown(), k=6)  # re-run-side error only
    assert len(p) == 1 and p[0].startswith("note:")


def write_cases(tmp_path):
    import dataclasses
    cp = tmp_path / "cases"
    cp.mkdir()
    (cp / "x.jsonl").write_text("".join(json.dumps(dataclasses.asdict(c)) + "\n" for c in cases()))
    return cp


def test_cli_exit_0_and_prints_seed(tmp_path, capsys):
    out = tmp_path / "r.jsonl"
    run(FakeAdapter(), cases(), out)  # the registered "fake" uses default rules
    cp = write_cases(tmp_path)
    assert main(["verify-submission", "--results", str(out), "--cases", str(cp), "--rerun", "fake"]) == 0
    assert "seed: " in capsys.readouterr().out
    assert main(["verify-submission", "--results", str(out), "--cases", str(cp), "--rerun", "fake", "--seed", "7"]) == 0
    assert "seed: 7" in capsys.readouterr().out


def test_cli_exit_1_on_problem(tmp_path, capsys):
    out, res = good(tmp_path)
    cp = write_cases(tmp_path)
    out.write_text("".join(json.dumps(r) + "\n" for r in res[:-1]))
    assert main(["verify-submission", "--results", str(out), "--cases", str(cp)]) == 1
    assert "missing case" in capsys.readouterr().out


def test_spot_check_mode_and_score_must_match(tmp_path):
    _, res = good(tmp_path)
    rec(res, "b")["mode"] = "flattened"
    rec(res, "c")["steps"][0]["score"] = 0.5  # fake scores 0.0
    p = spot_check(res, cases(), FakeAdapter(rules=EVIL), k=3)
    assert any("b submitted mode flattened, re-run native" in x for x in p)
    assert any("c submitted score 0.5, re-run 0.0" in x for x in p)
    rec(res, "c")["steps"][0]["score"] = 0.0 + 1e-9  # within tolerance
    assert not any(" c " in x for x in spot_check(res, cases(), FakeAdapter(rules=EVIL), k=3))


def test_check_complete_rejects_unknown_decision_and_mode(tmp_path):
    _, res = good(tmp_path)
    rec(res, "a")["decision"] = "maybe"
    rec(res, "b")["mode"] = "hybrid"
    p = check_complete(res, cases())
    assert any("bad decision: a" in x for x in p) and any("bad mode: b" in x for x in p)

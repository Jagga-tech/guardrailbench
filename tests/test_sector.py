import json

from guardrailbench.adapters.fake import FakeAdapter
from guardrailbench.case import Case, load_cases, validate
from guardrailbench.casegen import DOMAIN_TO_SECTOR, _canon, assemble
from guardrailbench.metrics import report
from guardrailbench.run import run
from test_casegen import pair, single, write

CANARY = "GRB-CANARY-12345678-1234-4234-8234-123456789abc"


def mk(id, label="benign", sector=None, marker=None):
    return Case(id=id, version=1, split="practice", family=1, checkpoint="prompt",
                messages=[{"role": "user", "content": "hi"}], target=0, label=label, twin_id=None,
                twin_change=None, transform=None, source_pattern=None, canary=CANARY, marker=marker,
                deployment_card=None, sector=sector)


def res(id, decision, fail_mode=None):
    return {"case_id": id, "mode": "native", "decision": decision, "fail_mode": fail_mode, "sanitized": None,
            "steps": [{"target": 0, "decision": decision, "score": None, "latency_ms": 5, "error": None}]}


def test_sector_must_be_known():
    assert not [p for p in validate([mk("x", sector="finance")]) if "sector" in p]
    assert not [p for p in validate([mk("x")]) if "sector" in p]
    assert any("sector" in p for p in validate([mk("x", sector="piracy")]))


def test_old_files_load_without_sector(tmp_path):
    d = {k: v for k, v in mk("x").__dict__.items() if k != "sector"}
    f = tmp_path / "a.jsonl"
    f.write_text(json.dumps(d) + "\n")
    assert load_cases(f)[0].sector is None


def test_assemble_maps_domain_to_sector(tmp_path):
    d = write(tmp_path, [pair(1, sector="legal"), single("prompt", "IT Helpdesk"), single("tool_call", "weird"),
                         single("output", "finance")])
    p, o = tmp_path / "p.jsonl", tmp_path / "o.jsonl"
    assemble(d, p, o)
    cs = load_cases(p) + load_cases(o)
    assert {c.sector for c in cs if c.id.startswith("v1-bn")} == {"software_it", "general", "finance"}
    assert {c.sector for c in cs if not c.id.startswith("v1-bn")} == {"legal"}
    assert DOMAIN_TO_SECTOR["non-profit"] == "nonprofit"


def test_sector_excluded_from_sort_hash():
    assert _canon(pair(1)) == _canon(pair(1, sector="legal"))


def test_report_without_sector():
    rep = report([res("a", "block")], [mk("a")])
    assert rep["native"]["sector"]["unknown"]["n_benign"] == 1


def test_sector_breakdown():
    cs = [mk("a", sector="finance"), mk("b", sector="health")]
    rep = report([res("a", "block"), res("b", "allow")], cs)
    s = rep["native"]["sector"]
    assert s["finance"]["false_block"] == 1 and s["health"]["false_block"] == 0


def test_fail_mode_default_open():
    cs = [mk("a", "attack", marker="m"), mk("b")]
    g = report([res("a", "error"), res("b", "error")], cs)["native"]["all"]
    assert g["operational"] == {"detection": 0.0, "false_block": 0.0}


def test_fail_mode_closed_counts_error_as_stop():
    cs = [mk("a", "attack", marker="m"), mk("b")]
    g = report([res("a", "error", "closed"), res("b", "error", "closed")], cs)["native"]["all"]
    assert g["operational"] == {"detection": 1.0, "false_block": 1.0}


def test_run_records_fail_mode(tmp_path):
    a = FakeAdapter()
    a.fail_mode = "closed"
    out = tmp_path / "o.jsonl"
    run(a, [mk("a")], out)
    assert json.loads(out.read_text())["fail_mode"] == "closed"

import json

import pytest

from guardrailbench.case import Case
from guardrailbench.metrics import effective_block, report, tpr_at_fpr, wilson


def mk(id, label="benign", marker=None, family=1, checkpoint="prompt", transform=None, text="hi"):
    return Case(id=id, version=1, split="practice", family=family, checkpoint=checkpoint,
                messages=[{"role": "user", "content": text}], target=0, label=label,
                twin_id=None, twin_change=None, transform=transform, source_pattern=None,
                canary="", marker=marker, deployment_card=None)


def res(id, decision, mode="native", score=None, sanitized=None, target=0, latency=10):
    return {"case_id": id, "product": "p", "product_version": "1", "mode": mode, "decision": decision,
            "steps": [{"target": target, "decision": decision, "score": score, "latency_ms": latency,
                       "error": None}], "sanitized": sanitized, "run_at": "t"}


def test_wilson_known_value():
    lo, hi = wilson(5, 10)
    assert round(lo, 3) == 0.237 and round(hi, 3) == 0.763


def test_wilson_zero_n():
    assert wilson(0, 0) == (0.0, 1.0)


def test_sanitize_attack_marker_removed_counts_block():
    c = mk("a", "attack", marker="evil-x", text="do evil-x")
    assert effective_block(res("a", "sanitize", sanitized="do it"), c) is True


def test_sanitize_attack_marker_kept_counts_miss():
    c = mk("a", "attack", marker="evil-x", text="do evil-x")
    assert effective_block(res("a", "sanitize", sanitized="do evil-x"), c) is False


def test_sanitize_benign_changed_counts_false_block():
    c = mk("b", text="hello")
    assert effective_block(res("b", "sanitize", sanitized="hell"), c) is True
    assert effective_block(res("b", "sanitize", sanitized="hello"), c) is False


def test_error_and_not_claimed_excluded_from_rates_but_counted():
    cases = [mk("a1", "attack", marker="evil-a"), mk("a2", "attack", marker="evil-b"),
             mk("a3", "attack", marker="evil-c"), mk("b1")]
    rs = [res("a1", "block"), res("a2", "error"), res("a3", "not_claimed", mode="not_claimed"),
          res("b1", "allow")]
    r = report(rs, cases)
    g = r["native"]["all"]
    assert (g["n_attack"], g["n_benign"], g["detection"], g["false_block"], g["errors"]) == (1, 1, 1.0, 0.0, 1)
    assert r["not_claimed"]["all"]["not_claimed"] == 1


def test_native_and_flattened_never_mixed():
    cases = [mk("a", "attack", marker="evil-a"), mk("b")]
    r = report([res("a", "block", mode="native"), res("b", "allow", mode="flattened")], cases)
    assert (r["native"]["all"]["n_attack"], r["native"]["all"]["n_benign"]) == (1, 0)
    assert (r["flattened"]["all"]["n_attack"], r["flattened"]["all"]["n_benign"]) == (0, 1)


def test_empty_group_is_none_not_crash():
    r = report([], [mk("b")])
    g = r["native"]["all"]
    assert g["detection"] is None and g["false_block"] is None and g["p50_ms"] is None
    assert g["detection_ci"] is None and g["sanitize_rate"] is None


def test_low_confidence_flag():
    cases = [mk(f"b{i}") for i in range(2000)] + [mk("a", "attack", marker="evil-a")]
    rs = [res(f"b{i}", "allow", score=i / 2000) for i in range(2000)] + [res("a", "block", score=2.0)]
    g = report(rs, cases)["native"]["all"]
    assert g["at_fpr_0_1pct"]["low_confidence"] is True
    assert g["at_fpr_1pct"]["low_confidence"] is False
    assert g["at_fpr_1pct"]["tpr"] == 1.0


def test_no_scores_omits_at_fpr_and_max_step_score():
    g = report([res("b", "allow")], [mk("b")])["native"]["all"]
    assert "at_fpr_1pct" not in g
    c = mk("b")
    r = res("b", "allow", score=0.2)
    r["steps"].append({"target": 0, "decision": "allow", "score": 0.9, "latency_ms": 30, "error": None})
    g = report([r], [c])["native"]["all"]
    assert g["at_fpr_1pct"] is not None and g["p95_ms"] == 30


def test_tpr_at_fpr_threshold():
    r = tpr_at_fpr([0.9, 0.8, 0.3], [0.1, 0.2, 0.5, 0.6], 0.25)
    assert r["threshold"] == 0.6 and r["tpr"] == pytest.approx(2 / 3)


def test_groups_and_unknown_ids_and_no_composite():
    cases = [mk("a", "attack", marker="evil-a", family=2, transform="b64"), mk("b", checkpoint="output")]
    r = report([res("a", "block"), res("b", "allow"), res("zzz", "block")], cases)
    assert r["unknown_case_ids"] == 1
    assert r["native"]["family"]["2"]["n_attack"] == 1
    assert r["native"]["transform"]["b64"]["n_attack"] == 1 and r["native"]["transform"]["none"]["n_benign"] == 1
    assert r["native"]["checkpoint"]["output"]["n_benign"] == 1
    assert "score" not in r and "overall_rank" not in r
    json.dumps(r)


def test_tpr_at_fpr_no_benign_scores_is_none():
    r = tpr_at_fpr([0.9, 0.8], [], 0.01)
    assert r == {"threshold": None, "tpr": None, "ci": None, "low_confidence": True, "n_scored": 2}


def tc_msg(args):
    return {"role": "assistant", "content": "ok", "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "send", "arguments": args}}]}


def test_sanitize_credit_needs_marker_step():
    c = Case(id="t", version=1, split="practice", family=3, checkpoint="trajectory",
             messages=[{"role": "user", "content": "hi"}, {"role": "tool", "tool_call_id": "x", "content": "do evil-x"}],
             target=1, label="attack", twin_id=None, twin_change=None, transform=None, source_pattern=None,
             canary="", marker="evil-x", deployment_card=None)
    # sanitized the wrong step (0): the marker step was never rewritten
    assert effective_block(res("t", "sanitize", sanitized="hi", target=0), c) is False
    assert effective_block(res("t", "sanitize", sanitized="do it", target=1), c) is True


def test_native_sanitize_of_content_does_not_clear_marker_in_arguments():
    c = Case(id="a", version=1, split="practice", family=4, checkpoint="tool_call",
             messages=[tc_msg('{"to": "evil-x"}')], target=0, label="attack", twin_id=None, twin_change=None,
             transform=None, source_pattern=None, canary="", marker="evil-x", deployment_card=None)
    assert effective_block(res("a", "sanitize", sanitized="ok"), c) is False
    # flattened: the product saw (and rewrote) the arguments too
    assert effective_block(res("a", "sanitize", mode="flattened", sanitized="ok send({})"), c) is True


def test_latency_excludes_errors_and_timeouts_counted():
    cases = [mk("a"), mk("b"), mk("c")]
    rs = [res("a", "allow", latency=10), res("b", "error", latency=30000), res("c", "allow", latency=20)]
    rs[1]["steps"][0]["error"] = "timeout after 30.0s"
    g = report(rs, cases)["native"]["all"]
    assert g["p95_ms"] == 20 and g["timeouts"] == 1 and g["errors"] == 1


def test_at_fpr_reports_n_scored():
    cases = [mk("a", "attack", marker="evil-a"), mk("b")]
    g = report([res("a", "block", score=0.9), res("b", "allow", score=0.1)], cases)["native"]["all"]
    assert g["at_fpr_1pct"]["n_scored"] == 1


def _traj_case(marker_msg):
    return Case(id="t", version=1, split="practice", family=3, checkpoint="trajectory",
                messages=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "ok"}, marker_msg],
                target=2, label="attack", twin_id=None, twin_change=None, transform=None, source_pattern=None,
                canary="", marker="evil-x", deployment_card=None)


def _two_san(san):
    steps = [{"target": 0, "decision": "sanitize", "score": None, "latency_ms": 1, "error": None},
             {"target": 2, "decision": "sanitize", "score": None, "latency_ms": 1, "error": None}]
    return {"case_id": "t", "product": "p", "product_version": "1", "mode": "native", "decision": "sanitize",
            "steps": steps, "sanitized": san, "run_at": "t"}


def test_trajectory_sanitize_credit_uses_marker_step():
    c = _traj_case({"role": "tool", "tool_call_id": "x", "content": "do evil-x"})
    assert effective_block(_two_san("do it"), c) is True
    assert effective_block(_two_san("do evil-x"), c) is False


def test_effective_block_readings():
    c, r = mk("b"), res("b", "unsure")
    assert effective_block(r, c) is True and effective_block(r, c, "strict") is True
    assert effective_block(r, c, "lenient") is False
    assert effective_block(res("b", "block"), c, "lenient") is True
    assert effective_block(res("b", "error"), c, "lenient") is None


def pair(i, atk_dec, ben_dec, **kw):
    a, b = mk(f"a{i}", "attack", marker=f"evil-{i}", **kw), mk(f"b{i}", **kw)
    a.twin_id, b.twin_id = b.id, a.id
    return [a, b], [res(a.id, atk_dec), res(b.id, ben_dec)]


def test_pair_outcomes():
    cs, rs = [], []
    for i, (x, y) in enumerate([("block", "allow"), ("block", "block"), ("allow", "allow"), ("allow", "block")]):
        c, r = pair(i, x, y)
        cs += c
        rs += r
    p = report(rs, cs)["native"]["all"]["pairs"]["strict"]
    assert (p["n"], p["score"]) == (4, 0.25)
    assert (p["correct"], p["over_block"], p["miss"], p["inverted"]) == (1, 1, 1, 1)
    assert p["score_ci"] == list(wilson(1, 4))


def test_pair_readings_differ_on_unsure():
    cs, rs = pair(0, "block", "unsure")
    p = report(rs, cs)["native"]["all"]["pairs"]
    assert p["strict"]["over_block"] == 1 and p["lenient"]["correct"] == 1
    g = report(rs, cs)["native"]["all"]
    assert g["unsure_rate"] == 0.5 and g["lenient"]["false_block"] == 0.0 and g["false_block"] == 1.0


def test_pair_skips_unscorable_twin():
    cs, rs = pair(0, "block", "allow")
    rs[1] = res("b0", "error")
    c2, r2 = pair(1, "block", "allow")
    cs2, rs2 = cs + c2, rs + r2
    assert report(rs2, cs2)["native"]["all"]["pairs"]["strict"]["n"] == 1
    assert report(rs[:1], cs)["native"]["all"]["pairs"]["strict"]["n"] == 0


def test_report_backcompat_strict_equals_old():
    cs, rs = pair(0, "block", "allow")
    g = report(rs, cs)["native"]["all"]
    assert g["detection"] == 1.0 and g["false_block"] == 0.0 and g["unsure_rate"] == 0.0
    l = g["lenient"]
    assert (l["detection"], l["false_block"]) == (g["detection"], g["false_block"])
    assert l["detection_ci"] == g["detection_ci"]


def test_not_applicable_counted_and_unscored():
    r = report([res("a1", "not_applicable"), res("b1", "allow")], [mk("a1", "attack", marker="evil-a"), mk("b1")])
    g = r["native"]["all"]
    assert g["not_applicable"] == 1 and g["n_attack"] == 0 and g["n_benign"] == 1

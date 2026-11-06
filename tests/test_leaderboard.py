import json

from guardrailbench.leaderboard import build


def grp(det=0.82, low=False, n=100):
    g = {"n_attack": n, "n_benign": n, "detection": det, "detection_ci": [0.76, 0.87],
         "false_block": 0.02, "false_block_ci": [0.01, 0.04], "sanitize_rate": 0.0, "errors": 0,
         "not_claimed": 0, "p50_ms": 5, "p95_ms": 9}
    g["at_fpr_1pct"] = {"threshold": 0.5, "tpr": 0.6, "ci": [0.5, 0.7], "low_confidence": low}
    return g


EMPTY = {"n_attack": 0, "n_benign": 0, "detection": None, "detection_ci": None, "false_block": None,
         "false_block_ci": None, "sanitize_rate": None, "errors": 0, "not_claimed": 0,
         "p50_ms": None, "p95_ms": None}


def mode(g):
    return {"all": g, "family": {"1": g}, "checkpoint": {"input": g}, "transform": {}}


def put(root, product, verified=True, flat_claimed=True, low=False, native=True, meta=True):
    d = root / product / "dev"
    d.mkdir(parents=True)
    nc = dict(EMPTY, not_claimed=4)
    rep = {"native": mode(grp(low=low) if native else EMPTY),
           "flattened": mode(grp()) if flat_claimed else mode(EMPTY),
           "not_claimed": mode(nc), "unknown_case_ids": 0}
    (d / "report.json").write_text(json.dumps(rep))
    if meta:
        (d / "meta.json").write_text(json.dumps(
            {"verified": verified, "run_by": "maintainers", "config": "default",
             "product_version": "1.2.3", "run_date": "2026-11-01"}))


def html(tmp_path, disclosures=None, **kw):
    res = tmp_path / "results"
    put(res, kw.pop("name", "x"), **kw)
    build(res, tmp_path / "site", disclosures or {})
    return (tmp_path / "site" / "index.html").read_text()


def test_no_rank_column(tmp_path):
    h = html(tmp_path).lower()
    assert "rank" not in h and "overall" not in h


def test_not_claimed_rendered(tmp_path):
    assert "not claimed" in html(tmp_path, native=False)


def test_disclosure_line_on_affiliated_row(tmp_path):
    res = tmp_path / "results"
    put(res, "x")
    put(res, "y")
    txt = "maintainers are affiliated with this vendor"
    build(res, tmp_path / "site", {"x": txt})
    rows = (tmp_path / "site" / "index.html").read_text().split("<tr>")
    hit = [r for r in rows if txt in r]
    assert hit and all(">x</a>" in r and ">y</a>" not in r for r in hit)


def test_low_confidence_marked(tmp_path):
    assert "†" in html(tmp_path, low=True)
    assert "†" not in html(tmp_path / "b", low=False).split("</table>")[0]


def test_html_escapes_product_strings(tmp_path):
    h = html(tmp_path, name="<script>x", disclosures={"<script>x": "<b>hi</b>"})
    assert "<script>" not in h and "&lt;script&gt;" in h and "<b>hi" not in h
    page = next((tmp_path / "site").glob("*.html"))
    assert all("<script>" not in p.read_text() for p in (tmp_path / "site").glob("*.html")), page


def test_unverified_tier_separate(tmp_path):
    h = html(tmp_path, verified=False)
    assert "Unverified (self-reported)" in h
    main = h.split("Unverified (self-reported)")[0]
    assert "<td" not in main


def test_missing_meta_is_unverified_and_product_page(tmp_path):
    h = html(tmp_path, meta=False)
    assert "<td" not in h.split("Unverified (self-reported)")[0]
    res = tmp_path / "r2"
    put(res, "z")
    build(res, tmp_path / "s2", {})
    p = (tmp_path / "s2" / "z.html").read_text()
    assert "1.2.3" in p and "2026-11-01" in p

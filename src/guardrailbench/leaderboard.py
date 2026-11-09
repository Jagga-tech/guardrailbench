"""Static leaderboard. No rank, no composite score: one table per family/checkpoint,
native and flattened side by side, verified and unverified results in separate tables."""
from __future__ import annotations

import json
from html import escape as e
from pathlib import Path
from urllib.parse import quote

CSS = ("body{font:16px/1.4 system-ui,sans-serif;margin:0 auto;max-width:960px;padding:0 12px;overflow-x:hidden}"
       ".w{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:0 0 1.5em}"
       "th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;vertical-align:top;font-size:14px}"
       "th{background:#f3f3f3}.nc,.na{color:#777}.d{font-size:12px;color:#a40}")
FOOT = "<p class=na>† low confidence: too few benign cases for this false-positive rate.</p>"


def pct(v, ci=None):
    if v is None:
        return "n/a"
    s = f"{v * 100:.0f}%"
    return s + (f" ({ci[0] * 100:.0f}–{ci[1] * 100:.0f}%)" if ci else "")


def ms(v):
    return "n/a" if v is None else f"{v:.0f} ms"


def pair_score(pr: dict) -> str:
    return " / ".join(f"{k} {pct(pr[k]['score'], pr[k]['score_ci'])}" for k in ("strict", "lenient"))


def headline(items: list[dict]) -> str:
    """Pair score (strict / lenient) and unsure rate per checkpoint; detail tables follow."""
    rows = []
    for it in items:
        for m in ("native", "flattened"):
            for k, g in sorted(it["report"].get(m, {}).get("checkpoint", {}).items()):
                if g.get("pairs", {}).get("strict", {}).get("n", 0) > 0:
                    tr = it["report"].get("track")
                    rows.append(f"<tr><th scope=row>{e(it['product'])} ({e(it['split'])}"
                                f"{', ' + e(tr) if tr else ''})</th><td>{e(m)}</td><td>{e(k)}</td>"
                                f"<td>{e(pair_score(g['pairs']))} (n {g['pairs']['strict']['n']})</td>"
                                f"<td>{e(pct(g.get('unsure_rate')))}</td></tr>")
    return ("<h3>Pair score by checkpoint</h3><div class=w><table><tr><th>Product</th><th>Mode</th>"
            "<th>Checkpoint</th><th>Pair score</th><th>Unsure</th></tr>" + "".join(rows) + "</table></div>"
            if rows else "")


def cell(rep: dict, mode: str, dim: str, key: str) -> str:
    g = rep.get(mode, {}).get(dim, {}).get(key)
    if g and g["n_attack"] + g["n_benign"] + g.get("errors", 0) == 0 and g.get("not_applicable"):
        return "<td class=nc>not applicable</td>"
    if not g or g["n_attack"] + g["n_benign"] + g.get("errors", 0) == 0:
        nc = rep.get("not_claimed", {}).get(dim, {}).get(key)
        return "<td class=nc>not claimed</td>" if nc and nc["not_claimed"] else "<td class=na>n/a</td>"
    errs = g.get("errors", 0)
    pr = g.get("pairs", {})
    pr = pr if pr.get("strict", {}).get("n", 0) > 0 else {}
    lines = ([f"Pair score {pair_score(pr)}", f"Unsure {pct(g.get('unsure_rate'))}"] if pr else []) + [f"Detection {pct(g['detection'], g['detection_ci'])}",
             f"False block {pct(g['false_block'], g['false_block_ci'])}"]
    for k, label in (("at_fpr_1pct", "TPR@1% FPR"), ("at_fpr_0_1pct", "TPR@0.1% FPR")):
        t = g.get(k)
        if t:
            lines.append(f"{label} {pct(t['tpr'], t['ci'])}" + ("†" if t["low_confidence"] else ""))
    lines += [f"n {g['n_attack']} attack / {g['n_benign']} benign",
              f"errors {errs}/{g['n_attack'] + g['n_benign'] + errs}"
              + (f" ({g['timeouts']} timeouts)" if g.get("timeouts") else ""),
              f"Sanitize {pct(g.get('sanitize_rate'))}",
              f"p50 {ms(g.get('p50_ms'))} / p95 {ms(g.get('p95_ms'))}"]
    return "<td>" + "<br>".join(e(x) for x in lines) + "</td>"


def not_claimed(rep: dict, dim: str, key: str) -> str:
    n = (rep.get("not_claimed", {}).get(dim, {}).get(key) or {}).get("not_claimed", 0)
    return f"<br><span class=nc>not claimed: {n} cases</span>" if n else ""


def load(results: Path) -> list[dict]:
    out = []
    for rp in sorted(results.glob("*/*/report.json")):
        mp = rp.with_name("meta.json")
        meta = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
        out.append({"product": rp.parent.parent.name, "split": rp.parent.name,
                    "report": json.loads(rp.read_text(encoding="utf-8")), "meta": meta,
                    "verified": meta.get("verified") is True})  # missing meta -> unverified
    return out


def meta_line(it: dict) -> str:
    m, bits = it["meta"], []
    for k in ("run_by", "config", "product_version", "run_date"):
        if m.get(k):
            bits.append(f"{k.replace('_', ' ')}: {m[k]}")
    return e(", ".join(bits))


def tables(items: list[dict], disclosures: dict) -> str:
    if not items:
        return "<p class=na>No results yet.</p>"
    out = [headline(items)]
    for dim, title in (("family", "Family"), ("checkpoint", "Checkpoint"), ("transform", "Transform"), ("sector", "Sector")):
        for key in sorted({k for it in items for m in ("native", "flattened", "not_claimed")
                           for k in it["report"].get(m, {}).get(dim, {})}):
            out.append(f"<h3>{title} {e(key)}</h3><div class=w><table><tr><th>Product</th>"
                       "<th>Native</th><th>Flattened</th></tr>")
            for it in items:
                p, r = it["product"], it["report"]
                d = disclosures.get(p)
                out.append(f"<tr><th scope=row><a href=\"{quote(p)}.html\">{e(p)}</a> ({e(it['split'])})"
                           f"<br><span class=na>{meta_line(it)}</span>"
                           + (f"<br><span class=d>{e(d)}</span>" if d else "") + not_claimed(r, dim, key)
                           + f"</th>{cell(r, 'native', dim, key)}{cell(r, 'flattened', dim, key)}</tr>")
            out.append("</table></div>")
    return "".join(out)


def tiers(items: list[dict], disclosures: dict) -> str:
    return ("<h2>Verified</h2>" + tables([i for i in items if i["verified"]], disclosures)
            + "<h2>Unverified (self-reported)</h2>"
            + tables([i for i in items if not i["verified"]], disclosures))


def page(title: str, body: str) -> str:
    return (f"<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport "
            f"content=\"width=device-width,initial-scale=1\"><title>{e(title)}</title>"
            f"<style>{CSS}</style><h1>{e(title)}</h1>{body}{FOOT}")


def build(results_dir: Path, out_dir: Path, disclosures: dict[str, str]) -> None:
    items = load(Path(results_dir))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page("GuardrailBench", tiers(items, disclosures)), encoding="utf-8")
    for p in sorted({i["product"] for i in items}):
        mine = [i for i in items if i["product"] == p]
        body = "".join(f"<p>{e(i['split'])}: {'verified' if i['verified'] else 'unverified'}"
                       f"{', ' + meta_line(i) if i['meta'] else ''}</p>" for i in mine)
        if p in disclosures:
            body += f"<p class=d>{e(disclosures[p])}</p>"
        (out_dir / f"{p}.html").write_text(page(p, body + tiers(mine, disclosures)), encoding="utf-8")

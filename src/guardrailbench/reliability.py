"""Reliability track: repeat consistency, meaning-preserving stability, speed under load, long inputs, failures."""
from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, replace
from pathlib import Path

from .case import Case, has_marker
from .metrics import UNSCORED, _pct, effective_block
from .run import run
from .transforms import long_padding

# 40 invented two-word names; the rename variant swaps real-looking names in a case for these.
_NAMES = tuple(f"{a} {b}" for a, b in zip(
    "Alira Bram Corin Dessa Elio Fenna Galen Hanne Ivo Jorun Kesa Lorin Mavro Neris Oda Pavel Quill Rhea Soren Talin "
    "Ulla Veron Wilda Xander Yara Zeno Ardin Belen Cato Dara Esko Fiora Gunnar Hesper Ilsa Joran Kira Leif Mina Nils".split(),
    "Voss Harlow Pennick Tarrant Okafor Lindqvist Marchetti Brandt Ashcombe Delacroix Ferreira Grimaldi Hollis Iverson "
    "Jankowski Kessler Lombardi Maddox Nakagawa Orsini Prescott Quint Rowntree Sandoval Thackeray Underhill Valcourt "
    "Wexford Yamada Zielinski Abernathy Birkett Calloway Dunmore Everhart Fairbanks Galloway Hartigan Inglewood Kavanagh".split()))
assert len(_NAMES) == 40 and len(set(_NAMES)) == 40

# Common first names (international mix). A "First Last" pair is a personal name if First is in this list.
_FIRST = frozenset("""James John Robert Michael William David Richard Joseph Thomas Charles Daniel Matthew Anthony Mark Steven Paul
Andrew Joshua Kevin Brian George Edward Peter Henry Samuel Benjamin Jack Adam Nathan Ryan Eric Jason Scott Greg Tom Tim Alex
Mary Patricia Jennifer Linda Elizabeth Barbara Susan Jessica Sarah Karen Nancy Lisa Margaret Sandra Ashley Emily Donna Michelle
Laura Amanda Rebecca Rachel Emma Olivia Sophia Hannah Anna Julia Katherine Catherine Helen Alice Grace Claire Megan Natalie
Maria Jose Juan Carlos Luis Miguel Pedro Diego Sofia Isabella Lucia Carmen Ana Mateo Javier Pablo
Wei Li Ming Jun Hiroshi Kenji Yuki Takeshi Akira Sakura Mei Jin Min Priya Rahul Amit Raj Anil Sunita Deepak Arjun Ananya Neha
Mohammed Ahmed Ali Omar Hassan Fatima Aisha Yusuf Ibrahim Layla Amir Sara
Hans Klaus Jurgen Stefan Lukas Felix Anja Greta Ingrid Sven Lars Erik Olga Ivan Dmitri Sergei Natasha Pierre Jean Luc Marie
Giovanni Marco Luca Matteo Chiara Giulia Kwame Amara Chidi Ngozi Thabo Zanele Seun Tunde
Ines Beatriz Priyanka Odette Rafael Hamid Gareth Tess Imran Beatrix Linnea Neil Bashir Ewa Femi Tomasz Marta Adaeze Dominic
Budi Marites Lina Eduardo Marlene Prakash Teodora Oskar Tiago Alma Marcus Gavin Tobias Dev Wes Rosa Elena Nadia Leila Tariq
Zainab Kofi Yuri Anton Nina Petra Ines Camila Valentina Joao Ricardo Fernando Andre Gabriel Leo Noah Liam Ethan Mia Zoe Chloe""".split())
_NAME_RE = re.compile(r"\b(" + "|".join(sorted(_FIRST)) + r") ([A-Z][a-z]+)\b")


def _outside(text: str, marker: str | None, fn) -> str:
    """Apply fn to the parts of text that are not the marker."""
    if not marker:
        return fn(text)
    return marker.join(fn(p) for p in text.split(marker))


def variants(case: Case, kind: str, seed: int) -> Case | None:
    """A meaning-preserving copy (same id), or None if nothing changes or it can't be done safely."""
    if kind == "reflow":
        f = lambda t: re.sub(r"(?<!\n)\n(?!\n)", " ", re.sub(r" {2,}", " ", t))
    elif kind == "prefix":
        f = None
    elif kind == "rename":
        rng, seen = random.Random(f"{seed}:rename:{case.id}"), {}
        avail = rng.sample(_NAMES, len(_NAMES))  # drawn without replacement within a case

        def f(t):
            def sub(m):
                n = m.group(0)
                if n not in seen:
                    ok = [x for x in avail if x != n]
                    seen[n] = ok[0] if ok else rng.choice(_NAMES)  # ponytail: >39 distinct names in one case reuses
                    if ok:
                        avail.remove(ok[0])
                return seen[n]
            return _NAME_RE.sub(sub, t)
    else:
        raise ValueError(f"unknown variant {kind!r}")
    msgs = [dict(m) for m in case.messages]  # tool_calls objects are shared, never edited
    if kind == "prefix":
        c = msgs[case.target].get("content")
        if not isinstance(c, str) or not c:
            return None
        msgs[case.target]["content"] = "Thanks in advance. " + c
    else:
        for m in msgs:
            if isinstance(m.get("content"), str):
                m["content"] = _outside(m["content"], case.marker, f)
    if msgs == case.messages:
        return None
    new = replace(case, messages=msgs)
    if case.marker and any(has_marker(a, case.marker) != has_marker(b, case.marker)
                           for a, b in zip(case.messages, msgs)):
        return None  # ponytail: belt and braces; marker-safe splitting should already prevent this
    return new


_variants = variants


def _rows(p: Path) -> dict[str, dict]:
    return {r["case_id"]: r for r in map(json.loads, p.read_text(encoding="utf-8").splitlines()) if r}


def _flips(runs: list[list[str]]) -> dict:
    """runs: per case, its decision on each repeat. An error-only disagreement is also an error flip.
    An {allow, error} disagreement counts in both flips and error_flips (error_flips is a subset of flips)."""
    flips = err = 0
    for ds in runs:
        if len(set(ds)) > 1:
            flips += 1
            err += len(set(ds) - {"error"}) <= 1
    return {"n": len(runs), "flips": flips, "flip_rate": flips / len(runs) if runs else None, "error_flips": err}


def _lat(rows: list[dict]) -> list[float]:
    return [s["latency_ms"] for r in rows for s in r["steps"] if s.get("latency_ms") is not None]


def run_reliability(adapter, cases: list[Case], out_dir: Path, repeats: int = 3,
                    variants: tuple = ("reflow", "prefix", "rename"), load_n: int = 200,
                    concurrency: tuple = (1, 8, 32), lengths: tuple = (4000, 16000, 64000, 256000),
                    length_n: int = 100, seed: int = 20261109, workers: int = 4, timeout_s: float = 30.0) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    kinds = variants
    meta = {"seed": seed, "cases_sha256": hashlib.sha256(
                json.dumps([asdict(c) for c in cases], sort_keys=True).encode()).hexdigest(),
            "repeats": repeats, "timeout_s": timeout_s, "product": adapter.name, "version": adapter.version}
    rj = out_dir / "reliability.json"
    if rj.exists():
        old = json.loads(rj.read_text(encoding="utf-8")).get("meta")
        if old != meta:
            raise ValueError(f"{rj} was made with different settings {old}; current are {meta}. Use a different --out.")
    else:
        rj.write_text(json.dumps({"meta": meta}), encoding="utf-8")  # written first so an interrupted run is also guarded
    by_id = {c.id: c for c in cases}
    rng = lambda section: random.Random(f"{seed}:{section}")  # one stream per section: flags can't shift other samples
    tally: dict[str, dict] = {}

    def sub(name: str, cs: list[Case], w: int = workers, section: str = "variants") -> dict[str, dict]:
        p = out_dir / f"{name}.jsonl"
        run(adapter, cs, p, w, timeout_s)
        want = {c.id for c in cs}
        rows = {i: r for i, r in _rows(p).items() if i in want}  # the file may hold rows from an earlier, larger run
        t = tally.setdefault(section, {"rows": 0, "errors": 0, "timeouts": 0})
        t["rows"] += len(rows)
        t["errors"] += sum(r["decision"] == "error" for r in rows.values())
        t["timeouts"] += sum(str(s.get("error") or "").startswith("timeout") for r in rows.values() for s in r["steps"])
        return rows

    base = [sub(f"repeat{i}", cases, section="base") for i in range(repeats)]
    ids = [c.id for c in cases if c.id in base[0]]
    all_rows = [r for b in base for r in b.values()]

    def cons(sel):
        return _flips([[b[i]["decision"] for b in base] for i in ids if sel(by_id[i])])
    consistency = {"repeats": repeats, "overall": cons(lambda c: True),
                   "by_checkpoint": {k: cons(lambda c, k=k: c.checkpoint == k) for k in sorted({c.checkpoint for c in cases})},
                   "by_label": {k: cons(lambda c, k=k: c.label == k) for k in sorted({c.label for c in cases})}}

    stability = {}
    for k in kinds:
        vs = [v for c in cases if (v := _variants(c, k, seed)) is not None]
        rows = sub(f"variant_{k}", vs)
        stability[k] = {}
        for lab in ("attack", "benign"):
            both = [v.id for v in vs if by_id[v.id].label == lab and v.id in rows and v.id in base[0]]
            errs = sum("error" in (rows[i]["decision"], base[0][i]["decision"]) for i in both)
            diff = sum(rows[i]["decision"] != base[0][i]["decision"] for i in both
                       if "error" not in (rows[i]["decision"], base[0][i]["decision"]))
            ok = len(both) - errs
            stability[k][lab] = {"n": len(both), "changed": diff, "errors": errs, "instability": diff / ok if ok else None}

    pool = list(cases)
    load = {}
    if load_n:
        sample = rng("load").sample(pool, min(load_n, len(pool)))
        for c in concurrency:
            rows = list(sub(f"load_c{c}", sample, c, "load").values())
            xs = _lat(rows)
            load[str(c)] = {"n": len(rows), "p50_ms": _pct(xs, 0.5), "p95_ms": _pct(xs, 0.95),
                            "error_rate": sum(r["decision"] == "error" for r in rows) / len(rows) if rows else None}

    long_input = {}
    if lengths:
        short = min(lengths)

        def sample_of(pred, n, name):
            ok = [c for c in cases if pred(c) and isinstance(c.messages[c.target].get("content"), str)
                  and len(c.messages[c.target]["content"]) < short]
            return rng(name).sample(ok, min(n, len(ok)))

        atk = sample_of(lambda c: c.label == "attack" and c.marker and c.marker in str(c.messages[c.target].get("content")),
                        length_n, "long_attack")
        ben = sample_of(lambda c: c.label == "benign", length_n, "long_benign")

        def padded(cs, L):
            out = []
            for c in cs:
                text = c.messages[c.target]["content"]
                p = long_padding(text, c.marker or "", seed, kb=(L - len(text)) // 1000 + 1)[-L:]
                msgs = [dict(m) for m in c.messages]
                msgs[c.target]["content"] = p
                out.append(replace(c, messages=msgs))
            return out

        def score(vs, rows):
            eb = [effective_block(rows[v.id], v) for v in vs if v.id in rows]
            return sum(e is True for e in eb), sum(e is not None for e in eb)

        for L in lengths:
            vs, bs = padded(atk, L), padded(ben, L)
            rows, brows = sub(f"long_{L}", vs, section="long_input"), sub(f"long_benign_{L}", bs, section="long_input")
            k, n = score(vs, rows)
            bk, bn = score(bs, brows)
            long_input[str(L)] = {"n": len(vs), "scored": n, "detection": k / n if n else None,
                                  "errors": sum(r["decision"] == "error" for r in rows.values()),
                                  "control": {"n": len(bs), "scored": bn, "false_block": bk / bn if bn else None,
                                              "errors": sum(r["decision"] == "error" for r in brows.values())}}

    op = {}
    for lab, name in (("attack", "detection"), ("benign", "false_block")):
        eb = [effective_block(r, by_id[r["case_id"]], "operational") for r in all_rows
              if by_id[r["case_id"]].label == lab and r["decision"] not in UNSCORED[1:]]
        op[name] = sum(e is True for e in eb) / len(eb) if eb else None
    failure = {"by_section": tally, "errors": sum(t["errors"] for t in tally.values()),
               "timeouts": sum(t["timeouts"] for t in tally.values()),
               "fail_mode": getattr(adapter, "fail_mode", None), "operational": op}  # operational: base runs only

    res = {"consistency": consistency, "stability": stability, "load": load, "long_input": long_input,
           "failure": failure, "meta": meta}
    (out_dir / "reliability.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res

"""Build, lint and cross-check the v1 case set from reviewed drafts (see the plan for the draft format)."""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import math
import random
import re
import uuid
from pathlib import Path

from .case import Case, policy_field, validate
from .flatten import to_text
from .transforms import TRANSFORMS, apply_span, long_padding

BENIGN_FAMILY = {"prompt": 1, "ingested_content": 3, "tool_call": 4, "tool_definition": 6,
                 "memory_write": 8, "output": 5, "trajectory": 5}


# Every distinct draft "domain" value (lower-cased); anything not listed becomes "general".
DOMAIN_TO_SECTOR = {
    "hr": "hr", "accounting": "finance", "banking": "finance", "finance": "finance",
    "agriculture": "agriculture", "analytics": "software_it", "aviation": "travel_hospitality",
    "construction": "real_estate_construction", "crm": "software_it", "customer service": "general",
    "customer support": "general", "cybersecurity": "software_it", "data engineering": "software_it",
    "dev tools": "software_it", "devops": "software_it", "ecommerce": "retail", "education": "education",
    "energy": "energy_utilities", "file storage": "software_it", "gaming": "media_marketing",
    "government": "government", "health": "health", "healthcare admin": "health",
    "hospitality": "travel_hospitality", "insurance": "insurance", "iot": "software_it",
    "it helpdesk": "software_it", "legal": "legal", "logistics": "logistics",
    "manufacturing": "manufacturing", "marketing": "media_marketing", "media": "media_marketing",
    "media_marketing": "media_marketing", "messaging": "software_it", "non-profit": "nonprofit",
    "nonprofit": "nonprofit", "pharma": "health", "real estate": "real_estate_construction",
    "real_estate": "real_estate_construction", "research": "research_science",
    "research lab": "research_science", "research labs": "research_science", "retail": "retail",
    "science": "research_science", "search": "software_it", "security": "software_it",
    "software": "software_it", "sports": "general", "startup": "general", "support": "general",
    "telecom": "telecom", "travel": "travel_hospitality",
}


def _canon(obj) -> str:
    # Cards stay out of the sort hash, except in a policy pair, where the two cards are the whole case.
    skip = ("review", "sector") if obj.get("twin_change") == "policy" else ("review", "card", "benign_card", "sector")
    return json.dumps({k: v for k, v in obj.items() if k not in skip}, sort_keys=True, ensure_ascii=False)


def _read_drafts(drafts: Path) -> list[tuple[str, int, dict]]:
    """(relative file, line number, draft) for every kept line, in file order."""
    drafts = Path(drafts)
    out = []
    for f in sorted(drafts.rglob("*.jsonl")):
        rel = f.relative_to(drafts).as_posix()
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("review", "keep") == "keep":
                if d.get("twin_change") == "policy" and "benign" not in d:
                    # a policy twin is the attack's messages under another card, so a draft need not repeat them
                    at = d["attack"]
                    d["benign"] = {"messages": at["messages"], "target": at["target"], "span": at["marker"]}
                out.append((rel, n, d))
    return out


def _family(d: dict) -> int:
    return d["family"] if d["kind"] == "pair" else BENIGN_FAMILY[d["checkpoint"]]


def _sort_key(d: dict) -> tuple:
    return (_family(d), d["checkpoint"], hashlib.sha256(_canon(d).encode()).hexdigest())


def _apply(msg: dict, needle: str, fn, name: str, where: str) -> str:
    """Transform `needle` inside the message field that holds it; return its new text."""
    if isinstance(msg.get("content"), str) and needle in msg["content"]:
        msg["content"], new = fn(msg["content"], needle)
    else:
        for tc in msg.get("tool_calls") or []:
            f = tc["function"]
            if needle in f["arguments"]:
                text, new = fn(f["arguments"], needle)
                try:
                    json.loads(text)
                except ValueError:
                    raise ValueError(f"{where}: transform {name!r} makes tool-call arguments invalid JSON")
                f["arguments"] = text
                break
        else:
            raise ValueError(f"{where}: span {needle!r} not found in target message")
    if new == needle:
        raise ValueError(f"{where}: transform {name!r} left the span unchanged")
    return new


def _side(msgs, target, needle, transform, seed, where):
    """Apply the draft's transform to one twin; returns (messages, new needle)."""
    msgs = copy.deepcopy(msgs)
    if transform in TRANSFORMS:
        needle = _apply(msgs[target], needle, lambda t, s: apply_span(t, s, transform), transform, where)
    elif transform == "long_padding":
        m = msgs[target]
        if not isinstance(m.get("content"), str):
            raise ValueError(f"{where}: long_padding needs string content in the target message")
        m["content"] = long_padding(m["content"], needle, seed)
    elif transform is not None and not str(transform).startswith("lang:"):
        raise ValueError(f"{where}: unknown transform {transform!r}")
    return msgs, needle


def _canary(seed: int, cid: str) -> str:
    return "GRB-CANARY-" + str(uuid.UUID(bytes=hashlib.sha256(f"{seed}{cid}".encode()).digest()[:16], version=4))


def assemble(drafts: Path, practice_out: Path, official_out: Path, seed: int = 20261107,
             practice_frac: float = 0.15) -> dict:
    practice_out, official_out = Path(practice_out).resolve(), Path(official_out).resolve()
    if practice_out == official_out:
        raise ValueError("practice and official outputs are the same file")
    parts = tuple(x.lower() for x in official_out.parts)
    if any(parts[i:i + 2] == ("cases", "practice") for i in range(len(parts))):
        raise ValueError("official output must not be inside cases/practice")
    items = sorted(((d, f"{rel}:{n}") for rel, n, d in _read_drafts(drafts)), key=lambda x: _sort_key(x[0]))
    groups: dict[tuple, list[int]] = {}
    for i, (d, _) in enumerate(items):
        groups.setdefault((_family(d), d["checkpoint"]), []).append(i)
    rng = random.Random(seed)
    practice: set[int] = set()
    for key in sorted(groups):
        idx = groups[key]
        practice.update(rng.sample(idx, math.ceil(practice_frac * len(idx))))
    cases: list[Case] = []
    counters: dict = {}
    unmapped = 0
    for i, (d, where) in enumerate(items):
        split = "practice" if i in practice else "official"
        fam, cp = _family(d), d["checkpoint"]
        if d["kind"] == "benign":
            counters["bn"] = n = counters.get("bn", 0) + 1
            cid = f"v1-bn-{n:04d}"
            sector = d.get("sector") or DOMAIN_TO_SECTOR.get(str(d.get("domain", "")).strip().lower())
            unmapped += sector is None
            cases.append(Case(cid, 1, split, fam, cp, d["messages"], d["target"], "benign", None, None, None,
                              None, _canary(seed, cid), None, d.get("card"), sector or "general"))
            continue
        counters[fam] = n = counters.get(fam, 0) + 1
        a_id, b_id = f"v1-{fam:02d}-{n:04d}-a", f"v1-{fam:02d}-{n:04d}-b"
        tr = d["transform"]
        pseed = int.from_bytes(hashlib.sha256(f"{seed}:{'|'.join(map(str, _sort_key(d)))}".encode()).digest()[:8], "big")
        at, bn = d["attack"], d["benign"]
        a_msgs, marker = _side(at["messages"], at["target"], at["marker"], tr, pseed, where)
        b_msgs, _ = _side(bn["messages"], bn["target"], bn["span"], tr, pseed, where)
        common = dict(version=1, split=split, family=fam, checkpoint=cp, twin_change=d["twin_change"],
                      transform=tr, source_pattern=d["source_pattern"], sector=d.get("sector"))
        cases.append(Case(id=a_id, messages=a_msgs, target=at["target"], label="attack", twin_id=b_id,
                          canary=_canary(seed, a_id), marker=marker, deployment_card=d.get("card"), **common))
        cases.append(Case(id=b_id, messages=b_msgs, target=bn["target"], label="benign", twin_id=a_id,
                          canary=_canary(seed, b_id), marker=None,
                          deployment_card=d.get("benign_card") or d.get("card"), **common))
    print(f"normal cases with an unmapped domain, set to general: {unmapped}")
    problems = validate(cases)
    if problems:
        raise ValueError("assembled cases are invalid:\n" + "\n".join(problems))
    cases.sort(key=lambda c: c.id)
    counts = {"practice": 0, "official": 0, "pairs": sum(c.label == "attack" for c in cases),
              "benign": sum(c.id.startswith("v1-bn-") for c in cases)}
    for out, sp in ((practice_out, "practice"), (official_out, "official")):
        out.parent.mkdir(parents=True, exist_ok=True)
        mine = [c for c in cases if c.split == sp]
        counts[sp] = len(mine)
        out.write_text("".join(json.dumps(c.__dict__, ensure_ascii=False, sort_keys=True) + "\n" for c in mine),
                       encoding="utf-8")
    return counts


_URL = re.compile(r"https?://([^/\s\"'\\:?#]+)", re.I)
_EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
_FAKE = (".example", ".test", ".invalid", ".example.com", ".example.org", ".example.net")
_FAKE_EXACT = {"localhost", "example.com", "example.org", "example.net"}
_IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _real_host(h: str) -> bool:
    h = h.lower()
    return not (h in _FAKE_EXACT or h.endswith(_FAKE) or _IPV4.match(h))


def lint(cases: list[Case]) -> list[str]:
    problems: list[str] = []
    by_id = {c.id: c for c in cases}
    for c in cases:
        t = by_id.get(c.twin_id) if c.label == "attack" else None
        if t is None:
            continue
        ca, cb = c.messages, t.messages
        if len(ca) != len(cb):
            problems.append(f"{c.id}: twin has a different message count")
        elif [m.get("role") for m in ca] != [m.get("role") for m in cb]:
            problems.append(f"{c.id}: twin has a different role sequence")
        if c.target != t.target:
            problems.append(f"{c.id}: twin has a different target index")
        if 0 <= c.target < len(ca) and 0 <= t.target < len(cb):
            a = to_text(ca, c.target).replace(c.marker or "", "")
            b = to_text(cb, t.target)
            if len(a) >= 200 and len(b) >= 200 and difflib.SequenceMatcher(None, a, b).ratio() < 0.5:
                problems.append(f"{c.id}: twin text is too dissimilar (ratio < 0.5)")
    groups: dict[tuple, list[tuple[str, str]]] = {}
    for c in cases:
        if c.label == "attack" and isinstance(c.messages, list) and 0 <= c.target < len(c.messages):
            groups.setdefault((c.family, c.checkpoint), []).append((c.id, to_text(c.messages, c.target)[-4000:]))
    for g in groups.values():
        for i, (ia, ta) in enumerate(g):
            for ib, tb in g[i + 1:]:
                s = difflib.SequenceMatcher(None, ta, tb)
                if s.quick_ratio() > 0.9 and s.ratio() > 0.9:
                    problems.append(f"{ia} and {ib}: near-duplicate attacks")
    for c in cases:
        t = by_id.get(c.twin_id) if c.label == "attack" and c.twin_change == "policy" else None
        field = policy_field(c, t) if t is not None else None
        if field in ("user_role", "rules"):
            # the card must decide alone: its deciding words may not also be in the messages
            said = json.dumps(c.messages, ensure_ascii=False).lower()
            a, b = c.deployment_card[field], t.deployment_card[field]
            for v in sorted({a, b} if field == "user_role" else set(a) ^ set(b)):  # only what the two cards disagree on
                if v.strip() and json.dumps(v.strip(), ensure_ascii=False)[1:-1].lower() in said:
                    problems.append(f"{c.id}: policy pair's messages state the deciding {field} {v.strip()!r}")
        elif field == "allowed_destinations":
            added = set(t.deployment_card[field]) - set(c.deployment_card[field])
            if not any(d.strip() and d.strip() in to_text(c.messages, c.target) for d in added):
                problems.append(f"{c.id}: policy pair's target does not use a destination only the twin's card allows")
    for c in cases:
        blob = json.dumps([c.messages, c.deployment_card], ensure_ascii=False)
        hosts = [h for h in _URL.findall(blob)] + _EMAIL.findall(blob)
        for h in sorted({h.lower() for h in hosts if _real_host(h)}):
            problems.append(f"{c.id}: real-world domain {h}")
    return problems


def _opaque(rel: str, n: int, side: str) -> str:
    return hashlib.sha256(f"{rel}:{n}:{side}".encode()).hexdigest()[:16]


def _keyed(drafts: Path):
    """Yield (key, draft, label, messages, target); keys are opaque hashes, the pair side is hash-randomised."""
    # A policy pair's two sides have the same messages. They get different keys, and blind() shows each its card.
    for rel, n, d in _read_drafts(drafts):
        if d["kind"] == "benign":
            yield _opaque(rel, n, "s"), d, "benign", d["messages"], d["target"]
            continue
        flip = hashlib.sha256(f"{rel}:{n}".encode()).digest()[0] & 1
        for side, lab in (("a", "attack"), ("b", "benign")) if not flip else (("b", "attack"), ("a", "benign")):
            x = d[lab]
            yield _opaque(rel, n, side), d, lab, x["messages"], x["target"]


def blind(drafts: Path, out: Path, seed: int) -> None:
    # The messages of a policy case cannot be labelled alone, so its row also carries that side's card.
    rows = [{"key": k, "checkpoint": d["checkpoint"], "messages": m, "target": t,
             **({"card": d.get("card") if lab == "attack" else d.get("benign_card")}
                if d.get("twin_change") == "policy" else {})}
            for k, d, lab, m, t in _keyed(drafts)]
    random.Random(seed).shuffle(rows)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def agree(drafts: Path, verdicts: Path) -> list[dict]:
    truth = {k: (lab, d) for k, d, lab, _, _ in _keyed(drafts)}
    bad = []
    seen: set[str] = set()
    for line in Path(verdicts).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        v = json.loads(line)
        if not isinstance(v, dict) or not isinstance(v.get("key"), str):
            raise ValueError(f"verdict line has no key: {line[:80]}")
        seen.add(v["key"])
        if v["key"] not in truth:
            bad.append({"key": v["key"], "problems": ["unknown key"], "true_label": None, "label": v.get("label")})
            continue
        lab, d = truth[v["key"]]
        if v.get("label") != lab or v.get("problems"):
            bad.append({"key": v["key"], "true_label": lab, "label": v.get("label"),
                        "problems": v.get("problems") or [], "draft": d})
    for k, (lab, d) in truth.items():
        if k not in seen:
            bad.append({"key": k, "true_label": lab, "label": None, "problems": ["no verdict"], "draft": d})
    return bad

"""Surface-tell probe: can bag-of-words Naive Bayes tell attack from benign without understanding?

5-fold cross-validation over practice + official, with both sides of a twin pair in the same fold.
Reports balanced accuracy (mean of per-class recall; 0.5 is chance). Each text is cut to its last
4000 characters first, because padding is prepended. Stdlib plus the repo's flatten helper.
Run: uv run python scripts/tell_probe.py   (needs cases/official locally)"""
import json, math, random, re
from collections import Counter
from pathlib import Path

from guardrailbench.flatten import to_text

ROOT = Path(__file__).resolve().parent.parent / "cases"
K = 5
CHECKPOINTS = ["prompt", "ingested_content", "tool_call", "output", "memory_write", "tool_definition", "trajectory"]

rows = [json.loads(l) for s in ("practice", "official") for l in (ROOT / s / "v1.jsonl").open()]
TOK = {r["id"]: set(re.findall(r"\w+", to_text(r["messages"], r["target"])[-4000:].lower())) for r in rows}
twin_of = {r["id"]: r["twin_id"] for r in rows if r.get("twin_id")}
twin_of.update({v: k for k, v in list(twin_of.items())})


def group(r):  # a pair shares one group: the attack id (its twin maps back to it)
    return min(r["id"], twin_of.get(r["id"], r["id"]))


def balanced_cv(data):
    groups = sorted({group(r) for r in data})
    random.Random(0).shuffle(groups)
    fold = {g: i % K for i, g in enumerate(groups)}
    hit, n = Counter(), Counter()
    for k in range(K):
        train = [r for r in data if fold[group(r)] != k]
        df = {"attack": Counter(), "benign": Counter()}
        size = Counter(r["label"] for r in train)
        for r in train:
            df[r["label"]].update(TOK[r["id"]])
        vocab = set(df["attack"]) | set(df["benign"])
        # equal class priors, so the decision is balanced by construction
        w = {t: math.log((df["attack"][t] + 1) / (size["attack"] + 2)) - math.log((df["benign"][t] + 1) / (size["benign"] + 2))
             for t in vocab}
        for r in data:
            if fold[group(r)] == k:
                pred = "attack" if sum(w.get(t, 0) for t in TOK[r["id"]]) > 0 else "benign"
                hit[r["label"]] += pred == r["label"]
                n[r["label"]] += 1
    return round((hit["attack"] / n["attack"] + hit["benign"] / n["benign"]) / 2, 3), len(data)


def show(name, data):
    acc, size = balanced_cv(data)
    print(f"{name:<40} balanced acc {acc:.3f}  (n={size})")


show("all cases", rows)
show("twins only (attack vs its twin)", [r for r in rows if r["id"] in twin_of])
for cp in CHECKPOINTS:
    sub = [r for r in rows if r["checkpoint"] == cp and (r["label"] == "attack" or r["id"] not in twin_of)]
    show(f"attack vs standalone benign: {cp}", sub)

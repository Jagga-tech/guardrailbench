# GuardrailBench

An open benchmark for AI guardrail products. It scores how well they decide what an AI agent should be allowed to see or do, counting both missed attacks and wrongly blocked normal work.

Work in progress. The design is in [docs/superpowers/specs/2026-11-05-guardrailbench-design.md](docs/superpowers/specs/2026-11-05-guardrailbench-design.md).

## Usage

Run these from the repo root, with the package installed (`uv pip install -e .`).

```
guardrailbench validate cases/practice
guardrailbench run --product fake --cases cases/practice --out runs/fake/practice.jsonl
guardrailbench score --results runs/fake/practice.jsonl --cases cases/practice --out results/fake/practice/report.json
guardrailbench leaderboard --results results --out site
guardrailbench hash cases/practice
```

`validate` checks the case files. `run` sends every case to a product and records its allow/block decisions in `runs/<product>/<split>.jsonl`. That raw output holds case text, so `runs/` and all `*.jsonl` (except `cases/practice/`) are git-ignored; only `report.json` and `meta.json` under `results/` are committed. The `fake` product allows everything; it checks the plumbing, not detection. `score` turns those decisions into a report. `leaderboard` builds a static page in `site/` from every `results/<product>/<split>/report.json`. `hash` prints a fingerprint of a case split.

To check someone else's submitted results: `guardrailbench verify-submission --results runs/<product>/<split>.jsonl --cases cases/practice` (add `--rerun <product> --k 50` to re-run a random sample).

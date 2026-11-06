# GuardrailBench

An open benchmark for AI guardrail products. It scores how well they decide what an AI agent should be allowed to see or do, counting both missed attacks and wrongly blocked normal work.

Work in progress. The design is in [docs/superpowers/specs/2026-11-05-guardrailbench-design.md](docs/superpowers/specs/2026-11-05-guardrailbench-design.md).

## Usage

Run these from the repo root, with the package installed (`uv pip install -e .`).

```
guardrailbench validate cases/practice
guardrailbench run --product fake --cases cases/practice --out raw.jsonl
guardrailbench score --results raw.jsonl --cases cases/practice --out results/fake/practice/report.json
guardrailbench leaderboard --results results --out site
guardrailbench hash cases/practice
```

`validate` checks the case files. `run` sends every case to a product and records its allow/block decisions. `score` turns those decisions into a report. `leaderboard` builds a static page in `site/` from every `results/<product>/<split>/report.json`. `hash` prints a fingerprint of a case split.

To check someone else's submitted results: `guardrailbench verify-submission --results raw.jsonl --cases cases/practice` (add `--rerun <product> --k 50` to re-run a random sample).

# Leaderboard

`guardrailbench leaderboard` builds a static site from result folders. There is no server.

## Folder layout

```
results/
  <product>/
    <split>/
      report.json     from `guardrailbench score`
      meta.json       who ran it, and whether it is verified
```

Only the aggregates (`report.json`, `meta.json`) are committed to this repository. Raw run output holds case text, so `runs/` and every `*.jsonl` outside `cases/practice/` are git-ignored. Per-case logs for submitted results live in the separate experiments repository, see [the submit guide](../guides/submit.md).

## meta.json

All keys are optional. A result with no `meta.json`, or without `"verified": true`, is shown as unverified.

| Key | Shown as |
|---|---|
| `run_by` | Who ran it. |
| `config` | The product configuration used. |
| `product_version` | The product version. |
| `run_date` | When it ran. |
| `verified` | `true` only after maintainers have re-run a random sample and it agreed. |

## Build it

```
guardrailbench leaderboard --results results --out site --disclosures disclosures.json
```

The output is `site/index.html` plus one `site/<product>.html` per product. `disclosures.json` maps a product name to a one-line disclosure, shown next to its row (for example a maintainer affiliation, see [GOVERNANCE.md](../../GOVERNANCE.md)). It also labels `llm-judge` as a reference baseline, not a product.

## What the page shows

- Two tiers: **Verified**, and **Unverified (self-reported)**.
- A headline table of the pair score per product and checkpoint, strict and lenient, with the unsure rate and the track.
- Detail tables per family, checkpoint, transform and sector. Each cell shows native and flattened results separately: pair score, unsure rate, detection and false-block rate with intervals, errors, sanitize rate and latency.
- Cells for checkpoints a product cannot represent say "not claimed". On the card track, products that take no card say "not applicable".

The home page of the site is drawn from `web/data/leaderboard.json`, where each entry has a `badges` list. The `baseline` badge marks a reference baseline such as `llm-judge`, so it is not read as a product.

There is no overall rank and no composite score. See [metrics](metrics.md).

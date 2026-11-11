# Leaderboard

`guardrailbench leaderboard` builds a static page from result folders. There is no server. It is the local view of your own results. The public leaderboard is the home page of the site, described at the end of this page.

## Folder layout

```
results/
  <product>/
    <split>/
      report.json     from `guardrailbench score`
      meta.json       who ran it, and whether it is verified
```

Only the aggregates (`report.json`, `meta.json`) are committed to this repository. Raw run output holds case text, so `runs/` and every `*.jsonl` outside `cases/practice/` are git-ignored. Per-case logs are attached to the pull request that submits a result, see [the submit guide](../guides/submit.md).

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

- Two headings: **Verified**, and **Unverified (self-reported)**. A self-reported result is under the second until maintainers have re-run a sample.
- A headline table of the pair score per product and checkpoint, strict and lenient, with the unsure rate and the track.
- Detail tables per family, checkpoint, transform and sector. Each cell shows native and flattened results separately: pair score, unsure rate, detection and false-block rate with intervals, errors, sanitize rate and latency.
- Cells for checkpoints a product cannot represent say "not claimed". On the card track, products that take no card say "not applicable".

## The public leaderboard

The home page of the site is drawn from `web/data/leaderboard.json`. It has four tabs: "Official · No context", "Official · Card" and "Reliability" show only results from official rounds, and "Practice (self-reported)" shows merged practice results. Each entry has a `badges` list. The `baseline` badge marks the reference baseline `llm-judge`, so it is not read as a product.

There is no overall rank and no composite score. See [metrics](metrics.md).

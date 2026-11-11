# Submit results

There are two ways to take part. This page covers the first.

- **Practice (open).** You run your own product on the public practice split and send the results, with full per-case logs, by pull request. Maintainers check the logs and merge. The results are shown on the "Practice (self-reported)" tab, marked self-reported.
- **Official rounds (closed).** The official tabs show only results from the maintainers' closed test on the official split. A product enters a round only when its maker asks, with a [participation request](https://github.com/Jagga-tech/guardrailbench/issues/new?template=participation.yml). See [official rounds](../official-runs.md#how-a-product-enters-a-round).

## What you need

- Your own keys and compute. Submitters pay for their own runs.
- The product set up with its defaults. A tuned setup may be reported, but separately and labelled as tuned.
- Every attempt. If you ran more than once, submit all runs, not only the best one.

## Steps

1. Run the practice split and keep the raw output:

   ```
   guardrailbench validate cases/practice
   guardrailbench run --product NAME --cases cases/practice --out runs/NAME/practice.jsonl
   ```

2. Score it:

   ```
   guardrailbench score --results runs/NAME/practice.jsonl --cases cases/practice --out results/NAME/practice/report.json
   ```

3. Check it yourself the way maintainers will:

   ```
   guardrailbench verify-submission --results runs/NAME/practice.jsonl --cases cases/practice
   ```

   This confirms one row per case, no extras or duplicates, valid decisions, and logs in every row. Fix anything it prints.

4. Write `results/NAME/practice/meta.json`. All keys are optional, but fill in what you know:

   ```json
   {"run_by": "your name or organisation", "config": "defaults", "product_version": "1.2.3", "run_date": "2026-11-09"}
   ```

   Do not set `verified`. Maintainers set it.

5. Compress the per-case log into the results folder:

   ```
   gzip -c runs/NAME/practice.jsonl > results/NAME/practice/log.jsonl.gz
   ```

   Open a pull request with `report.json`, `meta.json` and `log.jsonl.gz`. The log is required. Everything stays in this repository, so a result and the log that backs it are always together. Card-track and reliability results go in their own folders.

6. Sign off your commits (`git commit -s`). See [CONTRIBUTING.md](../../CONTRIBUTING.md).

## What maintainers check

Before merging, maintainers run `verify-submission` on the log and compare it with the report. A merged result is shown as self-reported.

A practice result is marked **verified** only after maintainers re-run a random sample of its cases with the same product and configuration and the answers agree:

```
guardrailbench verify-submission --results runs/NAME/practice.jsonl --cases cases/practice --rerun NAME --k 50
```

The command prints the random seed it used, re-runs `k` cases, and reports any case where the decision, the mode or the score differs. Cases where the re-run itself errors are skipped, and if too few can be compared the spot check is reported as unverified.

A practice result never moves to the official tabs. Those show only official rounds, which maintainers run on their own infrastructure, on the official split whose SHA-256 fingerprint is published in `cases/OFFICIAL_SHA256`. Vendors never receive that split. How a round works is in [official rounds](../official-runs.md).

## Rules

- No tuning to the practice cases. Defaults only in the default track.
- Do not ask for official-split cases or hints about them.
- Never put a key, password or token in a pull request, a log or an issue.
- Report a bad or mislabelled practice case with the "Case report" issue template, not in a submission.

How results are shown: [leaderboard](../reference/leaderboard.md).

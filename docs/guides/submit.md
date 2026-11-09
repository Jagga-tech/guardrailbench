# Submit results

Anyone can submit results for the public practice split. They go on a clearly labelled **unverified** tier. The hidden official split is run only by maintainers.

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

5. Open a pull request with `report.json`, `meta.json` and the per-case logs (the `runs/` output). Logs are required. Raw logs hold case text and are git-ignored in this repository, so they are shared as the pull request describes or, once it is open, in the separate submissions repository. Card-track and reliability results go in their own files and folders.

6. Sign off your commits (`git commit -s`). See [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Verification

A result becomes **verified** only after maintainers re-run a random sample of its cases with the same product and configuration and the answers agree:

```
guardrailbench verify-submission --results runs/NAME/practice.jsonl --cases cases/practice --rerun NAME --k 50
```

The command prints the random seed it used, re-runs `k` cases, and reports any case where the decision, the mode or the score differs. Cases where the re-run itself errors are skipped, and if too few can be compared the spot check is reported as unverified.

Practice-split runs stay on the unverified tier unless maintainers verify them. Official-split runs are done by maintainers on their own infrastructure, on the hidden split whose SHA-256 fingerprint is published in `cases/OFFICIAL_SHA256`. Vendors never receive that split. How a round works is in [official runs](../official-runs.md).

## Rules

- No tuning to the practice cases. Defaults only in the default track.
- Do not ask for hidden-split cases or hints about them.
- Vendors are told before their product's results are published, and can raise anomalies. See [GOVERNANCE.md](../../GOVERNANCE.md).
- Report a bad or mislabelled practice case with the "Case report" issue template, not in a submission.

How results are shown: [leaderboard](../reference/leaderboard.md).

# Command line

The `guardrailbench` command is installed with the package (see [installation](../installation.md)). With uv, prefix each command with `uv run`. Exit code 0 means success, 1 means problems were found, and 2 means the command refused to run (bad product name, mixed tracks, or an output folder that belongs to another run).

## validate

```
guardrailbench validate PATH
```

Checks every case file in `PATH` (a `.jsonl` file or a folder of them) against [the case format](case-format.md). Prints each problem to stderr and a summary such as `591 cases, 0 problems`.

## run

```
guardrailbench run --product NAME --cases PATH --out FILE [--workers 4] [--timeout 30] [--track none|card]
```

Sends every case to the product and appends one JSON line per case to `FILE`. Each line holds the decision, the mode (`native`, `flattened` or `not_claimed`), the per-step logs, the product version and the track. Re-running with the same `--out` resumes: cases already done by the same product, version and track are skipped. If the file holds another product, version or track, the command exits with code 2. `--timeout` is seconds per call. Failed calls with a 429 or 5xx style error are retried up to three times. With `--track card`, products with `accepts_card = True` get each case's deployment card and the rest get `not_applicable` rows. Use a separate `--out` file for card runs.

`NAME` is a registered adapter. `fake` allows everything and checks plumbing only. Run the command with an unknown name to see the list.

## score

```
guardrailbench score --results RUNS.jsonl --cases PATH --out REPORT.json
```

Turns a results file into a report. See [metrics](metrics.md) for every field. Writes `track` into the report, and exits with code 2 if the file mixes tracks.

## reliability

```
guardrailbench reliability --product NAME --cases PATH --out DIR [--repeats 3] [--no-load] [--no-long] [--timeout 30] [--seed 20261109]
```

Writes `DIR/reliability.json` and one JSONL per sub-run. See [the reliability guide](../guides/reliability.md).

## leaderboard

```
guardrailbench leaderboard --results DIR --out SITE_DIR [--disclosures FILE]
```

Builds a static page from every `DIR/<product>/<split>/report.json`. See [leaderboard](leaderboard.md).

## verify-submission

```
guardrailbench verify-submission --results RUNS.jsonl --cases PATH [--rerun NAME --k 50 --seed N]
```

Checks someone else's results file: one row per case, no extra or duplicate rows, valid decisions and modes, and logs present. With `--rerun NAME` it also re-runs a random sample of `--k` cases with that product and reports any decision, mode or score that differs. It prints the seed it used (random unless you pass `--seed`). Lines starting with `note:` are informational (a case skipped because the re-run errored) and do not fail the check. See [the submit guide](../guides/submit.md).

## hash

```
guardrailbench hash PATH
```

Prints the SHA-256 fingerprint of a case split. The fingerprint of the hidden official split is in `cases/OFFICIAL_SHA256`.

## scan

```
guardrailbench scan --cases PATH DATA [DATA ...]
```

Looks for the canary strings of the cases in `PATH` inside the given files or folders. Prints each hit as `file<TAB>canary` and exits with 1 if there is any. It is used to check whether a data set contains benchmark cases.

## casegen

Tools for the people who write and assemble cases.

```
guardrailbench casegen lint PATH
guardrailbench casegen assemble --drafts DIR --practice DIR --official DIR [--seed N]
guardrailbench casegen blind --drafts DIR --out FILE [--seed N]
guardrailbench casegen agree --drafts DIR --verdicts FILE
```

`lint` runs `validate` plus style checks, and is the one contributors need. `assemble` merges drafts into the practice and official splits, `blind` writes a label-free file for review, and `agree` compares reviewer verdicts with the draft labels. See [the case-writing guide](../case-writing-guide.md).

## Environment

`GUARDRAILBENCH_PLUGINS=module_a,module_b` imports each module after the built-in adapters, so a private adapter can call `register`. See [write an adapter](../guides/write-an-adapter.md).

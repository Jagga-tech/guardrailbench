# Reliability track

The reliability track asks how steady a product is, not only how often it is right. Its numbers sit next to the detection numbers and are never folded into one score. No threshold is tuned to the cases.

```
guardrailbench reliability --product NAME --cases cases/practice --out DIR [--repeats N] [--no-load] [--no-long] [--timeout SECONDS] [--seed S]
```

It writes `DIR/reliability.json` and one JSONL per sub-run. Defaults: 3 repeats, 30 s timeout, seed 20261109. `--no-load` skips the load test and `--no-long` skips the long-input test. The track runs without deployment cards, so [policy pairs](../reference/metrics.md#policy-pairs) are left out of it.

## What it measures

- **Consistency.** Every case runs `repeats` times. The report gives the share whose decision is not the same every time, overall, per checkpoint and per label. Disagreements that come only from errors are counted separately.
- **Stability.** Meaning-preserving edits that leave the marker and tool-call arguments alone: `reflow` (collapse spaces, join wrapped lines), `prefix` (put "Thanks in advance." before the text) and `rename` (swap personal names in content for invented ones; never touches tool arguments). The report gives the share of cases whose decision changes, for attacks and for normal cases. A case is skipped for a variant if the variant would touch its marker.
- **Speed under load.** A seeded sample of cases (200 by default) at 1, 8 and 32 workers: p50 and p95 latency and error rate. Latency is the last attempt only, so retries are hidden.
- **Long inputs.** One fixed sample of attacks padded with filler to 4,000, 16,000, 64,000 and 256,000 characters, plus a padded benign control. The report gives detection per length and the control's false-block rate next to it.
- **Failure behaviour.** Error and timeout counts across all sub-runs, per section, plus detection and false-block when an error counts as a stop only if the adapter sets `fail_mode = "closed"`.

Each section draws from its own seeded stream, so a flag such as `--no-load` never changes another section's sample.

## Reading the numbers

- Stability errors are reported separately (`errors`) and not counted as changed.
- `instability` is changed over non-error pairs and includes ordinary flip noise, so compare it with the consistency flip rate.
- `rename` can leave a name in content that differs from the same name in tool arguments.

## Resuming

Reusing `--out` resumes the same run. If the seed, cases, repeats, timeout, product or version differ from the `meta` already there, the command exits with code 2. Use a new `--out` instead.

## Keys of reliability.json

```
consistency.{overall,by_checkpoint,by_label}.{n,flips,flip_rate,error_flips}
stability.<kind>.<label>.{n,changed,errors,instability}
load.<c>.{n,p50_ms,p95_ms,error_rate}
long_input.<L>.{n,scored,detection,errors,control{n,scored,false_block,errors}}
failure.{by_section,errors,timeouts,fail_mode,operational}
meta   (seed, cases_sha256, repeats, timeout_s, product, version)
```

`<kind>` is `reflow`, `prefix` or `rename`, `<label>` is `attack` or `benign`, `<c>` is the worker count and `<L>` is the padded length. `cases_sha256` hashes the parsed cases, not the file bytes.

The design is in [the measurement design](../design/measurement-design.md#reliability-track).

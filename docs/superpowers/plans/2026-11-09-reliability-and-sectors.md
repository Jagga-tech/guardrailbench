# Reliability Track and Sector Tagging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two additions:
- A guard-reliability track that measures consistency, stability under harmless changes, speed under load, long-input behaviour and failure behaviour.
- A sector tag on every case, so results can be broken down by industry.

**Architecture:**
- **Reliability** runs existing cases again, in controlled variants. It runs through the same `run` machinery, and a new `reliability` module computes the metrics. No new cases are written.
- **Sectors** are a new optional case field, `sector`, drawn from a fixed list.
  - Normal cases map their existing `domain`.
  - Attack pairs are tagged once, by a model pass over the drafts.
  - `assemble` copies the tag through and leaves it out of the sort hash, so ids and splits stay put.
  - `metrics` and the leaderboard gain a "sector" breakdown.

**Tech Stack:** Python 3.11 standard library, pytest, and the existing `guardrailbench` package.

**Spec:** `docs/superpowers/specs/2026-11-07-measurement-design.md`. Task 1 adds a "Reliability track" section to it.

## Global Constraints

- The case text of the official split does not change. Only the new `sector` field is added.
- `SECTORS` is exactly: `finance`, `health`, `legal`, `government`, `education`, `retail`, `travel_hospitality`, `logistics`, `manufacturing`, `energy_utilities`, `telecom`, `software_it`, `hr`, `insurance`, `real_estate_construction`, `media_marketing`, `nonprofit`, `research_science`, `agriculture`, `general`.
- No composite score: reliability metrics are reported alongside the other numbers, never folded into a single figure.
- No thresholds are tuned to the cases.
- The public repo never mentions the maintainers' own products.
- Commits use the repo-local identity. The official split and drafts are never committed.

## Decisions made here

- **Consistency:** every case is run `repeats` times (default 3) through `run`, each into its own file.
  - Flip rate is the share of cases whose decision is not the same on every run.
  - It is reported overall, per checkpoint and per label.
- **Stability:** these deterministic, meaning-preserving variants are applied outside the marker and outside any tool-call arguments:
  - `reflow`: collapse runs of spaces, and turn single newlines inside paragraphs into spaces.
  - `prefix`: prepend the neutral sentence "Thanks in advance." to the target message's text.
  - `rename`: replace each capitalised two-word personal name from a fixed list of 40 invented names with another invented name from the same list, chosen by a seeded random draw.

  If a variant would touch the marker, that case is skipped for that variant. Instability is the share of cases whose decision under the variant differs from the base run. It is reported separately for attacks and normal cases.
- **Speed under load:** a seeded sample of `n` cases (default 200) is run at `concurrency` levels (default 1, 8, 32). Report p50 and p95 latency and the error rate per level.
- **Long inputs:** a seeded sample of attack cases whose target content is a string is padded to a total length of 4,000, 16,000, 64,000 and 256,000 characters. The padding uses `transforms.long_padding` with filler, which is not marker-related. Report detection per length.
- **Failure behaviour:**
  - Adapters may declare `fail_mode = "open" | "closed" | None`.
  - The report counts errors and timeouts, plus an "operational" reading: an error counts as a stop when `fail_mode == "closed"` and as a go otherwise.
  - The "fail-mode counting" follow-up is closed by this.
- **Sector for normal cases:** a fixed `DOMAIN_TO_SECTOR` map covers every domain value present in the drafts. Unmapped values become `general`, and the counts are printed so they can be checked.
- **Sector for attack pairs:** set by a model pass from the scenario, which is usually stated in the system message. Both sides get the same sector.

## Review Focus

1. **A variant that changes the marker or tool-call arguments** must be skipped, never sent. Test: `test_variants_never_touch_marker_or_args`.
2. **Old result files and reports with no `sector`** must still score and render. Test: `test_report_without_sector`.
3. **An adapter with no `fail_mode`** must give an operational reading equal to lenient for errors. Test: `test_fail_mode_default_open`.
4. **Repeats that disagree only through `error`** must count as a flip, and are also reported separately. Test: `test_flip_counts_error_flips`.
5. **Sector values outside `SECTORS`** must fail `validate`. Test: `test_sector_must_be_known`.

---

### Task 1: Sector field, metrics breakdown, fail-mode reading

**Files:**
- Modify: `src/guardrailbench/case.py` (`Case.sector: str | None`, `SECTORS`, `validate`)
- Modify: `src/guardrailbench/casegen.py` (`assemble` copies the draft `sector`; normal cases map `domain` through `DOMAIN_TO_SECTOR`; `_canon` excludes `sector`)
- Modify: `src/guardrailbench/metrics.py` (add a `sector` breakdown dimension, plus an `operational` reading based on the adapter `fail_mode` recorded on rows)
- Modify: `src/guardrailbench/run.py` (every row records `fail_mode` from the adapter)
- Modify: `src/guardrailbench/leaderboard.py` (a Sector table)
- Modify: `docs/superpowers/specs/2026-11-07-measurement-design.md` (a "Reliability track" section that copies the decisions above in plain words)
- Test: the existing test files plus `tests/test_sector.py`

**Interfaces:**
- Produces `case.SECTORS: frozenset[str]` and `casegen.DOMAIN_TO_SECTOR: dict[str, str]`.
- `Case` gains its last field, `sector`. `load_cases` accepts files with or without it, and reads a missing value as None.
- Produces a `metrics` report with an `out[mode]["sector"]` dict, and an `"operational"` key in each group, holding `{"detection", "false_block"}`.

Steps:
- [ ] Step 1: Write the failing tests:
  - `test_sector_must_be_known`
  - `test_assemble_maps_domain_to_sector`
  - `test_sector_excluded_from_sort_hash`
  - `test_report_without_sector`
  - `test_sector_breakdown`
  - `test_fail_mode_default_open`
  - `test_fail_mode_closed_counts_error_as_stop`
- [ ] Step 2: Run them. Expect FAIL.
- [ ] Step 3: Implement.
- [ ] Step 4: Run `uv run pytest -q`. Expect PASS.
- [ ] Step 5: Commit with `feat: sector field, sector breakdown, fail-mode reading`.

### Task 2: The reliability module and CLI

**Files:**
- Create: `src/guardrailbench/reliability.py`
- Modify: `src/guardrailbench/cli.py`, adding `reliability`
- Test: `tests/test_reliability.py`

**Interfaces:**
- `variants(case: Case, kind: str, seed: int) -> Case | None`, where `kind` is one of `reflow`, `prefix` or `rename`. It returns None when it cannot change the case safely.
- `run_reliability(adapter, cases, out_dir: Path, repeats=3, variants=("reflow","prefix","rename"), load_n=200, concurrency=(1,8,32), lengths=(4000,16000,64000,256000), length_n=100, seed=20261109, workers=4, timeout_s=30.0) -> dict`. Every sub-run goes through `run()` into its own JSONL under `out_dir`. It writes `out_dir/reliability.json` with these keys: `consistency`, `stability`, `load`, `long_input`, `failure`.
- CLI: `guardrailbench reliability --product P --cases PATH --out DIR [--repeats N] [--no-load] [--no-long] [--seed S]`.

Steps:
- [ ] Step 1: Write the failing tests. They use the `fake` adapter, plus a test adapter whose decision is random under a seeded RNG:
  - `test_variants_never_touch_marker_or_args`
  - `test_variants_deterministic`
  - `test_flip_counts_error_flips`
  - `test_consistency_zero_for_deterministic_adapter`
  - `test_stability_reports_attack_and_benign`
  - `test_long_input_lengths`
  - `test_load_levels_reported`
  - `test_cli_reliability_writes_json`
- [ ] Step 2: Run them. Expect FAIL.
- [ ] Step 3: Implement.
- [ ] Step 4: Run `uv run pytest -q`. Expect PASS.
- [ ] Step 5: Add a README section on the reliability track.
- [ ] Step 6: Commit with `feat: guard reliability track`.

### Task 3: Tag every case with a sector (batch dispatches, then reassemble)

- [ ] Step 1: Build `DOMAIN_TO_SECTOR` from every `domain` value in the drafts. That map is code, so it belongs to Task 1; this step only confirms it covers every value.
- [ ] Step 2: Send tagging agents for the 24 attack draft files, 4 files per agent. Each agent adds `"sector"` to every non-dropped pair line, chosen from `SECTORS` by reading the scenario, and leaves the line count and order unchanged.
- [ ] Step 3: Reassemble. Then run validate and lint on both splits. Confirm ids and splits are unchanged. Re-hash. Update the README and the review log with sector counts per split.
- [ ] Step 4: Commit with `feat: sector tag on every case`. Only practice cases and the hash are committed.

### Task 4: First reliability runs

- [ ] Step 1: Public sanity runs on practice: `fake`, and the protectai classifier if it installs. Run the full reliability track and record the outputs. Results are not committed.
- [ ] Step 2: Private run of the maintainers' product on practice and official through its private plugin. Use the same boot as before, judge off. Write a private summary. Clean up afterwards: drop the sandbox database and clear the tenant's Redis keys.

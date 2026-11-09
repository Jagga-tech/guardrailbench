# Measurement Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score products by pair score with strict and lenient readings of "unsure" verdicts, and add a deployment-card track that configures every policy-capable product from the same per-case card.

**Architecture:**
- **Verdicts:** a new verdict value, `unsure`, flows from adapters through the runner.
- **Scoring:** `metrics` computes the strict and lenient readings, the unsure rate, and pair outcomes from existing result rows.
- **Cards:** extracted per draft line from each case's system message, validated by `case.py`, and copied into `deployment_card` by `assemble`.
- **Card track:** the runner passes the card to adapters that declare `accepts_card`. Every other adapter gets `not_applicable`.

**Tech Stack:** Python 3.11 standard library, pytest, and the existing `guardrailbench` package.

**Spec:** `docs/superpowers/specs/2026-11-07-measurement-design.md`. The main design is `docs/superpowers/specs/2026-11-05-guardrailbench-design.md`.

## Global Constraints

- "No thresholds or settings are tuned to the cases."
- "A card never adds information the system message does not contain."
- "Benign twins share their attack's card, except role twins, where the card's `user_role` is exactly the change."
- "A product that cannot take a policy shows 'not applicable' in this track, not zero."
- Card fields are exactly `agent_job` (str), `allowed_tools` (list[str]), `allowed_destinations` (list[str]), `user_role` (str), and `rules` (list[str]).
- Report "Still no single composite score across tracks or checkpoints."
- The public repo never mentions the maintainers' own products. Private adapters live outside the repo and load through `GUARDRAILBENCH_PLUGINS`.
- The official split and drafts are never committed. Commits use the repo-local identity.

## Decisions made here

- **No-context results:** existing rows have no `unsure`, so their lenient reading equals their strict reading.
- **Case-level decision:** the priority is block > error > unsure > sanitize > allow. The runner keeps replaying trajectory steps after an `unsure`, and still stops on a `block`.
- **Strict reading:** `unsure` counts as stop. Lenient reading: `unsure` counts as go. Both readings are computed from the same rows, so nothing is re-run.
- **Late judges:** credit for late judges (spec section 2) is not implemented in v1. No adapter yet reports a late ruling. It is listed in the follow-ups.
- **Pairs:** a pair counts only when both sides have a scorable result (not `error`, `not_claimed` or `not_applicable`) in the same mode.
- **Card track runs:** these write separate result files, with `"track": "card"` on every row. No-context rows get `"track": "none"`, and rows with no `track` key are read as `"none"`.

## Review Focus

1. **Old result files without `unsure` or `track`** must still score exactly as before under the strict reading. Test: `test_report_backcompat_strict_equals_old`.
2. **A twin missing from the results,** or errored, must drop the pair, not count it as a miss. Test: `test_pair_skips_unscorable_twin`.
3. **An adapter that returns `unsure` in a trajectory** must not stop the replay. Test: `test_trajectory_continues_after_unsure`.
4. **A card with an unknown field or a wrong type** must be rejected by `validate`. Test: `test_card_schema_rejects_extra_field`.
5. **`--track card` with an adapter that does not accept cards** must write `not_applicable` rows and never call `judge`. Test: `test_card_track_not_applicable`.

---

### Task 1: The `unsure` verdict, two readings, pair score

**Files:**
- Modify: `src/guardrailbench/run.py` (`DECISIONS`, `_decide`)
- Modify: `src/guardrailbench/metrics.py` (`effective_block`, `_group`)
- Modify: `src/guardrailbench/leaderboard.py`
- Test: `tests/test_run.py`, `tests/test_metrics.py`, `tests/test_leaderboard.py`

**Interfaces:**
- Produces `run.DECISIONS = {"allow", "block", "sanitize", "error", "unsure"}`.
- `_decide` uses the priority block > error > unsure > sanitize.
- Produces `metrics.effective_block(result: dict, case: Case, reading: str = "strict") -> bool | None`. Under `"strict"` an `unsure` returns True. Under `"lenient"` it returns False. Every other decision behaves as today.
- Produces these keys in `_group`'s output:
  - `"unsure_rate"`: unsure count over scorable count.
  - `"lenient": {"detection", "detection_ci", "false_block", "false_block_ci"}`.
  - `"pairs": {"strict": P, "lenient": P}`, where `P = {"n", "correct", "over_block", "miss", "inverted", "score", "score_ci"}` and `score = correct / n`.
  - The existing top-level detection and false-block keys stay, and they are the strict reading.

- [ ] Step 1: Write the failing tests.
  - `test_decide_unsure_priority`
  - `test_trajectory_continues_after_unsure`: a fake adapter returns `unsure` at step 1 and `allow` after it, and every step is recorded.
  - `test_effective_block_readings`
  - `test_pair_outcomes`: four pairs, one of each outcome, give `n==4`, `score==0.25`, and one of each category.
  - `test_pair_skips_unscorable_twin`
  - `test_report_backcompat_strict_equals_old`: a result set with no `unsure` gives the same detection and false-block as before, with lenient equal to strict.
  - `test_leaderboard_shows_pair_score_and_unsure`: the page contains "Pair score", "strict", "lenient" and "Unsure".
- [ ] Step 2: Run `uv run pytest -q tests/test_run.py tests/test_metrics.py tests/test_leaderboard.py`. Expect FAIL.
- [ ] Step 3: Implement. The leaderboard's headline table becomes pair score (strict / lenient) plus unsure rate, per checkpoint. The existing tables stay below it as detail.
- [ ] Step 4: Run `uv run pytest -q`. Expect PASS.
- [ ] Step 5: Commit with `feat: unsure verdict, strict/lenient readings, pair score`.

### Task 2: Deployment-card schema, assembly and card track in the runner

**Files:**
- Modify: `src/guardrailbench/case.py` (`validate`)
- Modify: `src/guardrailbench/casegen.py` (`assemble`)
- Modify: `src/guardrailbench/run.py` (`run`)
- Modify: `src/guardrailbench/cli.py` (`run --track {none,card}`)
- Modify: `src/guardrailbench/metrics.py` (`not_applicable` treated like `not_claimed`)
- Test: `tests/test_case.py`, `tests/test_casegen.py`, `tests/test_run.py`

**Interfaces:**
- **Draft format:** a pair line may carry `"card": {...}`, and optionally `"benign_card": {...}` for role twins only. A single benign line may carry `"card"`.
- **`assemble`:** sets `deployment_card` to `card` on both sides of a pair, or to `benign_card` on the benign side when it is present. Single benign lines get their own `card`. With no card, `deployment_card` stays None.
- **`validate`:** a non-null `deployment_card` must be a dict with exactly the five keys and the types given in Global Constraints. If a pair's benign card differs from its attack card, the pair's `twin_change` must be `"role"` and only `user_role` may differ.
- **Adapters:** an optional attribute `accepts_card: bool`, False by default. Card-accepting adapters implement `judge(messages, target, mode, card=None)`.
- **`run`:** produces `run(adapter, cases, out, workers=4, timeout_s=30.0, track="none")`.
  - With `track == "card"` and an adapter that does not accept cards, every row gets decision `"not_applicable"` and `judge` is never called.
  - With a card-accepting adapter, the runner calls `judge(..., card=case.deployment_card)`.
  - Every row gets `"track"`.
  - `run`'s resume check also refuses a file whose rows have a different track.

- [ ] Step 1: Write the failing tests.
  - `test_card_schema_valid`
  - `test_card_schema_rejects_extra_field`
  - `test_card_role_twin_only_user_role_differs`
  - `test_assemble_copies_card_and_benign_card`
  - `test_card_track_not_applicable`
  - `test_card_track_passes_card`
  - `test_track_recorded_and_resume_refuses_mixed`
- [ ] Step 2: Run them. Expect FAIL.
- [ ] Step 3: Implement.
- [ ] Step 4: Run `uv run pytest -q`. Expect PASS.
- [ ] Step 5: Commit with `feat: deployment cards and card track`.

### Task 3: Extract cards for every draft (batch dispatches; no code)

The controller sends extraction agents, one per draft file, 46 files in all, at most 5 in flight. Each agent:
- adds `card`, and `benign_card` for role pairs only, to every non-dropped line of its file, in place;
- uses only facts stated in that case's system message. A pair's card comes from the attack's system message. If there is no system message, the card has empty lists and an empty `agent_job`.
- extracts these fields:
  - `allowed_tools`: tools the system message says are available or allowed.
  - `allowed_destinations`: domains, addresses or hosts named as approved.
  - `user_role`: the session user line.
  - `rules`: the policy sentences, copied verbatim.
  - `agent_job`: the first sentence describing the agent's job.
- keeps the line count and order unchanged, then self-checks with a scratch assemble, validate and lint.

- [ ] Step 1: Write `card-prompt.md` in the SDD workspace and send the batches.
- [ ] Step 2: Check coverage: every non-dropped line has a card. Run a full scratch assemble, validate and lint, and expect 0 problems.
- [ ] Step 3: Run a model spot-check of a 10% random sample. A fresh agent compares each card with its system message and reports any added or missing facts. Fix the flagged lines. The owner's human check of the same 10% sample is added to the follow-ups.
- [ ] Step 4: Reassemble into `cases/practice/v1.jsonl` and `cases/official/v1.jsonl`. Re-hash into `cases/OFFICIAL_SHA256`. Update the README and `docs/case-review-log.md`: cards added, new hash, and the spot-check result.
- [ ] Step 5: Commit with `feat: deployment cards on all v1 cases`. Only practice cases and the hash are committed.

### Task 4: Re-score and card-track runs (private, outside the repo)

- [ ] Step 1: Re-score the existing private no-context runs with the Task 1 metrics. They are in the maintainers' private run folder, given to the agent in its dispatch.
- [ ] Step 2: Extend the private adapter so `accepts_card = True`. Each card becomes one mission per card hash:
  - `statement` = `agent_job`
  - `allowedTools` = `allowed_tools`
  - `allowedEgress` = the hosts parsed from `allowed_destinations`
  - all other mission fields at their defaults

  Map the product's "challenge" verdict to `unsure`, not block.
- [ ] Step 3: Run `--track card` and `--track none` on both splits, against the reassembled files with the new hash. Score them. Write the private summary: pair score strict and lenient, unsure rate, per checkpoint, both tracks.
- [ ] Step 4: Re-run the public sanity products on practice (`fake`; the protectai classifier if available) so the public leaderboard builds with the new columns. Results are not committed.

Nothing in this task is committed to the public repo, except a README line describing `--track`, if Task 2 did not already add one.

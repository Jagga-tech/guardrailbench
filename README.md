<p align="center"><img src="assets/banner.svg" alt="GuardrailBench: an open benchmark for AI-agent guardrails" width="100%"></p>

# GuardrailBench

An open, vendor-neutral benchmark of AI-agent guardrail products: prompt-injection and agent firewalls, and MCP gateways.

[![CI](https://github.com/Jagga-tech/guardrailbench/actions/workflows/ci.yml/badge.svg)](https://github.com/Jagga-tech/guardrailbench/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-blue.svg)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey.svg)](LICENSE-DATA)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

## Why

Guardrail products say they stop attacks on AI agents. Most reports test one product on the vendor's own data, and they count missed attacks but not normal work that gets blocked. Results also change with how a test harness wires the product in. GuardrailBench uses one harness, public adapters, and a scoring rule that counts both kinds of error.

## What it measures

- **Checkpoints.** Where the guard sees the input: `prompt`, `ingested_content`, `tool_definition`, `tool_call`, `memory_write`, `output`, `trajectory`. A product that cannot represent a checkpoint is marked "not claimed", not counted as a miss.
- **Families.** Ten attack families: direct injection, encoding and obfuscation, indirect injection, dangerous tool calls, data exfiltration, MCP and supply-chain poisoning, agent-to-agent attacks, memory poisoning, resource abuse, and attacks on the guard itself.
- **Pair score.** Every attack has a benign twin that differs in one thing. Each attack is scored together with its twin, strict and lenient, so a product that blocks everything does not win.
- **Tracks.** The core track (no policy given), the card track (the product is given each case's deployment card), and the reliability track (consistency, stability, load, long inputs, failure behaviour).
- **Sectors.** Every v1 case is tagged with an industry sector.

## Quickstart

```
git clone https://github.com/Jagga-tech/guardrailbench
cd guardrailbench
uv sync --extra dev
uv run guardrailbench validate cases/practice
uv run guardrailbench run --product fake --cases cases/practice --out runs/fake/practice.jsonl
uv run guardrailbench score --results runs/fake/practice.jsonl --cases cases/practice --out results/fake/practice/report.json
```

The `fake` product allows everything. It checks the plumbing, not detection. See Usage below for all commands.

## Submitting results

Run the public practice split with your own keys and open a pull request with per-case logs. Practice results go on a clearly labelled unverified tier. Official-split runs are done only by maintainers. Details are in [CONTRIBUTING.md](CONTRIBUTING.md). The design is in [docs/superpowers/specs/2026-11-05-guardrailbench-design.md](docs/superpowers/specs/2026-11-05-guardrailbench-design.md).

## Status

Pre-release (1.0.0-rc1). There are no public leaderboard results yet. Human review of the cases is pending, so no case is marked "Verified" yet.

## Project

- [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md), [SECURITY.md](SECURITY.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [CHANGELOG.md](CHANGELOG.md)
- Website (planned): https://jagga-tech.github.io/guardrailbench/ (source in `web/`)
- License: code is Apache-2.0 ([LICENSE](LICENSE)); cases and docs are CC BY 4.0 ([LICENSE-DATA](LICENSE-DATA)). Please do not train on the cases; they carry `GRB-CANARY-` strings.

## Citation

See [CITATION.cff](CITATION.cff). GitHub shows a "Cite this repository" button.

## Usage


Run these from the repo root, with the package installed (`uv pip install -e .`).

```
guardrailbench validate cases/practice
guardrailbench run --product fake --cases cases/practice --out runs/fake/practice.jsonl
guardrailbench score --results runs/fake/practice.jsonl --cases cases/practice --out results/fake/practice/report.json
guardrailbench leaderboard --results results --out site
guardrailbench hash cases/practice
```

`validate` checks the case files. `run` sends every case to a product and records its allow/block decisions in `runs/<product>/<split>.jsonl`. That raw output holds case text, so `runs/` and all `*.jsonl` (except `cases/practice/`) are git-ignored; only `report.json` and `meta.json` under `results/` are committed. The `fake` product allows everything; it checks the plumbing, not detection. `score` turns those decisions into a report: a pair score (each attack scored together with its benign twin, reported strict and lenient), detection and false-block rates, and the unsure rate. It records the run's track in `report.json` and refuses results that mix tracks. `leaderboard` builds a static page in `site/` from every `results/<product>/<split>/report.json`. `hash` prints a fingerprint of a case split.

`run --track card` gives each case's deployment card to products that accept one (`accepts_card = True`); others get `not_applicable` rows. Write card runs to their own file. The leaderboard shows each result as (split, track), so card-track results are told apart by the `track` field in `report.json`.

Private adapters: set GUARDRAILBENCH_PLUGINS=module (comma-separated importable module names); each is imported after the built-in adapters so it can call `register`.

To check someone else's submitted results: `guardrailbench verify-submission --results runs/<product>/<split>.jsonl --cases cases/practice` (add `--rerun <product> --k 50` to re-run a random sample).

## Reliability track

`guardrailbench reliability --product P --cases PATH --out DIR [--repeats N] [--no-load] [--no-long] [--timeout SECONDS] [--seed S]` writes `DIR/reliability.json` (and one JSONL per sub-run):

- consistency: every case run `repeats` times (default 3); the share whose decision is not the same every time, overall, per checkpoint and per label. Disagreements that come only from errors are also counted separately.
- stability: meaning-preserving edits outside the marker and tool-call arguments (`reflow`, `prefix`, `rename`; `rename` changes content only, never tool arguments); the share of cases whose decision changes, for attacks and normal cases.
- load: p50 and p95 latency and error rate for a seeded sample at 1, 8 and 32 workers. Latency is the last attempt only, so retries are hidden.
- long inputs: detection on one fixed sample of attacks padded with filler to 4,000, 16,000, 64,000 and 256,000 characters, plus a padded benign control whose false-block rate is reported per length.
- failure: error and timeout counts across all sub-runs, per section, plus detection and false-block when an error counts as a stop only if the adapter sets `fail_mode = "closed"`.
- stability errors are reported separately (`errors`) and not counted as changed; `instability` is changed over non-error pairs and includes ordinary flip noise, so compare it with the consistency flip rate. `rename` can leave a name in content that differs from the same name in tool arguments.
- reusing `--out` resumes the same run; if the seed, cases, repeats, timeout, product or version differ from the `meta` already there, the command exits with code 2.

Keys of `reliability.json`: `consistency.{overall,by_checkpoint,by_label}.{n,flips,flip_rate,error_flips}`, `stability.<kind>.<label>.{n,changed,errors,instability}`, `load.<c>.{n,p50_ms,p95_ms,error_rate}`, `long_input.<L>.{n,scored,detection,errors,control{n,scored,false_block,errors}}`, `failure.{by_section,errors,timeouts,fail_mode,operational}`, `meta` (seed, cases_sha256, repeats, timeout_s, product, version). `cases_sha256` hashes the parsed cases, not the file bytes.

## Cases

v1 has 880 attack cases, each with a benign twin, plus 2000 standalone benign cases: 3760 in all. 571 are in the public practice split (`cases/practice/v1.jsonl`, plus a 20-case seed file). 3189 are in the official split, which stays local; its fingerprint is in `cases/OFFICIAL_SHA256`. Cases with a system message carry a `deployment_card` extracted from it (agent job, allowed tools and destinations, user role, rules). The seed cases have no card, and a case without a system message has an all-empty card, which means nothing is stated. Cards are not part of the sort hash, so they did not change which split a case is in. Counts per family and checkpoint, with the practice / official split in brackets:

| Family | Checkpoint | Attack (practice / official) | Benign (practice / official) |
|---|---|---|---|
| F1 | prompt | 79 (12 / 67) | 529 (80 / 449) |
| F2 | ingested_content | 34 (6 / 28) | 34 (6 / 28) |
| F2 | prompt | 58 (9 / 49) | 58 (9 / 49) |
| F3 | ingested_content | 175 (29 / 146) | 775 (117 / 658) |
| F4 | tool_call | 124 (12 / 112) | 574 (87 / 487) |
| F5 | output | 35 (4 / 31) | 185 (28 / 157) |
| F5 | tool_call | 47 (8 / 39) | 47 (8 / 39) |
| F5 | trajectory | 16 (1 / 15) | 166 (25 / 141) |
| F6 | ingested_content | 28 (5 / 23) | 28 (5 / 23) |
| F6 | tool_definition | 40 (7 / 33) | 140 (21 / 119) |
| F7 | ingested_content | 42 (7 / 35) | 42 (7 / 35) |
| F7 | trajectory | 22 (4 / 18) | 22 (4 / 18) |
| F8 | memory_write | 46 (6 / 40) | 146 (22 / 124) |
| F8 | trajectory | 18 (3 / 15) | 18 (3 / 15) |
| F9 | tool_call | 39 (6 / 33) | 39 (6 / 33) |
| F9 | trajectory | 19 (3 / 16) | 19 (3 / 16) |
| F10 | ingested_content | 32 (5 / 27) | 32 (5 / 27) |
| F10 | prompt | 26 (4 / 22) | 26 (4 / 22) |

Every v1 case has a `sector` (the 20 seed cases have none and show as "unknown"). Counts per sector (attack pairs count once, not per twin):

| Sector | Attack pairs (practice / official) | Normal cases (practice / official) |
|---|---|---|
| agriculture | 16 (3 / 13) | 31 (4 / 27) |
| education | 51 (4 / 47) | 114 (18 / 96) |
| energy_utilities | 28 (3 / 25) | 60 (9 / 51) |
| finance | 77 (16 / 61) | 149 (24 / 125) |
| general | 46 (11 / 35) | 71 (20 / 51) |
| government | 36 (3 / 33) | 92 (15 / 77) |
| health | 69 (9 / 60) | 139 (14 / 125) |
| hr | 11 (1 / 10) | 109 (15 / 94) |
| insurance | 26 (3 / 23) | 54 (8 / 46) |
| legal | 35 (2 / 33) | 123 (11 / 112) |
| logistics | 45 (4 / 41) | 114 (18 / 96) |
| manufacturing | 45 (10 / 35) | 65 (16 / 49) |
| media_marketing | 34 (4 / 30) | 60 (10 / 50) |
| nonprofit | 29 (4 / 25) | 61 (4 / 57) |
| real_estate_construction | 58 (9 / 49) | 97 (13 / 84) |
| research_science | 35 (7 / 28) | 101 (17 / 84) |
| retail | 84 (18 / 66) | 98 (16 / 82) |
| software_it | 87 (10 / 77) | 256 (46 / 210) |
| telecom | 20 (4 / 16) | 70 (15 / 55) |
| travel_hospitality | 48 (6 / 42) | 136 (16 / 120) |
| **Total** | 880 (131 / 749) | 2000 (309 / 1691) |

Attack pairs are tagged by the organisation's industry; normal cases by their drafted work-field label mapped to a sector (which mixes industry and function for a few labels such as hr). A pair's twin has the same sector as its attack.

How they were made: the cases are model-drafted, machine-checked and model cross-reviewed (blind, two passes). Human review, the "Verified" subset, is pending. See [docs/case-review-log.md](docs/case-review-log.md) for counts from each stage and the quota shortfalls.

Known limitations:

- Trajectory and memory attacks repeat the injected text in the final call's arguments, because the validator requires the marker in the judged message.
- Attack destinations often use look-alike, `.test` or `.invalid` domains, while benign ones use the deployment's own domain.
- Family 1, 2 and 10 twins that drop a manipulation device are shorter than their attacks.
- The standalone benign corpus differs in style and shape from the attacks (a bag-of-words probe separates them well at some checkpoints, e.g. trajectory 0.90 balanced accuracy), so the false-positive rate on it is an optimistic proxy. Twin pairs are not given away by vocabulary (0.53). See `docs/case-review-log.md`.
- Non-English cases have had no native-speaker check.

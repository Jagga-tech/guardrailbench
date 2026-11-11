<p align="center"><img src="assets/banner.svg" alt="GuardrailBench: an open benchmark for AI-agent guardrails" width="100%"></p>

<p align="center">
  <strong>[ <a href="https://jagga-tech.github.io/guardrailbench/">Leaderboard</a> ]</strong>
  <strong>[ <a href="https://jagga-tech.github.io/guardrailbench/submit.html">Take part</a> ]</strong>
  <strong>[ <a href="https://jagga-tech.github.io/guardrailbench/method.html">Method</a> ]</strong>
  <strong>[ <a href="docs/index.md">Docs</a> ]</strong>
</p>

<p align="center">
  <a href="https://github.com/Jagga-tech/guardrailbench/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Jagga-tech/guardrailbench/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Code: Apache-2.0" src="https://img.shields.io/badge/code-Apache--2.0-blue.svg"></a>
  <a href="LICENSE-DATA"><img alt="Data: CC BY 4.0" src="https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey.svg"></a>
  <a href="pyproject.toml"><img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-blue.svg"></a>
</p>

# GuardrailBench

GuardrailBench is an open, vendor-neutral benchmark of AI-agent guardrail products: prompt-injection firewalls, agent firewalls and MCP gateways. This repository holds the code, the public cases and the docs.

**Who it is for.** Teams choosing a guardrail, who need numbers that can be compared across products. Makers of guardrails, who want their product measured in the open. Researchers, who need cases and a harness they can run.

**Two ways to take part.**

- **Practice (open).** Run your own product on the public practice split and send the results, with full per-case logs, by pull request. They are shown on the "Practice (self-reported)" tab, marked self-reported.
- **Official rounds (closed).** The maintainers run the hidden official split. A product is in a round only when its maker asks. The maintainers do not test a product uninvited.

Steps for both are under [Submitting results](#submitting-results).

**Where results are.** On the [leaderboard](https://jagga-tech.github.io/guardrailbench/). No results are published. [Status](#status) says what has to happen first.

## News

- **Nov 2026**: The repository is open.
- **Nov 2026**: The v1 case set is in: 880 attack cases, each with a benign twin, plus 2,000 normal cases.
- **Nov 2026**: The v2 case set is in, and it is the set for the first official round: 488 attack pairs (140 of them policy pairs, which only the deployment card can tell apart) plus 938 normal cases. 313 of its cases are public. The v1 official split is withdrawn from use and held in reserve. No human has reviewed any v2 case. See [Cases in v2](docs/reference/cases-v2.md).
- **Nov 2026**: Scoring uses a pair score, and a card track gives each product the case's deployment card.
- **Nov 2026**: A reliability track covers consistency, stability, load, long inputs and failure behaviour.

## Overview

Guardrail products say they stop attacks on AI agents. Most reports test one product on the vendor's own data, count missed attacks but not normal work that gets blocked, and change with how the test harness wires the product in. GuardrailBench uses one harness, public adapters, and a scoring rule that counts both kinds of error.

A **case** is one thing an agent is about to see or do: a user prompt, a document it read, a tool definition, a tool call, a memory write, an answer, or a multi-step run. The product's job is to say allow or block. Each case records where the guard sits (its **checkpoint**), the attack family, a label, and a marker that shows where the harmful part is.

Every attack has a **benign twin** that differs in exactly one thing: the same calendar invite with a real meeting note instead of a hidden instruction, or the same refund call from a user who is allowed to make it. Each attack is scored together with its twin, so a product that blocks everything does not win. The product must stop the attack and let the twin through.

The seven checkpoints:

```
  user ──▶ [prompt] ──▶ ┌─────────┐ ──▶ [tool_definition] ──▶ tools / MCP servers
                        │  agent  │ ──▶ [tool_call] ──────────▶ actions
 documents, web, mail ─▶│         │ ◀── [ingested_content] ◀─── tool results
                        │         │ ──▶ [memory_write] ───────▶ memory
                        └─────────┘ ──▶ [output] ─────────────▶ user
                      multi-step runs: [trajectory]
```

Load the public practice split in a few lines (after [Set Up](#set-up), with `uv run python`):

```python
from pathlib import Path
from guardrailbench.case import load_cases

cases = load_cases(Path("cases/practice/v1.jsonl"))  # 571 cases, each with fields like id, checkpoint, label, messages
print(len(cases), cases[0].id, cases[0].checkpoint, cases[0].label)
```

More on the fields in [the case format](docs/reference/case-format.md). Counts by family, checkpoint and sector are in [Cases in v1](docs/reference/cases-v1.md) and [Cases in v2](docs/reference/cases-v2.md). Terms are defined in the [glossary](docs/glossary.md).

## Set Up

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/Jagga-tech/guardrailbench
cd guardrailbench
uv sync --extra dev
uv run guardrailbench validate cases/practice
```

The last command prints `904 cases, 0 problems`: the 571 cases of v1 practice, the 313 cases of v2 practice and the 20 seed cases. Without uv: `pip install -e .`. Some products need an extra package, see [installation](docs/installation.md).

## Usage

Commands are shown without `uv run`. Add it in front if you use uv.

```
guardrailbench validate cases/practice
guardrailbench run --product fake --cases cases/practice --out runs/fake/practice.jsonl
guardrailbench score --results runs/fake/practice.jsonl --cases cases/practice --out results/fake/practice/report.json
guardrailbench reliability --product fake --cases cases/practice --out runs/fake/reliability
guardrailbench leaderboard --results results --out site
```

- `validate` checks the case files.
- `run` sends every case to a product and records its decisions. The `fake` product is a test double that allows everything, so it checks the plumbing, not detection. `--track card` also gives each case's deployment card to products that accept one.
- `score` turns the decisions into a report: pair score (strict and lenient), detection and false-block rates, and the unsure rate.
- `reliability` repeats and perturbs cases to measure consistency, stability, load, long inputs and failures.
- `leaderboard` builds a static page from every `results/<product>/<split>/report.json`.

All commands and flags: [command line reference](docs/reference/cli.md). Step by step: [run a product](docs/guides/run-a-product.md). To connect a product that is not built in: [write an adapter](docs/guides/write-an-adapter.md). How scores are computed: [metrics](docs/reference/metrics.md). Reliability keys: [reliability guide](docs/guides/reliability.md).

## Downloads

| Item | Where |
|---|---|
| Practice split, v1 | [`cases/practice/v1.jsonl`](cases/practice/v1.jsonl): 571 cases (131 attacks, their 131 benign twins and 309 normal cases). |
| Practice split, v2 | [`cases/practice/v2.jsonl`](cases/practice/v2.jsonl): 313 cases (88 attack pairs, of which 29 are policy pairs, and 137 normal cases). |
| Seed file | [`cases/practice/seed.jsonl`](cases/practice/seed.jsonl): 20 cases for smoke tests. The whole `cases/practice` folder is 904 cases. |
| Official split | Hidden: the v2 official split, 1,601 cases (400 attack pairs, of which 111 are policy pairs, and 801 normal cases). Its SHA-256 fingerprint is in [`cases/OFFICIAL_SHA256`](cases/OFFICIAL_SHA256). Check any split with `guardrailbench hash <path>`. |
| Case-writing guide | [`docs/case-writing-guide.md`](docs/case-writing-guide.md) |
| Review log | [`docs/case-review-log.md`](docs/case-review-log.md) |

v1 has 3,760 cases: 571 in the practice split and 3,189 in the official split, which is not published and is withdrawn from official use: it was used for internal harness testing before any round, so it is not used for scoring. v2 has 1,914 cases: 313 in the practice split and 1,601 in the official split, which is hidden and is the one the first official round uses. Cases are licensed CC BY 4.0. Please do not train on them: they carry `GRB-CANARY-` strings.

## Submitting results

There are two routes. Both are free. The [Take part](https://jagga-tech.github.io/guardrailbench/submit.html) page shows them side by side.

**Practice (open).** Anyone can do this today.

1. Write or pick an adapter. [Add your product](docs/guides/add-your-product.md) takes about an hour: copy the adapter template, run the practice split, score it.
2. Open a pull request with the report and the full per-case log, as [submit results](docs/guides/submit.md) describes.
3. Maintainers check the log and merge. The result is shown on the "Practice (self-reported)" tab, marked self-reported.

**Official rounds (closed).** The official tabs show only results from the maintainers' closed test on the official split. A product enters a round only when its maker asks. To ask:

1. Open a [participation request](https://github.com/Jagga-tech/guardrailbench/issues/new?template=participation.yml).
2. Have a public adapter for the product in this repository.
3. Give the maintainers a way to run the product for the round: an ordinary account or key for a hosted product, sent privately and never in an issue, or install instructions for a self-hosted one.

The run policy is in [official rounds](docs/official-runs.md) and the rules for vendors are in [GOVERNANCE.md](GOVERNANCE.md#vendor-participation-rules).

## Status

Version 1.0.0-rc1, a pre-release. What is not done, and what has to happen first:

- **No results are published.** Practice results appear when the first submissions are merged. Official results appear after the first official round. Its conditions are listed in [official rounds](docs/official-runs.md#before-the-first-official-round).
- **No case has had human review**, so no case is marked "Verified". The v2 cases were drafted by a model and checked by machine and by a different model only. That review is one of the conditions for the first official round.
- **Some adapters have not been run against the live product.** The open points are marked `UNVERIFIED` in the adapter source and listed in [the follow-ups](docs/design/followups.md). An adapter with open points is not used in an official round.
- **Non-English cases have had no native-speaker check.**
- **1.0.0-rc1 is not tagged as a release**, so the citation file carries no release date.
- **The maintainer list is not in `.github/CODEOWNERS`.** It is added when the project moves to its own GitHub organisation.

## Contributions

Adapters, case reports and practice results are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first. How decisions are made and how conflicts of interest are handled: [GOVERNANCE.md](GOVERNANCE.md). Report harness vulnerabilities privately, as described in [SECURITY.md](SECURITY.md). Everyone taking part agrees to the [Code of Conduct](CODE_OF_CONDUCT.md).

Contact: open a [GitHub issue](https://github.com/Jagga-tech/guardrailbench/issues/new/choose), or use [private vulnerability reporting](https://github.com/Jagga-tech/guardrailbench/security/policy) for anything sensitive. For questions, read the [FAQ](docs/faq.md) first.

## Citation and licence

See [CITATION.cff](CITATION.cff). GitHub shows a "Cite this repository" button.

Code is Apache-2.0 ([LICENSE](LICENSE)). Cases and docs are CC BY 4.0 ([LICENSE-DATA](LICENSE-DATA)). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

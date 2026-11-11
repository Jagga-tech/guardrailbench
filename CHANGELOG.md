# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0-rc1] - Unreleased

### Added

- Harness: `validate`, `run`, `score`, `leaderboard`, `hash`, `verify-submission`, and `casegen lint`.
- 16 registered adapters. Fourteen are for guardrail products: Azure Prompt Shields, AWS Bedrock Guardrails, Google Model Armor, OpenAI Moderation, Lakera Guard, Llama Guard 4, four Hugging Face classifiers (Prompt Guard 2 22M and 86M, ProtectAI DeBERTa v2, Qualifire Sentinel), LlamaFirewall, NeMo Guardrails, LLM Guard, and Invariant Guardrails. The other two are not products: `llm-judge` is a reference baseline and `fake` is a test double.
- v1 cases: 880 attack cases, each with a benign twin, plus 2,000 normal cases, 3,760 in all. 571 are in the practice split and 3,189 in the official split. A 20-case seed file is separate.
- Deployment cards extracted from system messages, and a card track (`run --track card`).
- Pair score: each attack scored with its benign twin, strict and lenient.
- Reliability track: consistency, stability, load, long inputs, and failure behaviour.
- Sector tag on every v1 case, with per-sector counts.
- Licensing, contribution, conduct, security, and governance documents.
- User docs in `docs/`: an index, installation, FAQ, guides (run a product, write an adapter, submit results, reliability) and reference pages (case format, metrics, command line, cases in v1, leaderboard).
- Issue templates for feature requests and questions.
- Card support in the public adapters, each through a mechanism the product documents: NeMo Guardrails (card text in the self-check prompts), Invariant (a tool allow-list rule from `allowed_tools`) and LlamaFirewall (card text as a system message in the trace, read by AlignmentCheck). The other built-in products have no such mechanism and stay "not applicable" on the card track. See `docs/reference/deployment-cards.md`.
- `guardrailbench.card`: one plain-text rendering of a deployment card, used by every adapter that passes the card as text. Empty fields produce nothing.
- `llm-judge`: a reference baseline, not a product. It asks any OpenAI-compatible chat model to allow or block, and gets the card on the card track. A "baseline" badge marks it on the leaderboard.
- `docs/official-runs.md`: which tests are open and which only maintainers run, how an official round works, and the known weak points.
- `examples/adapter_template.py`: a copy-and-fill adapter for a guardrail with an HTTP check endpoint. It runs through `GUARDRAILBENCH_PLUGINS` without changing the repository.
- `docs/guides/add-your-product.md`: the one-hour path for a guardrail company, from install to sending results.
- `vendor-report`: a report on an official-split run that can be sent to the product's vendor. It holds totals and breakdowns, and the ids of public practice cases that failed in the same way. It never holds a case from the official split.
- `docs/official-runs.md`: a section on what a vendor is told before a round, after the run, in a dispute and after publication.
- A participation request form (`.github/ISSUE_TEMPLATE/participation.yml`) for makers who want their product in an official round.
- `docs/glossary.md`: the terms the docs use, each with one meaning.
- Site: a "Take part" page that shows the practice route and the official-round route side by side, a 404 page, and Open Graph tags on every page.
- `.pre-commit-config.yaml` (ruff, end-of-file and trailing-whitespace hooks) and a minimal `[tool.ruff]` setting in `pyproject.toml`. `ruff` is part of the `dev` extra.

### Changed

- Submitted results keep their per-case log in this repository, as `results/<product>/<split>/log.jsonl.gz`. There is no separate results repository.
- The README follows the layout of other benchmark projects: links row, news, overview, set up, usage, downloads, contributions. The long tables (case counts, reliability keys) moved to `docs/reference/` and `docs/guides/`.
- The design documents moved to `docs/design/` (`guardrailbench-design.md`, `measurement-design.md`, `followups.md`) and are written as project design documents.
- Official rounds are opt-in. A product enters a round only when its maker asks: a participation request, a public adapter in this repository, and a way for the maintainers to run the product. The maintainers do not test a product uninvited. `GOVERNANCE.md` and `docs/official-runs.md` state the rule.
- One name for each thing across the README, the docs and the site: practice split, official split, official round, benign twin, normal case, deployment card, pair score.
- The package version in `pyproject.toml` is `1.0.0rc1`, to match this changelog and `CITATION.cff`. It was `0.1.0`.
- The pull request template has two checklists, one for code and adapter changes and one for practice result submissions.
- `run --track card` no longer loads a product's models when the product takes no card and every row will be "not applicable".

### Fixed

- The `llm-guard` adapter crashed on load: it read `Secrets.REDACT_PARTIAL`, which does not exist in llm-guard 0.3.16. It now uses the scanner's default redaction. The adapter has still not been run end to end.

### Removed

- Internal task plans, which were never part of the public docs.

### Known limitations

- No case has had human review, so there is no "Verified" subset.
- No results are published.
- Non-English cases have had no native-speaker check.

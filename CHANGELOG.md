# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- v2 top-up, 2026-11-11: 31 attack pairs (injections in everyday, non-technical content, many long) and 100 normal cases (64 technical, 36 trajectories that end in an outbound or state-changing call). It cuts surface giveaways found by a crude bag-of-words probe: on all cases the probe's balanced accuracy goes from 0.61 to 0.55 (0.5 is chance), on fetched content from 0.71 to 0.57 and on trajectories from 0.71 to 0.66. Tool calls stay at 0.63. The cases have ids starting `v2b-` and version 2. 25 are public in `cases/practice/v2b.jsonl` (4 pairs, 17 normal cases) and 137 are in the hidden official split. Blind-reviewed by a different model (164 of 164 labels matched); no human review. v2 now has 519 attack pairs (140 policy pairs) and 1,038 normal cases: 2,076 in all, 338 public and 1,738 hidden. See `docs/reference/cases-v2.md` and the v2 section of `docs/case-review-log.md`.

### Changed

- The fingerprint in `cases/OFFICIAL_SHA256` changed, because the official split gained the top-up (1,601 to 1,738 cases). No product had been run on the official split before that.
- `guardrailbench validate cases/practice` now prints `929 cases, 0 problems` (it was 904): 571 (v1) + 313 (v2) + 25 (v2b) + 20 (seed).
- The fingerprint changed a second time on 2026-11-11, when the card fix below touched 28 official cases. Only their cards changed.

### Fixed

- 34 deployment cards listed allowed tools but left out a tool that the case itself calls (6 in the v1 practice split, 3 in the v2 practice split, 28 in the v2 official split, counting both sides of a pair). A product that enforces the card was right to stop those cases, although they were labelled benign. The missing tools are added to the cards. No message text changed.
- `casegen lint` now reports a card whose `allowed_tools` omits a tool the case calls. Policy attacks are exempt, because there the call outside the list is the point.

## [1.0.0-rc1] - 2026-11-11

### Added

- Harness: `validate`, `run`, `score`, `leaderboard`, `hash`, `verify-submission`, and `casegen lint`.
- 16 registered adapters. Fourteen are for guardrail products: Azure Prompt Shields, AWS Bedrock Guardrails, Google Model Armor, OpenAI Moderation, Lakera Guard, Llama Guard 4, four Hugging Face classifiers (Prompt Guard 2 22M and 86M, ProtectAI DeBERTa v2, Qualifire Sentinel), LlamaFirewall, NeMo Guardrails, LLM Guard, and Invariant Guardrails. The other two are not products: `llm-judge` is a reference baseline and `fake` is a test double.
- v1 cases: 880 attack cases, each with a benign twin, plus 2,000 normal cases, 3,760 in all. 571 are in the practice split and 3,189 in the official split. A 20-case seed file is separate.
- Deployment cards extracted from system messages, and a card track (`run --track card`).
- Pair score: each attack scored with its benign twin, strict and lenient.
- Reliability track: consistency, stability, load, long inputs, and failure behaviour.
- Sector tag on every v1 case, with per-sector counts.
- v2 case set: 488 attack pairs (140 policy pairs) and 938 normal cases. 313 cases are public in `cases/practice/v2.jsonl` (88 pairs, 137 normal cases) and 1,601 are in the hidden official split (400 pairs, 801 normal cases). Model-drafted, machine-checked and blind-reviewed by a different model. No human review. See `docs/reference/cases-v2.md` and the v2 section of `docs/case-review-log.md`.
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
- Policy pairs: a fifth `twin_change` value, `policy`. The attack and its twin have identical messages and differ only in one field of the deployment card (`allowed_tools`, `allowed_destinations`, `user_role` or `rules`), so only a product that uses the card can tell them apart. `validate`, `casegen` (drafts may leave out the benign side; blind review shows the card) and the case-writing guide cover them. The v1 case files are unchanged and hold none.
- `report.json`: a `twin_change` breakdown next to family, checkpoint, transform and sector, and a `card_only_pairs` count. `vendor-report.json` has the same count.
- `.pre-commit-config.yaml` (ruff, end-of-file and trailing-whitespace hooks) and a minimal `[tool.ruff]` setting in `pyproject.toml`. `ruff` is part of the `dev` extra.

### Changed

- Scoring of policy pairs: on the no-context track and the reliability track they are left out of every number and only counted ("card-only pairs, not scoreable without a card"); on the card track they count like any pair. No number changes for a case set without policy pairs, and a test pins the practice split's report to its earlier bytes.
- `casegen lint` also checks deployment cards for real-world domains.
- Submitted results keep their per-case log in this repository, as `results/<product>/<split>/log.jsonl.gz`. There is no separate results repository.
- The README follows the layout of other benchmark projects: links row, news, overview, set up, usage, downloads, contributions. The long tables (case counts, reliability keys) moved to `docs/reference/` and `docs/guides/`.
- The design documents moved to `docs/design/` (`guardrailbench-design.md`, `measurement-design.md`, `followups.md`) and are written as project design documents.
- Official rounds are opt-in. A product enters a round only when its maker asks: a participation request, a public adapter in this repository, and a way for the maintainers to run the product. The maintainers do not test a product uninvited. `GOVERNANCE.md` and `docs/official-runs.md` state the rule.
- One name for each thing across the README, the docs and the site: practice split, official split, official round, benign twin, normal case, deployment card, pair score.
- The package version in `pyproject.toml` is `1.0.0rc1`, to match this changelog and `CITATION.cff`. It was `0.1.0`.
- The pull request template has two checklists, one for code and adapter changes and one for practice result submissions.
- `run --track card` no longer loads a product's models when the product takes no card and every row will be "not applicable".
- The official split is now the v2 official split (1,601 cases). `cases/OFFICIAL_SHA256` holds its fingerprint. The v1 official split (3,189 cases) is withdrawn from official use and held in reserve, unpublished: it was used for internal harness testing before any round, so it is not used for scoring. The v1 practice split stays public. `guardrailbench validate cases/practice` now prints `904 cases, 0 problems`.

### Fixed

- The `llm-guard` adapter crashed on load: it read `Secrets.REDACT_PARTIAL`, which does not exist in llm-guard 0.3.16. It now uses the scanner's default redaction. The adapter has still not been run end to end.

### Removed

- Internal task plans, which were never part of the public docs.

### Known limitations

- No case has had human review, so there is no "Verified" subset.
- No results are published.
- Non-English cases have had no native-speaker check.

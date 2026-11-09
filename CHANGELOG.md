# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased] - 1.0.0-rc1

### Added

- Harness: `validate`, `run`, `score`, `leaderboard`, `hash`, `verify-submission`, and `casegen lint`.
- 13 adapters: the fake baseline plus Azure Prompt Shields, AWS Bedrock Guardrails, Google Model Armor, OpenAI Moderation, Lakera Guard, Llama Guard, Prompt Guard / Hugging Face classifiers, LlamaFirewall, NeMo Guardrails, LLM Guard, and Invariant Guardrails.
- v1 cases: 880 attack cases, each with a benign twin, plus 2000 standalone benign cases. 571 are in the public practice split. The rest are the hidden official split.
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
- `docs/official-runs.md`: which tests are open and which only maintainers run, how a round works, and the known weak points.
- `.pre-commit-config.yaml` (ruff, end-of-file and trailing-whitespace hooks) and a minimal `[tool.ruff]` setting in `pyproject.toml`. `ruff` is part of the `dev` extra.

### Changed

- The README follows the layout of other benchmark projects: links row, news, overview, set up, usage, downloads, contributions. The long tables (case counts, reliability keys) moved to `docs/reference/` and `docs/guides/`.
- The design documents moved to `docs/design/` (`guardrailbench-design.md`, `measurement-design.md`, `followups.md`) and are written as project design documents.

- `run --track card` no longer loads a product's models when the product takes no card and every row will be "not applicable".

### Removed

- Internal task plans, which were never part of the public docs.

### Known limitations

- Human review of the cases ("Verified" subset) is pending.
- No public leaderboard results yet.
- Non-English cases have had no native-speaker check.

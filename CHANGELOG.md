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

### Known limitations

- Human review of the cases ("Verified" subset) is pending.
- No public leaderboard results yet.
- Non-English cases have had no native-speaker check.

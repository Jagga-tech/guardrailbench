# v1 follow-ups

Things found in review that are known and left for later. Each one says when it has to be done.

## Before any official run

- **Invariant warmup.** `warmup()` only builds the policy. The detector models still load on the first `analyze_pending` call, which can time out. Make `warmup()` run one dummy analyze, and check it in a throwaway venv with `invariant-ai` installed.
- **Gated model cards.** Accept the Meta licence (Prompt Guard 2, Llama Guard 4) and the Qualifire licence on Hugging Face. Then confirm the items marked UNVERIFIED in `adapters/hf_classifier.py` and `adapters/llama_guard.py`: the PG2 label names, the PG2-22M scope, the Qualifire labels and max length, and the Llama Guard 4 assistant-turn template.
- **Cloud APIs.** Using real credentials, confirm the items marked UNVERIFIED:
  - Bedrock: that `guard_content` triggers the prompt-attack filter.
  - Azure: that an empty `userPrompt` is accepted.
  - Lakera: the project is in Enforce mode, and the tool content format works.
  - Model Armor: its default confidence level.
- **Version pinning.** Record the exact `transformers`, `torch`, `boto3` and `google-auth` versions used, inside each result's `version`.
- **Human review.** The owner's human review pass that creates the "Verified" subset.
- **Card sample check.** The owner's human check of the 10% deployment-card sample (296 sides).
- **Card support in adapters.** Spec build step 5: public policy-capable adapters need to take the card (Invariant allow-lists, Lakera projects, Bedrock denied topics, NeMo rails, Azure task adherence). None sets `accepts_card` yet, so they show "not applicable" in the card track. Do this before any public card-track round.
- **Backup.** An encrypted off-machine backup of `cases/official/` and `drafts/`.
- **Public-data check.** An outside check against public datasets for copied text.
- **Non-English cases.** A native-speaker check.
- **Invented company names.** A web check for collisions with real companies.

## Not yet implemented (spec §2)

- **Late-judge credit.** A product that rules after the fact and freezes the agent should get credit if the harmful step of a multi-step case is stopped. Deferred: no adapter reports late rulings yet.
- **Fail-mode counting.** Errors and timeouts are not yet counted by the product's fail mode (open or closed).
- **Unsure mapping.** Adapters should declare which raw verdicts map to "unsure".

## Small

- `run._jsonable` should use `allow_nan=False`, so a NaN inside `raw` drops `raw` and not the whole verdict.
- Spot-check scores are compared at an exact 1e-6 tolerance. GPU non-determinism on local models may need a looser tolerance.
- If `warmup()` fails, the run stops before writing anything. Mention this in the README.

## After v1

- **Top up short quota rows (v1.1).** F1 prompt, F2 ingested, F3 ingested, F5 output, F5 trajectory, F6 tool_definition, F7 trajectory and F10 prompt are under quota. See `docs/case-review-log.md`.
- **Lint false positives.** The URL host regex includes a trailing sentence period. The email regex matches `pkg@1.2.3`. Dotted code identifiers like `pytest.fixture` are flagged as domains.
- **Trajectory marker separation (v2).** Trajectory and memory attacks repeat the injected text in the final call's arguments, because the validator needs the marker in the judged message. Separate the marker from the payload step.

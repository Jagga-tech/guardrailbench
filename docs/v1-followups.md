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

## Before trajectory or policy cases are written

- **Native trajectory sanitize credit.** This currently uses the first sanitize step. It should use the step whose target is the marker message, in both `metrics.effective_block` and `run._decide`.

## Small

- `run._jsonable` should use `allow_nan=False`, so a NaN inside `raw` drops `raw` and not the whole verdict.
- Spot-check scores are compared at an exact 1e-6 tolerance. GPU non-determinism on local models may need a looser tolerance.
- If `warmup()` fails, the run stops before writing anything. Mention this in the README.

# Installation

You need Python 3.11 or newer. The harness itself has no dependencies. Adapters for some products need extra packages, listed below.

## With uv (recommended)

[uv](https://docs.astral.sh/uv/) is what the project's own checks use.

```
git clone https://github.com/Jagga-tech/guardrailbench
cd guardrailbench
uv sync --extra dev
uv run guardrailbench validate cases/practice
```

The last command should print `904 cases, 0 problems`: the 571 cases of v1 practice, the 313 cases of v2 practice and the 20 seed cases. In the rest of the docs, commands are written as `guardrailbench ...`. With uv, put `uv run` in front.

## With pip

```
git clone https://github.com/Jagga-tech/guardrailbench
cd guardrailbench
pip install -e .
guardrailbench validate cases/practice
```

## Optional extras

Install an extra only for the product you want to run. Each one is a name in `pyproject.toml`.

| Extra | Installs | For adapters |
|---|---|---|
| `dev` | pytest, ruff | running the tests and the linter |
| `hf` | transformers, torch | `prompt-guard-2-22m`, `prompt-guard-2-86m`, `protectai-deberta-v2`, `qualifire-sentinel`, `llama-guard-4` |
| `llamafirewall` | llamafirewall | `llamafirewall` |
| `nemo` | nemoguardrails | `nemo-guardrails` |
| `llmguard` | llm-guard | `llm-guard` |
| `invariant` | invariant-ai | `invariant` |
| `bedrock` | boto3 | `bedrock-guardrails` |
| `modelarmor` | google-auth, requests | `model-armor` |

Example: `uv sync --extra dev --extra bedrock`, or `pip install -e ".[bedrock]"`.

The hosted-API adapters (`azure-prompt-shields`, `lakera-guard`, `openai-moderation`) need no extra package, only your own keys. Nor do `llm-judge`, the reference baseline, and `fake`, the test double. Each adapter's module docstring in `src/guardrailbench/adapters/` lists the environment variables it reads, the documentation pages it relies on, and anything marked `UNVERIFIED`.

## Check the install

```
guardrailbench run --product fake --cases cases/practice --out runs/fake/practice.jsonl
guardrailbench score --results runs/fake/practice.jsonl --cases cases/practice --out results/fake/practice/report.json
```

The `fake` product is a test double that allows everything. It checks the plumbing, not detection, so every attack counts as a miss. Do not commit the `fake` report.

## Run the tests

The tests need the `dev` extra: `uv sync --extra dev` as above, or `pip install -e ".[dev]"`.

```
uv run pytest -q
uv run ruff check .
uv run guardrailbench casegen lint cases/practice/v1.jsonl
```

With pip, drop `uv run`.

Next: [run a product](guides/run-a-product.md).

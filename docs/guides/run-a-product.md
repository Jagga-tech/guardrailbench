# Run a product

This walks through one full run of a product on the public practice split. Install first: [installation](../installation.md).

## 1. Pick the product

```
guardrailbench run --product nope --cases cases/practice --out /tmp/x.jsonl
```

An unknown name exits with code 2 and prints the 16 registered names. Fourteen are adapters for guardrail products: `azure-prompt-shields`, `bedrock-guardrails`, `invariant`, `lakera-guard`, `llama-guard-4`, `llamafirewall`, `llm-guard`, `model-armor`, `nemo-guardrails`, `openai-moderation`, `prompt-guard-2-22m`, `prompt-guard-2-86m`, `protectai-deberta-v2`, `qualifire-sentinel`. The other two are not products: `llm-judge` is a reference baseline and `fake` is a test double that allows everything. If your product is not on the list, [write an adapter](write-an-adapter.md).

Set up the product with its defaults and your own keys. Read the module docstring of its adapter first. Do not tune thresholds or settings to the cases.

## 2. Check the cases

```
guardrailbench validate cases/practice
```

## 3. Run

```
guardrailbench run --product fake --cases cases/practice --out runs/fake/practice.jsonl
```

Replace `fake` with your product. Useful flags: `--workers` (parallel calls, default 4), `--timeout` (seconds per call, default 30). If the run stops, run the same command again: finished cases are skipped. Keep one output file per product, version and track, because a file that holds anything else is refused.

Each line of the output records the decision, the mode (`native`, `flattened`, `not_claimed`), the logs of every step, the product version and the time. Models load once before the run starts, outside the per-call timeout.

## 4. Score

```
guardrailbench score --results runs/fake/practice.jsonl --cases cases/practice --out results/fake/practice/report.json
```

The report is explained in [metrics](../reference/metrics.md).

## 5. Optional: card track

```
guardrailbench run --product NAME --cases cases/practice --out runs/NAME/practice-card.jsonl --track card
guardrailbench score --results runs/NAME/practice-card.jsonl --cases cases/practice --out results/NAME/practice-card/report.json
```

Products that accept a policy get each case's deployment card. Others get `not_applicable` rows. Keep card results in their own files and folders.

## 6. Optional: reliability

See [reliability](reliability.md).

## 7. See it on a page

```
guardrailbench leaderboard --results results --out site
```

Open `site/index.html`. To put your result on the public leaderboard, follow [submit results](submit.md).

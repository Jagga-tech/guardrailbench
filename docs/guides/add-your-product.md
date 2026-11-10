# Add your product

This is the path for a company that makes a guardrail and wants it in GuardrailBench. It takes about an hour and needs no help from the maintainers. You write one small file, run the public practice cases on your own machine, and send the results.

## What your product needs to expose

- A way to ask "should this go ahead?" from a script: an HTTP endpoint, an SDK or a local library.
- An answer that maps to allow or block. If the product can also say "needs review", "challenge" or "escalate", that is recorded as `unsure`.
- A key or test account for the run. You use your own, on your own machine.
- Documentation that says what the product inspects: user messages, tool calls, tool results, tool definitions, agent output. This decides which checkpoints it is tested on natively.
- Optional: a documented way to give the product a policy for the agent (its job, allowed tools, allowed destinations, rules). With it, the product can also run on the card track.

## What we will never ask for

- Source code.
- Model weights.
- Customer data, logs or traffic.
- Money. There is no fee to be tested or listed.

The adapter you write calls the product the way a customer would. That is all the benchmark sees.

## The steps

Commands are written for [uv](https://docs.astral.sh/uv/). With pip, run `pip install -e .` once and drop `uv run`. See [installation](../installation.md).

### 1. Install (5 minutes)

```
git clone https://github.com/Jagga-tech/guardrailbench
cd guardrailbench
uv sync
uv run guardrailbench validate cases/practice
```

The last command should print `591 cases, 0 problems`.

### 2. Copy the template (1 minute)

```
cp examples/adapter_template.py my_adapter.py
```

The file can live anywhere Python can import it. You do not need to change anything inside the repository.

### 3. Fill it in (30 minutes)

Open `my_adapter.py`. Every place to change is marked `EDIT`. In order:

1. `DECISIONS`: your product's answers, mapped to `allow`, `block` or `unsure`.
2. `build_policy`: the deployment card turned into your policy format. Skip it if the product takes no policy, and set `accepts_card = False`.
3. `build_request`: the request body for a conversation, for a tool definition, and for plain text.
4. `parse_response`: where the answer and the score sit in your response.
5. The class attributes: the product name, the checkpoints it inspects natively, `accepts_text`, `accepts_card`, `fail_mode`.
6. `__init__`: the endpoint, the key and the version.

The rules are short: send only what your documentation says the product inspects, use the default configuration, and tune nothing to the cases. They are listed in [write an adapter](write-an-adapter.md), with the full interface.

Then tell the harness where the adapter is. The template reads these three variables; change the names if you changed them in the file.

```
export PYTHONPATH=. GUARDRAILBENCH_PLUGINS=my_adapter
export MY_PRODUCT_URL=https://guard.example.com/v1/check
export MY_PRODUCT_API_KEY=your-key
export MY_PRODUCT_VERSION=1.4.2
uv run python -c "from guardrailbench.adapters import ADAPTERS; print('my-product' in ADAPTERS)"
```

It should print `True`.

### 4. Smoke-test on 20 cases (2 minutes)

`run` has no flag to limit the number of cases. Point it at the seed file instead, which holds 20 cases (10 attacks and their twins) across five checkpoints:

```
uv run guardrailbench run --product my-product --cases cases/practice/seed.jsonl --out runs/my-product/smoke.jsonl
uv run python -c "import json, collections; print(collections.Counter(json.loads(l)['decision'] for l in open('runs/my-product/smoke.jsonl')))"
```

You should see a mix of `allow`, `block` and perhaps `unsure`. If you see `error`, the reason is in the `error` field of each row in `runs/my-product/smoke.jsonl`. Fix the adapter, delete the file and run again. Everything under `runs/` is git-ignored.

### 5. Run the practice split (10 minutes, depending on your product's speed)

```
uv run guardrailbench run --product my-product --cases cases/practice --out runs/my-product/practice.jsonl
```

This sends 591 cases, four at a time (`--workers` changes that). Multi-step cases are sent once per step, so the number of calls is a little higher. If the run stops, run the same command again and it carries on where it stopped.

### 6. Score

```
uv run guardrailbench score --results runs/my-product/practice.jsonl --cases cases/practice --out results/my-product/practice/report.json
uv run python -c "import json; print(json.load(open('results/my-product/practice/report.json'))['native']['all']['pairs']['strict'])"
```

The second command prints the headline: how many attack and twin pairs the product got right, with a 95% interval. Every field of the report is explained in [metrics](../reference/metrics.md).

To read the same run as tables by checkpoint, attack family, sector and outcome, and to see what the report from an official round looks like:

```
uv run guardrailbench vendor-report --results runs/my-product/practice.jsonl --cases cases/practice --out runs/my-product/breakdown
```

Open `runs/my-product/breakdown/vendor-report.md`. To look at single cases, read `runs/my-product/practice.jsonl`: each row has the `case_id`, the `decision` and your product's raw response.

### 7. Check the results file

```
uv run guardrailbench verify-submission --results runs/my-product/practice.jsonl --cases cases/practice
```

It prints nothing and exits with 0 when the file is complete: one row per case, valid decisions, logs in every row. Maintainers run the same check.

### 8. Card track (optional)

Only if the adapter sets `accepts_card = True`:

```
uv run guardrailbench run --product my-product --cases cases/practice --out runs/my-product/practice-card.jsonl --track card
uv run guardrailbench score --results runs/my-product/practice-card.jsonl --cases cases/practice --out results/my-product/practice-card/report.json
```

Each case now arrives with its deployment card. Comparing this report with the one from step 6 shows what the policy is worth to your product.

### 9. Reliability (optional)

```
uv run guardrailbench reliability --product my-product --cases cases/practice --out runs/my-product/reliability
```

This repeats every case three times, sends reworded copies, and tests load and long inputs, so it makes several thousand calls. `--no-load` and `--no-long` skip the two heaviest parts. What it measures is in [the reliability guide](reliability.md). Consistency and stability numbers you measure yourself are shown as self-reported. Load and latency are only published from maintainer runs.

### 10. Send the results

Follow [submit results](submit.md): add a `meta.json`, and open a pull request with the reports and the per-case logs. The separate submissions repository is not open yet, so for now results go by pull request to this repository. They appear on the practice tab, marked self-reported, until a maintainer re-runs a sample.

To have the adapter itself added, so that maintainers can run your product in official rounds, open a second pull request that puts the file in `src/guardrailbench/adapters/` with an offline test. `tests/test_adapter_template.py` shows one way to write that test.

## Official rounds

Results on the practice split are yours to produce. Official results are not: maintainers run the hidden split on their own infrastructure, through the public adapter, and no vendor receives those cases before or during a round.

You are told before a round that your product is in it, and you can fix the adapter beforehand. After the run and before anything is published, you get a report with your numbers, the breakdowns, and the ids of practice cases that show the same kinds of failure. The round's cases are published when the split is retired. The whole process, including how to dispute a result, is in [official runs](../official-runs.md#what-a-vendor-is-told).

# Write an adapter

An adapter turns one case into a product's own API request and the response into a verdict. It is a small Python class with a few attributes and one method.

## The interface

From `guardrailbench.verdict`:

```python
from guardrailbench.verdict import Verdict


class MyAdapter:
    name = "my-product"                         # the name used with --product
    version = "1.2.3@2026-11-09"                # recorded in every result row
    native_checkpoints = frozenset({"prompt"})  # checkpoints the product inspects natively
    accepts_text = True                         # can it take plain text for other checkpoints?

    def judge(self, messages, target, mode):
        ...
        return Verdict("block", score=0.97, raw={})
```

- `messages` is the conversation in OpenAI chat format and `target` the index of the message to judge. `mode` is `"native"` or `"flattened"`. See [the case format](../reference/case-format.md).
- Return a `Verdict(decision, score=None, sanitized=None, raw={}, latency_ms=0.0, error=None)`. `decision` is `allow`, `block`, `sanitize`, `unsure` or `error`. Return `unsure` when the product abstains. A `sanitize` must carry the rewritten text in `sanitized`.
- Raise `Retryable` (from `guardrailbench.verdict`) for 429 or 5xx style failures. The run loop retries up to three times with backoff. Any other exception becomes an `error` row.
- Optional attributes: `accepts_card = True` to receive `card=<deployment card>` on the card track; `fail_mode = "open"` or `"closed"` for how the product behaves on errors; `warmup()` to load models once before the run.

How the run decides the mode: a case whose checkpoint is in `native_checkpoints` is sent with `mode="native"`. Otherwise it is sent flattened if `accepts_text` is true (use `guardrailbench.flatten.to_text(messages, target)`), and recorded as `not_claimed` if not. See [metrics](../reference/metrics.md).

## Rules

These are the same as in [CONTRIBUTING.md](../../CONTRIBUTING.md).

- Send only fields the product's documentation says it inspects. Do not decode or clean the input first.
- Use library or API defaults. No tuning, and no thresholds chosen to help the product.
- Cite the documentation pages you relied on in the adapter's module docstring and in the pull request.
- State the capability sheet: which checkpoints the product supports natively.
- Mark any claim you could not verify as `UNVERIFIED` in a comment and in the pull request.
- Keep the file small. Extra dependencies go in an optional extra in `pyproject.toml`, and heavy imports happen lazily.
- Add a test that runs without network access or keys. The cloud adapters take an injectable `opener` for this; see `tests/adapters/test_cloud_adapters.py`.

## Register it

Built-in adapters call `register` at import time:

```python
from guardrailbench.adapters import register

register("my-product")(MyAdapter)
```

and are imported from `src/guardrailbench/adapters/__init__.py`. The file `src/guardrailbench/adapters/openai_moderation.py` is a short complete example, and `fake.py` is the smallest.

## A private adapter

You do not need to change the repository to run an adapter of your own. Put it in any importable module, call `register` in it, and name the module in `GUARDRAILBENCH_PLUGINS`:

```
PYTHONPATH=. GUARDRAILBENCH_PLUGINS=my_private_adapter \
  guardrailbench run --product my-product --cases cases/practice --out runs/my-product/practice.jsonl
```

Several modules can be given, separated by commas. Each is imported after the built-in adapters. Set the same variable when you use `verify-submission --rerun`.

## Open a pull request

To add the adapter to the repository, open a pull request and sign off your commits (`git commit -s`). If you want to discuss it first, use the "New adapter" issue template.

# Contributing

This page covers setup, the kinds of contribution the project takes, and what it does not take.

By taking part you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Set up

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/Jagga-tech/guardrailbench
cd guardrailbench
uv sync --extra dev
```

Run the checks before every pull request:

```
uv run pytest -q
uv run guardrailbench validate cases/practice
uv run guardrailbench casegen lint cases/practice/v1.jsonl
```

Optional: after installing [pre-commit](https://pre-commit.com/), `pre-commit install` runs ruff and basic whitespace checks on each commit (see `.pre-commit-config.yaml`). The user docs start at [docs/index.md](docs/index.md), and the design documents are in [docs/design/](docs/design/guardrailbench-design.md).

## Contribute an adapter

An adapter turns one case into a product's own API request and the response into a verdict. To add your own product, start from `examples/adapter_template.py` and follow [docs/guides/add-your-product.md](docs/guides/add-your-product.md). Rules:

- Send only fields the product's documentation says it inspects. Do not decode or clean the input first.
- Use the library or API defaults. No tuning, no custom thresholds chosen to help the product.
- Cite the documentation pages you relied on, in the adapter file and in the pull request.
- Include a capability sheet: which checkpoints the product supports natively. Anything else is flattened or "not claimed".
- Mark any claim you could not verify as `UNVERIFIED` in a comment and in the pull request.
- Keep the file small. Extra dependencies go in an optional extra in `pyproject.toml`.
- Add a test that runs without network access or keys.

## Report a bad or mislabelled practice case

Open an issue with the "Case report" template. Give the case id, what is wrong (label, realism, twin mismatch, marker), and why. Do not paste working attacks against real products. Reports on the official split cannot be accepted, because its contents cannot be discussed.

## Submit results

- Run the **practice split** with your own keys and compute. The steps are in [docs/guides/submit.md](docs/guides/submit.md).
- Open a pull request with the report and the full per-case log. Logs are required.
- If you ran more than once, submit every attempt, not only the best.
- Maintainers check the log and merge. Practice results are shown on the "Practice (self-reported)" tab, marked self-reported.
- Check a submission yourself with `guardrailbench verify-submission`.

## Ask for an official round

The official tabs show only results from the maintainers' closed test on the official split. A product enters a round only when its maker asks, and the maintainers do not test a product uninvited. If you make the product, open a [participation request](https://github.com/Jagga-tech/guardrailbench/issues/new?template=participation.yml). You also need a public adapter in this repository and a way for the maintainers to run the product. Never post a key in an issue or a pull request. The policy is in [docs/official-runs.md](docs/official-runs.md).

## What is not accepted

- Requests for official-split cases, hints about them, or access to them.
- Requests to put someone else's product in an official round. Only its maker can ask.
- Vendor-tuned configurations in the default track. Tuned setups may be reported separately, labelled as tuned.
- Cases copied from public datasets. Cases are written fresh.
- Working harmful payloads (malware, real weapons information) in cases.
- Public posts of working attacks against third-party products. See [SECURITY.md](SECURITY.md).

## Commits and pull requests

- One logical change per commit. Short imperative subject, such as `fix: reliability rerun count`. Prefixes used here: `feat`, `fix`, `docs`, `test`, `chore`.
- Keep pull requests small and explain why, not only what.
- Sign off every commit under the [Developer Certificate of Origin](https://developercertificate.org/): `git commit -s`. This adds a `Signed-off-by:` line.
- Contributions to code are under Apache-2.0. Contributions to cases and docs are under CC BY 4.0.

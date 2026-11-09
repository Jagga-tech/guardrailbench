# Contributing

Thanks for helping. This page covers setup, the kinds of contribution we take, and what we do not take.

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

An adapter turns one case into a product's own API request and the response into a verdict. Rules:

- Send only fields the product's documentation says it inspects. Do not decode or clean the input first.
- Use the library or API defaults. No tuning, no custom thresholds chosen to help the product.
- Cite the documentation pages you relied on, in the adapter file and in the pull request.
- Include a capability sheet: which checkpoints the product supports natively. Anything else is flattened or "not claimed".
- Mark any claim you could not verify as `UNVERIFIED` in a comment and in the pull request.
- Keep the file small. Extra dependencies go in an optional extra in `pyproject.toml`.
- Add a test that runs without network access or keys.

## Report a bad or mislabelled practice case

Open an issue with the "Case report" template. Give the case id, what is wrong (label, realism, twin mismatch, marker), and why. Do not paste working attacks against real products. Reports on the hidden official split cannot be accepted, because we cannot discuss its contents.

## Submit results

- Run the **practice split** with your own keys and compute. The steps are in [docs/guides/submit.md](docs/guides/submit.md).
- Open a pull request with the per-case logs (the `runs/` output) and the report. Logs are required.
- If you ran more than once, submit every attempt, not only the best.
- Practice-split results go on the **unverified tier**, clearly labelled.
- Official-split runs are done only by maintainers. A result becomes "verified" after maintainers re-run a random sample.
- You can check a submission with `guardrailbench verify-submission`.

## What we do not accept

- Requests for hidden-split cases, hints about them, or access to them.
- Vendor-tuned configurations in the default track. Tuned setups may be reported separately, labelled as tuned.
- Cases copied from public datasets. Cases are written fresh.
- Working harmful payloads (malware, real weapons information) in cases.
- Public posts of working attacks against third-party products. See [SECURITY.md](SECURITY.md).

## Commits and pull requests

- One logical change per commit. Short imperative subject, such as `fix: reliability rerun count`. Prefixes used here: `feat`, `fix`, `docs`, `test`, `chore`.
- Keep pull requests small and explain why, not only what.
- Sign off every commit under the [Developer Certificate of Origin](https://developercertificate.org/): `git commit -s`. This adds a `Signed-off-by:` line.
- Contributions to code are under Apache-2.0. Contributions to cases and docs are under CC BY 4.0.

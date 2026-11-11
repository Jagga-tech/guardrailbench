## What and why

<!-- Say which kind of pull request this is and delete the checklist that does not apply. -->

## A. Code, adapter, docs or case change

- [ ] `uv run --extra dev pytest -q` passes
- [ ] `uv run guardrailbench validate cases/practice` passes
- [ ] `uv run guardrailbench casegen lint cases/practice/v1.jsonl` passes
- [ ] No official-split content or drafts included
- [ ] For adapters: docs cited, defaults only, capability sheet, UNVERIFIED claims marked, a test that needs no network or keys
- [ ] Commits are signed off (`git commit -s`)

## B. Practice result submission

Steps are in [submit results](https://github.com/Jagga-tech/guardrailbench/blob/main/docs/guides/submit.md).

- Product and version:
- Who ran it (`run_by`):
- Configuration: defaults / tuned (say what was changed)

- [ ] The run is on the practice split (`cases/practice`), with the product's defaults unless labelled as tuned
- [ ] `results/<product>/practice/report.json` and `meta.json` are in this pull request, and `verified` is not set
- [ ] The full per-case log is in this pull request as `results/<product>/practice/log.jsonl.gz`
- [ ] Every attempt is included, not only the best one
- [ ] `uv run guardrailbench verify-submission --results runs/<product>/practice.jsonl --cases cases/practice` prints nothing
- [ ] No key, password or token appears in the logs or in this pull request
- [ ] Commits are signed off (`git commit -s`)

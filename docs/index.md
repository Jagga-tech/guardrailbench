# GuardrailBench documentation

GuardrailBench is an open, vendor-neutral benchmark of AI-agent guardrail products. This page is the map of the docs. The project overview is in the [README](../README.md).

## Start here

- [Installation](installation.md)
- [Run a product](guides/run-a-product.md)
- [FAQ](faq.md)
- [Glossary](glossary.md): the terms the docs use, each with one meaning

## Take part

A maker of a guardrail product has two routes: send practice results by pull request ([submit results](guides/submit.md)), or ask for an official round with a [participation request](https://github.com/Jagga-tech/guardrailbench/issues/new?template=participation.yml) ([official rounds](official-runs.md#how-a-product-enters-a-round)). [Add your product](guides/add-your-product.md) covers both.

## Guides

- [Run a product](guides/run-a-product.md): validate, run, score, and build a page
- [Add your product](guides/add-your-product.md): the one-hour path for a guardrail company, from install to results
- [Write an adapter](guides/write-an-adapter.md): connect a product the harness does not know
- [Submit results](guides/submit.md): the practice route, from the run to the pull request, and what maintainers check
- [Reliability track](guides/reliability.md): consistency, stability, load, long inputs and failures
- [Official rounds](official-runs.md): the run policy. Which tests are open, how a product enters a round, and how a round works

## Reference

- [Case format](reference/case-format.md): fields, checkpoints, families, twins, deployment cards, sectors
- [Which products take a deployment card](reference/deployment-cards.md): the mechanism per product, and what was checked
- [Metrics](reference/metrics.md): decisions, strict and lenient, pair score, native and flattened
- [Command line](reference/cli.md): every command and flag
- [Cases in v1](reference/cases-v1.md): counts by family, checkpoint and sector, and known limitations
- [Leaderboard](reference/leaderboard.md): result folders, `meta.json` and the generated page

## Writing and reviewing cases

- [Case-writing guide](case-writing-guide.md)
- [Case review log](case-review-log.md): counts from each review stage

## Design

- [GuardrailBench design](design/guardrailbench-design.md): goals, scope, tracks, splits, governance
- [Measurement design](design/measurement-design.md): the deployment card, three outcomes, pair score, reliability
- [Follow-ups](design/followups.md): known open items, with when each is due

## Project

[CONTRIBUTING](../CONTRIBUTING.md), [GOVERNANCE](../GOVERNANCE.md), [SECURITY](../SECURITY.md), [CODE_OF_CONDUCT](../CODE_OF_CONDUCT.md), [CHANGELOG](../CHANGELOG.md).

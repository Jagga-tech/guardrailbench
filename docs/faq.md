# FAQ

## What is a benign twin?

Every attack case has a benign twin: a matched case that differs in exactly one thing, such as the same calendar invite with a real meeting note instead of a hidden instruction, or the same refund call from a user who is allowed to make it. The field `twin_change` names the one thing: `intent`, `role`, `destination`, `data_origin` or `policy`. See [case format](reference/case-format.md).

## Why a pair score?

Detection rate and false-block rate, reported apart, hide whether a product can tell an attack from ordinary work. A product that blocks everything gets perfect detection. The pair score counts an attack as correct only when the product stops it and lets its twin through. Blocking everything scores zero. See [metrics](reference/metrics.md).

## Why is the official split hidden?

Public test sets leak into training data and into vendors' tuning, so they stop measuring anything. The official split is held by the maintainers and run on their infrastructure. Before each round, the SHA-256 fingerprint of the frozen split is published in `cases/OFFICIAL_SHA256` (today that is the v2 official split), so anyone can later check that it was not changed once results came in. Every case also carries a canary string that shows if it leaks.

## Can vendors tune their product to the benchmark?

Not in the default track. Products run with library or API defaults, and an adapter may not choose thresholds to help a product. A tuned configuration may be reported separately, labelled as tuned. Vendors never receive the official split, and are asked to confirm they did not train on GuardrailBench cases. Please do not train on the cases.

## How are conflicts of interest handled?

Any maintainer affiliation with a vendor is disclosed on that vendor's row. An affiliated product runs through the same harness with no early access, and the affiliated maintainer steps out of decisions about it. See [GOVERNANCE.md](../GOVERNANCE.md).

## What is not measured?

- Whether an agent or model resists attacks. Other benchmarks do that.
- General content safety such as hate speech or self-harm.
- A single overall "best guardrail" rank. There is no composite score.
- Adaptive attackers. v1 uses a fixed set of cases written in advance, and a fixed set can be overturned by a stronger attacker.
- Real harmful payloads. Attacks point at fake environments and fake addresses.
- Native-speaker quality of non-English cases, which have not had that check.

A guardrail is one layer of defence, not a full security boundary.

## How do I add a product?

Write an adapter, a small class that turns a case into the product's API request and the response into a verdict. [Add your product](guides/add-your-product.md) is the one-hour path with a template to copy, and [write an adapter](guides/write-an-adapter.md) has the full interface. You can run a private adapter without changing the repository, or open a pull request to add it.

## How does a company take part?

There are two routes, and both are free.

- **Practice (open).** Run your own product on the public practice split and [submit the results](guides/submit.md) with full per-case logs by pull request. Maintainers check the logs and merge. The result is shown on the "Practice (self-reported)" tab, marked self-reported.
- **Official rounds (closed).** The official tabs show only results from the maintainers' closed test on the official split. Your product is in a round only if you ask: open a [participation request](https://github.com/Jagga-tech/guardrailbench/issues/new?template=participation.yml), have a public adapter in this repository, and give the maintainers a way to run the product. See [how a product enters a round](official-runs.md#how-a-product-enters-a-round).

## Will the maintainers test a product without being asked?

No. A product enters an official round only when its maker asks. An adapter in this repository lets anyone run that product on the practice split. It does not put the product in a round.

## How do I learn what my product got wrong in an official round?

Before results are published you get a report on your own product. It gives the numbers by checkpoint, attack family, sector and outcome, and for each weak group it names public practice cases your product got wrong in the same way, so you can reproduce the failure. It does not show hidden cases. Those are published when the round's split is retired. See [what a vendor is told](official-runs.md#what-a-vendor-is-told).

## How often is the benchmark refreshed?

Each official round uses a fresh official split. When a round's results are published, its cases are published too and move to the practice split. No round has been run yet. The v2 case set was made for the first one: its official split is hidden and its practice share is public. The v1 official split is withdrawn from official use and held in reserve, unpublished: it was used for internal harness testing before any round, so it is not used for scoring. Changes that alter published scores are versioned and recorded in [the changelog](../CHANGELOG.md).

## What does "unsure" mean?

Some products return more than allow or block: a challenge, a flag for review, a decision left to a slower judge. GuardrailBench records that as `unsure`. Every number is shown two ways: strict (unsure counts as a stop, as a fail-closed deployment would) and lenient (unsure counts as a go). The unsure rate has its own column, so a product that is unsure about everything cannot look good under either reading.

## What is the card track?

In the no-context track a product gets the case and nothing else. In the card track it also gets the case's deployment card: the agent's job, its allowed tools and destinations, the user's role and the policy rules, taken from the case's system message. Products that accept a policy are configured from the card. Products that cannot take one show "not applicable", not zero. See [case format](reference/case-format.md).

## Why do some pairs only count on the card track?

Those are policy pairs. The attack and its twin have the same messages, word for word. What differs is one field of the deployment card: the allowed tools, the allowed destinations, the user's role or a rule. The action breaks one card and is allowed by the other.

A product that is not given the card gets the same input twice, so it must give the same answer twice. It cannot get the pair right, and counting its answer as a catch or a miss would be noise. On the no-context track these pairs are therefore left out of every number, and the report gives their count as "card-only pairs, not scoreable without a card". On the card track they count like any other pair and show whether a product uses the card it is given. v1 has no policy pairs. See [metrics](reference/metrics.md#policy-pairs).

## Which products can take a card?

Of the built-in adapters: NeMo Guardrails (the card goes into its self-check prompts), Invariant (the card's allowed tools become a rule) and LlamaFirewall (the card goes into the trace, which only its alignment check reads). The hosted APIs, the text classifiers, Llama Guard and LLM Guard have no documented way to take a per-case policy, so they show "not applicable". The full table, with what was checked, is in [which products take a deployment card](reference/deployment-cards.md).

## Why not just put the card in front of the text for every product?

Because that would test our prompt, not the product. A product gets the card only through a way its own documentation gives for policy or context. A classifier trained to spot injections has no such input, and pasting a policy in front of the text would change what it is classifying.

## What is llm-judge?

A reference baseline, not a product. It asks a general chat model whether to allow or block, with a short fixed prompt, and adds the card on the card track. Running it on both tracks with the same model shows what the card is worth to a reader that can use it. It carries a "baseline" badge on the leaderboard. See [which products take a deployment card](reference/deployment-cards.md#the-llm-judge-baseline).

## What does "not claimed" mean?

The product cannot represent that checkpoint, for example a text classifier given a tool call. It is not counted as a miss. The leaderboard says so plainly, because telling buyers which products cannot see tool calls is part of the point. If the product takes text, the case can still be run flattened, and flattened results are never mixed with native ones.

## How are cases made, and are they checked by people?

Cases are written fresh, never copied from public datasets. They are model-drafted, machine-checked and model cross-reviewed in two blind passes. No case has had human review, so no case is marked "Verified". See [the review log](case-review-log.md), [cases in v1](reference/cases-v1.md) and [cases in v2](reference/cases-v2.md).

## Can I post results?

Run the practice split and [submit it](guides/submit.md). It appears on the "Practice (self-reported)" tab. Please do not publish working attacks against third-party products. See [SECURITY.md](../SECURITY.md).

## How do I report a bad case?

Open an issue with the "Case report" template. Give the case id, what is wrong and why. Reports on the official split cannot be accepted, because its contents cannot be discussed.

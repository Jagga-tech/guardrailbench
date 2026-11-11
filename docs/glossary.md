# Glossary

The terms the docs use, each with one meaning. Links go to the page that has the detail.

**Adapter.** A small Python class that turns one case into a product's own API request and the response into a verdict. See [write an adapter](guides/write-an-adapter.md).

**Attack family.** One of ten kinds of attack, numbered F1 to F10. See [case format](reference/case-format.md#families).

**Baseline.** A reference point that is not a guardrail product. `llm-judge` is the only one. It carries a "baseline" badge on the leaderboard.

**Benign twin.** The matched case for an attack. It differs from the attack in exactly one thing and should be allowed. See [case format](reference/case-format.md#twins).

**Canary.** A unique `GRB-CANARY-` string in every case. It shows if the case leaks into training data.

**Card track.** The track in which a product also gets each case's deployment card. See [metrics](reference/metrics.md#tracks).

**Case.** One thing an agent is about to see or do, with a label of attack or benign. See [case format](reference/case-format.md).

**Checkpoint.** Where in an agent's run the guard sees the input. There are seven: `prompt`, `ingested_content`, `tool_definition`, `tool_call`, `memory_write`, `output` and `trajectory`.

**Deployment card.** A record of the agent's setup taken from a case's system message: its job, allowed tools, allowed destinations, the user's role and the rules. See [case format](reference/case-format.md#deployment-card).


**Flattened.** A case sent as plain text because the product cannot represent its checkpoint. Flattened results are never mixed with native ones. See [metrics](reference/metrics.md#native-and-flattened).

**Native.** A case sent in the form the product's API has for that checkpoint.

**No-context track.** The default track. The product gets the case and nothing else. The site also calls it the core track.

**Normal case.** A benign case that is not the twin of an attack. v1 has 2,000.

**Not applicable.** Shown on the card track for a product that cannot take a deployment card.

**Not claimed.** Shown for a checkpoint a product cannot represent and cannot take as text. It is not counted as a miss.

**Official round.** One closed test of the official split, run by the maintainers on the products whose makers asked to take part. See [official rounds](official-runs.md).

**Official split.** The cases used in official rounds. It is hidden: only its SHA-256 fingerprint is published before a round. v1 has 3,189.

**Pair.** An attack and its benign twin.

**Pair score.** The share of pairs where the product stops the attack and allows the twin. It is the headline number. See [metrics](reference/metrics.md#pair-score).

**Participation request.** The issue a maker opens to ask for its product to be in an official round. See [how a product enters a round](official-runs.md#how-a-product-enters-a-round).

**Practice split.** The public cases in `cases/practice/v1.jsonl`. Anyone can run them. v1 has 571.

**Reliability track.** Consistency, stability, speed under load, long inputs and failure behaviour. See [the reliability guide](guides/reliability.md).

**Sector.** One of 20 industry tags on a case, such as `finance` or `health`.

**Seed file.** `cases/practice/seed.jsonl`: 20 small cases (10 pairs) for smoke tests. They are not part of the v1 counts.

**Self-reported.** A practice result produced by the submitter, not by the maintainers. It is shown on the "Practice (self-reported)" tab.

**Strict and lenient.** Two readings of every rate. Strict counts `unsure` as a stop, lenient as a go. See [metrics](reference/metrics.md#strict-and-lenient).

**Test double.** `fake`, an adapter that allows everything. It checks the plumbing and is never a result.

**Unsure.** A product's answer that is neither allow nor block: a challenge, a flag for review, a decision left to a slower judge.

**Vendor.** The maker of a guardrail product. A participating vendor is one that has asked for an official round.

**Verified.** Used in two places. A verified case is one that has passed human review. A verified practice result is one where maintainers re-ran a random sample and the answers agreed.

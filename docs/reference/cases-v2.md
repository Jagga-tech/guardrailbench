# Cases in v2

Counts for the v2 case set. For the file format, see [case-format.md](case-format.md). The earlier set is in [cases-v1.md](cases-v1.md).

**Status.** v2 is the case set for the first official round. The practice share is public in `cases/practice/v2.jsonl` and `cases/practice/v2b.jsonl`. The official split is hidden. Its fingerprint is in `cases/OFFICIAL_SHA256`. No human has reviewed any v2 case.

v2 has 519 attack pairs (an attack and its benign twin) and 1,038 normal cases: 2,076 cases in all. 338 are in the practice split: 92 pairs (184 cases) and 154 normal cases. 1,738 are in the official split: 427 pairs (854 cases) and 884 normal cases. The v2 set was topped up on 2026-11-11 (see [Top-up](#top-up)). Its cases sit in two files: `v2.jsonl` (313 practice cases) and `v2b.jsonl` (25). The practice split as a whole is `v1.jsonl` (571) + `v2.jsonl` (313) + `v2b.jsonl` (25) + the 20-case seed file = 929 cases.

What v2 adds to v1:

- **Policy pairs.** The messages are identical and the deployment card alone decides which side is the attack. They are scored on the card track only. 140 of the 519 pairs are policy pairs (29 practice, 111 official).
- **Long-form attacks.** Attacks that are long, not only short injected lines.
- **Normal cases that share the attacks' surface features.** Normal cases with the same length, encodings, languages and machine-to-machine content, so that those features alone do not give an attack away.

Family codes: F1 direct injection and jailbreaks, F2 encoding and obfuscation, F3 indirect injection, F4 dangerous tool calls, F5 data exfiltration and leakage, F6 MCP and supply-chain poisoning, F7 agent-to-agent attacks, F8 memory poisoning, F9 resource abuse, F10 attacks on the guard itself.

## Counts

Attack pairs by family, with the practice / official split in brackets. Counts are pairs, not cases: an attack and its twin count once.

| Family | Attack pairs (practice / official) |
|---|---|
| F1 direct injection and jailbreaks | 28 (6 / 22) |
| F2 encoding and obfuscation | 34 (6 / 28) |
| F3 indirect injection | 95 (14 / 81) |
| F4 dangerous tool calls | 120 (24 / 96) |
| F5 data exfiltration and leakage | 85 (13 / 72) |
| F6 MCP and supply-chain poisoning | 29 (6 / 23) |
| F7 agent-to-agent attacks | 25 (5 / 20) |
| F8 memory poisoning | 27 (4 / 23) |
| F9 resource abuse | 55 (10 / 45) |
| F10 attacks on the guard itself | 21 (4 / 17) |
| **Total** | 519 (92 / 427) |

By checkpoint. Normal cases are the benign cases that are not a twin.

| Checkpoint | Attack pairs (practice / official) | Normal cases (practice / official) |
|---|---|---|
| prompt | 62 (12 / 50) | 212 (30 / 182) |
| ingested_content | 142 (23 / 119) | 344 (53 / 291) |
| tool_definition | 19 (4 / 15) | 47 (6 / 41) |
| tool_call | 182 (34 / 148) | 212 (27 / 185) |
| memory_write | 20 (2 / 18) | 47 (9 / 38) |
| output | 19 (3 / 16) | 70 (11 / 59) |
| trajectory | 75 (14 / 61) | 106 (18 / 88) |
| **Total** | 519 (92 / 427) | 1038 (154 / 884) |

By twin change (what differs between an attack and its twin). 6 practice pairs use an input transform (`transform` is set).

| Twin change | Pairs (practice / official) |
|---|---|
| intent | 298 (51 / 247) |
| role | 27 (2 / 25) |
| destination | 38 (5 / 33) |
| data_origin | 16 (5 / 11) |
| policy | 140 (29 / 111) |
| **Total** | 519 (92 / 427) |

## Policy pairs

In a policy pair the attack and its twin have identical messages. They differ in one field of the deployment card, and the target action breaks one card and is allowed by the other. See [case format](case-format.md#policy-pairs). In v2 they sit at two checkpoints:

| Checkpoint | Policy pairs (practice / official) |
|---|---|
| tool_call | 95 (20 / 75) |
| trajectory | 45 (9 / 36) |
| **Total** | 140 (29 / 111) |

A product that is not given the card sees the same input twice. These pairs are not scoreable on the no-context track or the reliability track. They are counted there as "card-only pairs" and left out of every number. On the card track they are scored like any pair. See [metrics](metrics.md#policy-pairs).

## Sectors

Every v2 case has a `sector`. Counts per sector (attack pairs count once, not per twin):

| Sector | Attack pairs (practice / official) | Normal cases (practice / official) |
|---|---|---|
| agriculture | 18 (4 / 14) | 47 (8 / 39) |
| education | 30 (6 / 24) | 57 (6 / 51) |
| energy_utilities | 29 (6 / 23) | 48 (5 / 43) |
| finance | 32 (4 / 28) | 59 (9 / 50) |
| general | 8 (4 / 4) | 51 (6 / 45) |
| government | 29 (1 / 28) | 56 (14 / 42) |
| health | 34 (6 / 28) | 59 (9 / 50) |
| hr | 27 (4 / 23) | 52 (10 / 42) |
| insurance | 30 (5 / 25) | 53 (6 / 47) |
| legal | 23 (6 / 17) | 53 (10 / 43) |
| logistics | 28 (8 / 20) | 54 (9 / 45) |
| manufacturing | 23 (2 / 21) | 48 (8 / 40) |
| media_marketing | 23 (4 / 19) | 48 (10 / 38) |
| nonprofit | 20 (6 / 14) | 44 (5 / 39) |
| real_estate_construction | 28 (6 / 22) | 48 (7 / 41) |
| research_science | 19 (2 / 17) | 46 (2 / 44) |
| retail | 33 (4 / 29) | 58 (6 / 52) |
| software_it | 34 (5 / 29) | 58 (10 / 48) |
| telecom | 23 (3 / 20) | 49 (7 / 42) |
| travel_hospitality | 28 (6 / 22) | 50 (7 / 43) |
| **Total** | 519 (92 / 427) | 1038 (154 / 884) |

Per-sector counts are small, especially in the practice split (for example government has one practice pair). Do not read a per-sector result as a stable measure on v2 alone.

## How the cases were made

- A model drafted the cases under [the case-writing guide](../case-writing-guide.md).
- Every case was machine-checked with `guardrailbench validate` and `guardrailbench casegen lint`.
- Every case was reviewed blind by a different model that saw no labels.
- Flagged cases were repaired once and reviewed blind again. Anything still flagged was dropped.

No human has reviewed any case. There is no "Verified" subset. Nine labelling rulings came out of the review. They are in [the guide](../case-writing-guide.md#labelling-rulings).

## Review numbers

Counts only. Per-stage detail is in [the review log](../case-review-log.md#v2-case-set). These are the numbers for the first drafting. The top-up has its own numbers below.

- 503 pairs and 938 normal cases were drafted.
- First blind pass: 1,944 items. The reviewer's label matched the intended label on 1,897 (97.6%).
- 150 drafts were sent to repair. 116 were fixed, 3 were dropped and 31 were left unchanged. 6 unflagged drafts were also fixed.
- Second blind pass: 281 items, of which 228 were repaired and 53 were decoys. 10 repaired drafts and 2 decoy drafts were still flagged and were dropped.
- 15 pairs were dropped in all. No normal case was dropped. 488 pairs and 938 normal cases remained.

## Top-up

On 2026-11-11 the v2 set got a top-up, before any product had been run on the official split.

**Why.** A crude surface probe (see below) could partly tell attacks from standalone normal cases by topic and shape, without reading the content. Injection cases sat mostly in short technical text that often mentions AI assistants. Normal fetched content was mostly everyday and often long. Attack trajectories ended in a short outbound call, while many normal ones ended in a text reply.

**What was added.**

- 32 injection pairs set in everyday, non-technical content, many of it long. 31 were kept.
- 64 normal technical cases. 34 of them carry a visible, harmless note to automated readers.
- 36 normal trajectories that end in an outbound or state-changing call.

That is 31 pairs and 100 normal cases, 162 cases in all: 25 in the practice split (4 pairs and 17 normal cases) and 137 in the official split (27 pairs and 83 normal cases). The totals above include them.

**Ids.** Top-up cases have ids that start with `v2b-` and `version` 2. They were assembled separately, so the published v2 practice cases kept their split. The practice ones are in `cases/practice/v2b.jsonl`.

**Review.** The top-up went through the same machine checks and a blind review by a different model. 164 items were reviewed blind, and the reviewer's label matched on 164 of 164. It raised 4 real-entity flags and 1 broken flag, and no ambiguous flags. 2 pairs had real public bodies replaced with invented ones. 1 pair (the broken one) was dropped. No human has reviewed any v2 case, the top-up included.

**Hash.** The official split gained the top-up, so the fingerprint in `cases/OFFICIAL_SHA256` changed. No product had been run on the official split before that. It changed once more the same day, when 31 v2 cards that left out a tool the case calls were corrected (3 practice, 28 official). See [the changelog](../../CHANGELOG.md).

## Surface-tell probe

`scripts/tell_probe.py`: a bag-of-words Naive Bayes classifier, 5-fold cross-validation, balanced accuracy (0.5 is chance). It was run over v1 practice, v2 practice and v2 official together, with policy pairs left out (their messages are identical, so there is nothing to separate). It is a crude check. It sees word presence only, and a low score does not show that the cases are free of giveaways.

| Run | Before top-up | After top-up |
|---|---|---|
| All cases | 0.613 | 0.545 |
| Twins only (attack vs its twin) | 0.570 | 0.571 |
| Attack vs normal cases, prompt | 0.573 | 0.573 |
| Attack vs normal cases, ingested_content | 0.714 | 0.566 |
| Attack vs normal cases, tool_call | 0.631 | 0.631 |
| Attack vs normal cases, output | 0.500 | 0.500 |
| Attack vs normal cases, memory_write | 0.579 | 0.579 |
| Attack vs normal cases, tool_definition | 0.508 | 0.508 |
| Attack vs normal cases, trajectory | 0.706 | 0.664 |

What moved: fetched content (ingested_content) fell from 0.71 to 0.57, all cases from 0.61 to 0.55, and trajectories from 0.71 to 0.66. What did not: tool calls stay at 0.63, and the other checkpoints did not change because the top-up added no cases there. Trajectories at 0.66 and tool calls at 0.63 are still above chance, so vocabulary alone still separates attacks from normal cases at those two checkpoints. Twins-only is low, so vocabulary alone does not say which side of a pair is the attack. The v1 figures in [cases-v1.md](cases-v1.md) came from a different run over v1 only, so they are not comparable with this table. Where the probe separates the classes, a false-positive rate measured on normal cases is an optimistic proxy for real traffic.

## Known limitations

- The cases were drafted by a model and reviewed by a different model. No human has reviewed them.
- Text written by language models can share a style. A product tuned to that style could do well here without being good on real traffic.
- Per-sector counts are small. See above.
- The tell-probe figures show that vocabulary alone still separates attacks from normal cases at some checkpoints, trajectory and tool_call in particular, even after the top-up. The probe is crude, and 0.5 is chance.
- The top-up was reviewed blind by a model only, like the rest of v2.
- Policy pairs cannot be scored without a card. A product that cannot take a card has none of the 140 policy pairs in its numbers.
- Non-English cases have had no native-speaker check.

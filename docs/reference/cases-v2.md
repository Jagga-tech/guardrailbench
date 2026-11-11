# Cases in v2

Counts for the v2 case set. For the file format, see [case-format.md](case-format.md). The earlier set is in [cases-v1.md](cases-v1.md).

**Status.** v2 is the case set for the first official round. The practice share is public in `cases/practice/v2.jsonl`. The official split is hidden. Its fingerprint is in `cases/OFFICIAL_SHA256`. No human has reviewed any v2 case.

v2 has 488 attack pairs (an attack and its benign twin) and 938 normal cases: 1,914 cases in all. 313 are in the practice split: 88 pairs (176 cases) and 137 normal cases. 1,601 are in the official split: 400 pairs (800 cases) and 801 normal cases. The practice split as a whole is `v1.jsonl` (571) + `v2.jsonl` (313) + the 20-case seed file = 904 cases.

What v2 adds to v1:

- **Policy pairs.** The messages are identical and the deployment card alone decides which side is the attack. They are scored on the card track only. 140 of the 488 pairs are policy pairs (29 practice, 111 official).
- **Long-form attacks.** Attacks that are long, not only short injected lines.
- **Normal cases that share the attacks' surface features.** Normal cases with the same length, encodings, languages and machine-to-machine content, so that those features alone do not give an attack away.

Family codes: F1 direct injection and jailbreaks, F2 encoding and obfuscation, F3 indirect injection, F4 dangerous tool calls, F5 data exfiltration and leakage, F6 MCP and supply-chain poisoning, F7 agent-to-agent attacks, F8 memory poisoning, F9 resource abuse, F10 attacks on the guard itself.

## Counts

Attack pairs by family, with the practice / official split in brackets. Counts are pairs, not cases: an attack and its twin count once.

| Family | Attack pairs (practice / official) |
|---|---|
| F1 direct injection and jailbreaks | 28 (6 / 22) |
| F2 encoding and obfuscation | 34 (6 / 28) |
| F3 indirect injection | 64 (10 / 54) |
| F4 dangerous tool calls | 120 (24 / 96) |
| F5 data exfiltration and leakage | 85 (13 / 72) |
| F6 MCP and supply-chain poisoning | 29 (6 / 23) |
| F7 agent-to-agent attacks | 25 (5 / 20) |
| F8 memory poisoning | 27 (4 / 23) |
| F9 resource abuse | 55 (10 / 45) |
| F10 attacks on the guard itself | 21 (4 / 17) |
| **Total** | 488 (88 / 400) |

By checkpoint. Normal cases are the benign cases that are not a twin.

| Checkpoint | Attack pairs (practice / official) | Normal cases (practice / official) |
|---|---|---|
| prompt | 62 (12 / 50) | 212 (30 / 182) |
| ingested_content | 111 (19 / 92) | 280 (42 / 238) |
| tool_definition | 19 (4 / 15) | 47 (6 / 41) |
| tool_call | 182 (34 / 148) | 212 (27 / 185) |
| memory_write | 20 (2 / 18) | 47 (9 / 38) |
| output | 19 (3 / 16) | 70 (11 / 59) |
| trajectory | 75 (14 / 61) | 70 (12 / 58) |
| **Total** | 488 (88 / 400) | 938 (137 / 801) |

By twin change (what differs between an attack and its twin). 6 practice pairs and 28 official pairs use an input transform (`transform` is set).

| Twin change | Pairs (practice / official) |
|---|---|
| intent | 267 (47 / 220) |
| role | 27 (2 / 25) |
| destination | 38 (5 / 33) |
| data_origin | 16 (5 / 11) |
| policy | 140 (29 / 111) |
| **Total** | 488 (88 / 400) |

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
| agriculture | 16 (4 / 12) | 43 (8 / 35) |
| education | 27 (6 / 21) | 52 (5 / 47) |
| energy_utilities | 27 (6 / 21) | 43 (4 / 39) |
| finance | 31 (4 / 27) | 53 (8 / 45) |
| general | 7 (3 / 4) | 46 (6 / 40) |
| government | 26 (1 / 25) | 51 (12 / 39) |
| health | 32 (6 / 26) | 53 (6 / 47) |
| hr | 27 (4 / 23) | 47 (9 / 38) |
| insurance | 27 (5 / 22) | 48 (5 / 43) |
| legal | 23 (6 / 17) | 48 (9 / 39) |
| logistics | 26 (7 / 19) | 49 (9 / 40) |
| manufacturing | 23 (2 / 21) | 43 (8 / 35) |
| media_marketing | 22 (4 / 18) | 43 (8 / 35) |
| nonprofit | 18 (5 / 13) | 40 (5 / 35) |
| real_estate_construction | 25 (6 / 19) | 43 (6 / 37) |
| research_science | 18 (2 / 16) | 42 (2 / 40) |
| retail | 30 (4 / 26) | 53 (4 / 49) |
| software_it | 34 (5 / 29) | 52 (10 / 42) |
| telecom | 23 (3 / 20) | 44 (6 / 38) |
| travel_hospitality | 26 (5 / 21) | 45 (7 / 38) |
| **Total** | 488 (88 / 400) | 938 (137 / 801) |

Per-sector counts are small, especially in the practice split (for example government has one practice pair). Do not read a per-sector result as a stable measure on v2 alone.

## How the cases were made

- A model drafted the cases under [the case-writing guide](../case-writing-guide.md).
- Every case was machine-checked with `guardrailbench validate` and `guardrailbench casegen lint`.
- Every case was reviewed blind by a different model that saw no labels.
- Flagged cases were repaired once and reviewed blind again. Anything still flagged was dropped.

No human has reviewed any case. There is no "Verified" subset. Nine labelling rulings came out of the review. They are in [the guide](../case-writing-guide.md#labelling-rulings).

## Review numbers

Counts only. Per-stage detail is in [the review log](../case-review-log.md#v2-case-set).

- 503 pairs and 938 normal cases were drafted.
- First blind pass: 1,944 items. The reviewer's label matched the intended label on 1,897 (97.6%).
- 150 drafts were sent to repair. 116 were fixed, 3 were dropped and 31 were left unchanged. 6 unflagged drafts were also fixed.
- Second blind pass: 281 items, of which 228 were repaired and 53 were decoys. 10 repaired drafts and 2 decoy drafts were still flagged and were dropped.
- 15 pairs were dropped in all. No normal case was dropped. 488 pairs and 938 normal cases remain.

## Surface-tell probe

`scripts/tell_probe.py`: a bag-of-words Naive Bayes classifier, 5-fold cross-validation, balanced accuracy (0.5 is chance). It was run over v1 practice, v2 practice and v2 official together, with policy pairs left out (their messages are identical, so there is nothing to separate).

| Run | Balanced accuracy |
|---|---|
| All cases | 0.613 |
| Twins only (attack vs its twin) | 0.570 |
| Attack vs normal cases, prompt | 0.573 |
| Attack vs normal cases, ingested_content | 0.714 |
| Attack vs normal cases, tool_call | 0.631 |
| Attack vs normal cases, output | 0.500 |
| Attack vs normal cases, memory_write | 0.579 |
| Attack vs normal cases, tool_definition | 0.508 |
| Attack vs normal cases, trajectory | 0.706 |

What this means: a classifier that sees only word presence tells attack from normal cases better than chance at ingested_content, trajectory and tool_call (0.63 to 0.71), and at about chance at output and tool_definition. Twins-only is lower, so vocabulary alone does not say which side of a pair is the attack. The v1 figures in [cases-v1.md](cases-v1.md) came from a different run over v1 only, so the two sets of numbers are not a before-and-after. Where the probe separates the classes, a false-positive rate measured on normal cases is an optimistic proxy for real traffic.

## Known limitations

- The cases were drafted by a model and reviewed by a different model. No human has reviewed them.
- Text written by language models can share a style. A product tuned to that style could do well here without being good on real traffic.
- Per-sector counts are small. See above.
- The tell-probe figures show that vocabulary alone separates attacks from normal cases at some checkpoints.
- Policy pairs cannot be scored without a card. A product that cannot take a card has none of the 140 policy pairs in its numbers.
- Non-English cases have had no native-speaker check.

# Cases in v1

Counts for the v1 case set. For the file format, see [case-format.md](case-format.md). The second case set is in [cases-v2.md](cases-v2.md).

**Status.** The v1 practice split stays public (`cases/practice/v1.jsonl`). The v1 official split (3,189 cases) is withdrawn from official use and held in reserve, unpublished: it was used for internal harness testing before any round, so it is not used for scoring. The first official round uses the v2 case set. `cases/OFFICIAL_SHA256` now holds the fingerprint of the v2 official split, not of the v1 one. It changed on 2026-11-11, when the official split gained the v2 top-up.

v1 has 880 attack cases, each with a benign twin, plus 2,000 normal cases: 3,760 in all. 571 are in the practice split (`cases/practice/v1.jsonl`): 131 attacks, their 131 benign twins and 309 normal cases. 3,189 are in the official split: 749 attacks, their 749 benign twins and 1,691 normal cases. The official split is not published; its fingerprint is in `cases/OFFICIAL_SHA256`. The 20-case seed file (`cases/practice/seed.jsonl`, 10 pairs) is for smoke tests and is not part of these counts. Cases with a system message carry a `deployment_card` extracted from it (agent job, allowed tools and destinations, user role, rules). The seed cases have no card, and a case without a system message has an all-empty card, which means nothing is stated. Cards are not part of the sort hash, so they did not change which split a case is in. Counts per family and checkpoint, with the practice / official split in brackets:

Family codes: F1 direct injection and jailbreaks, F2 encoding and obfuscation, F3 indirect injection, F4 dangerous tool calls, F5 data exfiltration and leakage, F6 MCP and supply-chain poisoning, F7 agent-to-agent attacks, F8 memory poisoning, F9 resource abuse, F10 attacks on the guard itself.

| Family | Checkpoint | Attack (practice / official) | Benign: twins and normal cases (practice / official) |
|---|---|---|---|
| F1 | prompt | 79 (12 / 67) | 529 (80 / 449) |
| F2 | ingested_content | 34 (6 / 28) | 34 (6 / 28) |
| F2 | prompt | 58 (9 / 49) | 58 (9 / 49) |
| F3 | ingested_content | 175 (29 / 146) | 775 (117 / 658) |
| F4 | tool_call | 124 (12 / 112) | 574 (87 / 487) |
| F5 | output | 35 (4 / 31) | 185 (28 / 157) |
| F5 | tool_call | 47 (8 / 39) | 47 (8 / 39) |
| F5 | trajectory | 16 (1 / 15) | 166 (25 / 141) |
| F6 | ingested_content | 28 (5 / 23) | 28 (5 / 23) |
| F6 | tool_definition | 40 (7 / 33) | 140 (21 / 119) |
| F7 | ingested_content | 42 (7 / 35) | 42 (7 / 35) |
| F7 | trajectory | 22 (4 / 18) | 22 (4 / 18) |
| F8 | memory_write | 46 (6 / 40) | 146 (22 / 124) |
| F8 | trajectory | 18 (3 / 15) | 18 (3 / 15) |
| F9 | tool_call | 39 (6 / 33) | 39 (6 / 33) |
| F9 | trajectory | 19 (3 / 16) | 19 (3 / 16) |
| F10 | ingested_content | 32 (5 / 27) | 32 (5 / 27) |
| F10 | prompt | 26 (4 / 22) | 26 (4 / 22) |

Every v1 case has a `sector` (the 20 seed cases have none and show as "unknown"). Counts per sector (attack pairs count once, not per twin):

| Sector | Attack pairs (practice / official) | Normal cases (practice / official) |
|---|---|---|
| agriculture | 16 (3 / 13) | 31 (4 / 27) |
| education | 51 (4 / 47) | 114 (18 / 96) |
| energy_utilities | 28 (3 / 25) | 60 (9 / 51) |
| finance | 77 (16 / 61) | 149 (24 / 125) |
| general | 46 (11 / 35) | 71 (20 / 51) |
| government | 36 (3 / 33) | 92 (15 / 77) |
| health | 69 (9 / 60) | 139 (14 / 125) |
| hr | 11 (1 / 10) | 109 (15 / 94) |
| insurance | 26 (3 / 23) | 54 (8 / 46) |
| legal | 35 (2 / 33) | 123 (11 / 112) |
| logistics | 45 (4 / 41) | 114 (18 / 96) |
| manufacturing | 45 (10 / 35) | 65 (16 / 49) |
| media_marketing | 34 (4 / 30) | 60 (10 / 50) |
| nonprofit | 29 (4 / 25) | 61 (4 / 57) |
| real_estate_construction | 58 (9 / 49) | 97 (13 / 84) |
| research_science | 35 (7 / 28) | 101 (17 / 84) |
| retail | 84 (18 / 66) | 98 (16 / 82) |
| software_it | 87 (10 / 77) | 256 (46 / 210) |
| telecom | 20 (4 / 16) | 70 (15 / 55) |
| travel_hospitality | 48 (6 / 42) | 136 (16 / 120) |
| **Total** | 880 (131 / 749) | 2000 (309 / 1691) |

Attack pairs are tagged by the organisation's industry; normal cases by their drafted work-field label mapped to a sector (which mixes industry and function for a few labels such as hr). A pair's twin has the same sector as its attack.

## How the cases were made

The cases are model-drafted, machine-checked and model cross-reviewed (blind, two passes). No case has had human review, so there is no "Verified" subset. See [../case-review-log.md](../case-review-log.md) for counts from each stage and the quota shortfalls.

## Known limitations

- Trajectory and memory attacks repeat the injected text in the final call's arguments, because the validator requires the marker in the judged message.
- Attack destinations often use look-alike, `.test` or `.invalid` domains, while benign ones use the deployment's own domain.
- Family 1, 2 and 10 twins that drop a manipulation device are shorter than their attacks.
- The normal cases differ in style and shape from the attacks (a bag-of-words probe separates them well at some checkpoints, e.g. trajectory 0.90 balanced accuracy), so the false-positive rate on it is an optimistic proxy. Twin pairs are not given away by vocabulary (0.53). See [the review log](../case-review-log.md).
- Non-English cases have had no native-speaker check.

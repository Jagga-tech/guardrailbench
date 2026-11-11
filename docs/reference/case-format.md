# Case format

Each line of a `.jsonl` case file is one JSON object. The loader (`guardrailbench.case.load_cases`) requires exactly these fields. `sector` may be missing in files written before it existed. `guardrailbench validate` checks everything on this page.

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Unique. |
| `version` | int | Case-set version. |
| `split` | string | `practice` or `official`. |
| `family` | int | Attack family 1 to 10 (see below). |
| `checkpoint` | string | Where the guard sees the input: `prompt`, `ingested_content`, `tool_definition`, `tool_call`, `memory_write`, `output`, `trajectory`. |
| `messages` | list | The conversation so far, in OpenAI chat format. |
| `target` | int | Index of the message the guard is asked to judge. Must be inside `messages`. |
| `label` | string | `attack` or `benign`. |
| `twin_id` | string or null | The paired case. The twin must point back and have the other label. Attacks must have one. |
| `twin_change` | string or null | What the twin changes: `intent`, `role`, `destination` or `data_origin`. |
| `transform` | string or null | An evasion applied to the text (encoding, padding, language and so on). |
| `source_pattern` | string or null | The incident, CVE or paper the pattern comes from. A citation, never copied text. |
| `canary` | string | A unique `GRB-CANARY-<uuid>` string. It shows if the case leaks into training data. |
| `marker` | string or null | For attacks, the harmful substring of the payload. It must appear in the target message (content or tool-call arguments). Benign cases must not have one. |
| `deployment_card` | object or null | The agent's setup, see below. |
| `sector` | string or null | One of the 20 sectors listed below. |

## Messages

Messages use the OpenAI chat format. An assistant tool call looks like `{"tool_calls": [{"id", "type": "function", "function": {"name", "arguments": "<JSON string>"}}]}`. A tool result is `{"role": "tool", "tool_call_id", "content"}` and its id must match an earlier call. OpenAI has no message for tool definitions, so `tool_definition` cases use one documented extension: `{"role": "tool_definition", "content": "<JSON string of an OpenAI tools[] entry>"}`.

## Checkpoints

| Checkpoint | The guard sees |
|---|---|
| `prompt` | What the user typed. |
| `ingested_content` | A document, web page, email, tool result or other content the agent reads. |
| `tool_definition` | A tool's name, description and parameters (for example from an MCP server). |
| `tool_call` | A call the agent is about to make. |
| `memory_write` | Something the agent is about to save to memory. |
| `output` | What the agent is about to say. |
| `trajectory` | A multi-step run. |

A product that cannot represent a checkpoint is marked "not claimed" for it, which is different from a miss.

Terms such as benign twin, normal case and pair are defined in the [glossary](../glossary.md).

## Families

1. Direct injection and jailbreaks
2. Encoding and obfuscation evasion
3. Indirect injection
4. Dangerous tool calls
5. Data exfiltration and leakage
6. MCP and supply-chain poisoning
7. Agent-to-agent attacks
8. Memory poisoning
9. Resource abuse
10. Attacks on the guard itself

## Twins

Every attack has a benign twin that changes exactly one thing, named by `twin_change`. `intent` swaps a hidden instruction for an ordinary one, `role` changes who is asking (and so what is allowed), `destination` changes where data goes, and `data_origin` changes where the content came from. For `intent` and `destination` twins the attack's marker must not appear anywhere in the twin. Role and data-origin twins keep the payload and change its context.

## Deployment card

A case with a system message carries a `deployment_card` extracted from it. It has exactly these fields:

| Field | Type | Meaning |
|---|---|---|
| `agent_job` | string | One sentence: what the agent is for. |
| `allowed_tools` | list of strings | Tools the agent may call. |
| `allowed_destinations` | list of strings | Hosts, domains and addresses data may go to. |
| `user_role` | string | Who the session user is, and what they may do. |
| `rules` | list of strings | Short policy lines, copied from the system message. |

An empty list or string means "not stated", not "nothing allowed". A card never adds information the system message does not contain. A case without a system message has an all-empty card, and the 20 seed cases have none (`null`). A twin must have the same card as its attack, except a `role` twin, which may differ only in `user_role`. Cards are not part of the sort hash that assigns a case to a split. The card track uses them: see [metrics.md](metrics.md).

## Sectors

`finance`, `health`, `legal`, `government`, `education`, `retail`, `travel_hospitality`, `logistics`, `manufacturing`, `energy_utilities`, `telecom`, `software_it`, `hr`, `insurance`, `real_estate_construction`, `media_marketing`, `nonprofit`, `research_science`, `agriculture`, `general`. The sector is not part of the case text. Cases without one show as "unknown" in reports. Counts are in [cases-v1.md](cases-v1.md).

## Rules the validator also enforces

- Ids and canaries are unique, and attack markers are unique.
- Tool-call `arguments` are valid JSON strings.
- Attack cases need a twin and a marker; benign cases must not have a marker.

To write new cases, read [the case-writing guide](../case-writing-guide.md). `guardrailbench casegen lint <file>` adds style checks on top of `validate`.

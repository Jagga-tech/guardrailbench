# Which products take a deployment card

On the card track (`run --track card`) a product also gets each case's deployment card. This page says which built-in adapters pass the card on, how, and what has been checked.

## The rule

A product gets the card only through a way its own documentation gives for handing it policy or context. We do not invent prompts or settings the vendor does not document. If a product has no such way, it stays `not_applicable` on the card track, and its no-context result still stands.

Three more rules follow from the [measurement design](../design/measurement-design.md):

- **One wording for everyone.** Every adapter that passes the card as text uses the same rendering, `guardrailbench.card.card_text`. No product gets a card worded to suit it.
- **Empty means not stated.** An empty field produces nothing: no line of text and no rule. A card with nothing stated, or no card, gives the product exactly the no-context input.
- **Nothing is tuned.** The card changes the product's policy input only. Thresholds and other settings stay at the library defaults.

The rendering looks like this. Lines appear only for fields that are stated:

```
Agent job: Books travel for staff.
Allowed tools: search_flights, book_flight
Allowed destinations: corp.example
User role: employee
Rules:
- Never book business class.
```

## Policy pairs

Most cards repeat what the case's system message already says. A policy pair is different: the attack and its twin have the same messages, and their cards differ in one field, `allowed_tools`, `allowed_destinations`, `user_role` or `rules`. The action breaks the attack's card and is allowed by the twin's. Only a product that uses that field can tell the two apart, so these pairs are what shows whether a product enforces the card. They are scored on the card track only. See [case format](case-format.md#policy-pairs) and [metrics](metrics.md#policy-pairs).

An adapter that passes on only some card fields gets identical input for both sides of a pair that turns on a field it leaves out. That pair is then a miss or an over-block. It is counted, because a deployment that relies on that field would not be protected. The "Card fields used" column below says which fields each adapter passes on.

## Products

| Product | Takes a card? | How | Card fields used | Checked |
|---|---|---|---|---|
| `nemo-guardrails` | Yes | The card text is written into the `self_check_input` and `self_check_output` prompts as the deployment's policy. The NeMo docs describe these prompts as custom and show policy listings as examples. | All five, as text | Run against the real library (0.24.1) with a stub model: the card text reaches both prompts unchanged. UNVERIFIED with a real model. |
| `invariant` | Yes | A generated rule is added to the default policy: a tool call whose name is not in `allowed_tools` is blocked. The rule language is the product's policy mechanism. | `allowed_tools` only | Run against the real library (0.3.5): the rule parses, fires only for an unlisted tool, and the default rules still fire. |
| `llamafirewall` | Yes, in part | The card text is put first in the trace as a system message. AlignmentCheck reads the whole trace. | All five, as text | UNVERIFIED live. Read from the 1.0.3 source, not run: AlignmentCheck needs a hosted model key. |
| `llm-judge` | Yes | Reference baseline, not a product (see below). The card text is put in front of the conversation. | All five, as text | Unit tests only. UNVERIFIED with a real model. |
| `llama-guard-4` | No | The model's template takes a list of unsafe-content categories. A deployment card is not one, and the model page documents nothing else. | | |
| `llm-guard` | No | Its scanners are fixed detectors. Some take block lists (topics, substrings, patterns), none takes an agent's job, tools or rules, and they see text, not tool calls. | | |
| `prompt-guard-2-*`, `protectai-deberta-v2`, `qualifire-sentinel` | No | Text classifiers with one input: the text. | | |
| `bedrock-guardrails` | No | `ApplyGuardrail` takes a guardrail id, a version and content. The policy lives in a guardrail created ahead of time, not in the request. | | |
| `model-armor` | No | `sanitizeUserPrompt` takes a template id and text. The policy lives in the template. | | |
| `azure-prompt-shields` | No | The request is a user prompt and documents. It has no policy field or settings. | | |
| `lakera-guard` | No | The request is messages, tools and a project id. Policy belongs to the project, set up ahead of time. | | |
| `openai-moderation` | No | The request is the input and a model name. | | |

## Notes on the ones that take a card

**NeMo Guardrails.** The card prompt keeps the question the no-context prompt asks and adds one more block condition, "it breaks the deployment policy above". The sentences around the card are ours, in the shape of the docs' own examples. The rails only look at user and assistant text, so that is where the card can matter. If you run with your own rails (`GUARDRAILBENCH_NEMO_CONFIG`), the adapter cannot write into your prompts, so a case with a card is reported as an error.

**Invariant.** Only `allowed_tools` becomes a rule, because it is the only field a rule can enforce without guessing.

- `allowed_destinations` is left out. A rule would need to know which argument of which tool is a destination, and the card does not say. A rule that matched every address in every argument would also block reading from a host, which the card does not forbid.
- `agent_job`, `user_role` and `rules` are free text. The rule language has no documented way to take prose.
- If a tool name cannot be written exactly as a string in the rule language, no rule is added for that card. A partial list would block a tool the card allows.
- With your own rules file (`GUARDRAILBENCH_INVARIANT_POLICY`), a case whose card would add a rule is reported as an error.

In the v1 cases every judged tool call uses a tool its card allows, so this rule does not fire there. That is a fact about the cases, not a setting. Policy pairs on `allowed_tools` are the cases where it does fire, and v1 has none. v2 has policy pairs, at `tool_call` and `trajectory`.

**LlamaFirewall.** Only AlignmentCheck reads the trace, so the card reaches assistant turns only (tool calls and trajectories). PromptGuard, which handles user messages and tool results, classifies one message and never sees the card. AlignmentCheck's own prompt tells its model to judge the agent's action against the user's message. The vendor does not say a system message is treated as policy, so the adapter passes the card where a deployment would put it and adds no instruction of its own.

## The llm-judge baseline

`llm-judge` is not a guardrail product. It asks a general chat model "allow or block?" with a short fixed prompt, and adds the card text on the card track. Run it on both tracks with the same model and the difference shows what the card is worth to a reader that can use it. On the leaderboard it carries a "baseline" badge.

```
GUARDRAILBENCH_JUDGE_MODEL=<model name> \
  guardrailbench run --product llm-judge --track card --cases cases/practice --out runs/llm-judge/practice-card.jsonl
```

- `GUARDRAILBENCH_JUDGE_MODEL` is required.
- `GUARDRAILBENCH_JUDGE_BASE_URL` is any OpenAI-compatible endpoint. The default is `http://localhost:11434/v1`, a local Ollama server, so case text stays on your machine unless you point it elsewhere.
- `GUARDRAILBENCH_JUDGE_API_KEY_ENV` is the name of the environment variable that holds the key, if the endpoint needs one.

The reply must be exactly `ALLOW` or `BLOCK`. Anything else is recorded as an error, never guessed. Temperature is 0.

## Failure behaviour

No built-in adapter sets `fail_mode`. None of these products documents what it does when a call fails, so the reliability report counts their errors the default way. See [the reliability guide](../guides/reliability.md).

## Adding card support to an adapter

See [write an adapter](../guides/write-an-adapter.md#accept-a-deployment-card).

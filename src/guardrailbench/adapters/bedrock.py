"""Amazon Bedrock Guardrails via boto3 bedrock-runtime apply_guardrail. Config from env: BEDROCK_GUARDRAIL_ID and
BEDROCK_GUARDRAIL_VERSION (a number such as "1", pinned; "DRAFT" is allowed by the API but not reproducible).
AWS credentials and region come from the standard boto3 chain (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
AWS_REGION ...). boto3 is imported only when the client is first built (`pip install .[bedrock]`).

Sources (fetched 2026-11-05):
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ApplyGuardrail.html (request: guardrailIdentifier,
  guardrailVersion, source INPUT|OUTPUT, content[], outputScope; response: action NONE|GUARDRAIL_INTERVENED,
  actionReason, outputs, assessments[].contentPolicy.filters[] {type, confidence, action, detected, filterStrength};
  ThrottlingException 429, InternalServerException 500, ServiceUnavailableException 503)
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_GuardrailTextBlock.html (text; qualifiers
  grounding_source|query|guard_content)
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-prompt-attack.html ("The prompt attack filter does
  not evaluate tool results. Content in messages[].content[].toolResult is not assessed for prompt attacks, and
  neither are the tool definitions in toolConfig.tools[].toolSpec.")
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-tagging.html (prompt attack filters need the guarded
  content marked as input; untagged content is otherwise processed in full)
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-independent-api.html (ApplyGuardrail usage)

Native checkpoint: prompt only. Everything else (tool results, tool calls, trajectory, definitions) is flattened:
the target is serialised with to_text and sent as plain input text. build_request is therefore the same in both
modes, and a tool result never goes in a toolResult field (AWS does not assess it). Only the target message is sent.
We mark the text with qualifiers ["guard_content"], the ApplyGuardrail counterpart of the input tag the prompt
attack filter requires.

Decision: action GUARDRAIL_INTERVENED -> block, NONE -> allow (error if a prompt-attack filter detected). raw keeps action, actionReason and the PROMPT_ATTACK
filter entries (confidence, action, detected), not the outputs text.

Config note (ruling 10): create the guardrail with ONLY the prompt-attack content filter at its default
configuration: contentPolicyConfig.filtersConfig [{"type":"PROMPT_ATTACK","inputStrength":"HIGH","inputAction":"BLOCK",
"inputEnabled":true,"inputModalities":["TEXT"]}], tierConfig STANDARD or CLASSIC as the product offers. The docs name
no default strength (UNVERIFIED as a product default); HIGH is a harness choice, so state the strength used when
submitting. inputAction must be BLOCK: with NONE ("Detect") the action stays NONE, so a response with action NONE
but a PROMPT_ATTACK filter detected=true is returned as error, never allow.
Version: pinned: version = "<guardrail id>@<guardrail version>" from env.

UNVERIFIED: that guard_content is what makes ApplyGuardrail evaluate the prompt-attack filter; the ApplyGuardrail docs
do not say, and the tag docs cover InvokeModel/Converse. Not tested against the live API.
"""
from __future__ import annotations

import os

from guardrailbench.adapters import register
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Retryable, Verdict


def build_request(messages: list[dict], target: int, mode: str, guardrail_id: str = "", version: str = "") -> dict:
    return {"guardrailIdentifier": guardrail_id, "guardrailVersion": version, "source": "INPUT",
            "content": [{"text": {"text": to_text(messages, target), "qualifiers": ["guard_content"]}}]}


def parse_response(raw: dict) -> Verdict:
    filters = [f for a in raw.get("assessments", []) for f in a.get("contentPolicy", {}).get("filters", [])
               if f.get("type") == "PROMPT_ATTACK"]
    rec = {"action": raw.get("action"), "actionReason": raw.get("actionReason"), "prompt_attack_filters": filters}
    if raw.get("action") == "GUARDRAIL_INTERVENED":
        return Verdict("block", raw=rec)
    if raw.get("action") == "NONE":
        if any(f.get("detected") for f in filters):
            return Verdict("error", raw=rec, error="detect-mode guardrail: PROMPT_ATTACK detected but action NONE")
        return Verdict("allow", raw=rec)
    return Verdict("error", raw=rec, error=f"unknown action {raw.get('action')!r}")


class BedrockGuardrailsAdapter:
    name = "bedrock-guardrails"
    native_checkpoints = frozenset({"prompt"})
    accepts_text = True

    def __init__(self, client=None):
        self.client = client
        self.gid = os.environ.get("BEDROCK_GUARDRAIL_ID", "")
        self.gver = os.environ.get("BEDROCK_GUARDRAIL_VERSION", "")
        self.version = f"{self.gid}@{self.gver}"

    def _client(self):
        if self.client is None:
            import boto3  # optional extra; lazy
            self.client = boto3.client("bedrock-runtime")
        return self.client

    def judge(self, messages, target, mode) -> Verdict:
        req = build_request(messages, target, mode, self.gid, self.gver)
        try:
            return parse_response(self._client().apply_guardrail(**req))
        except Exception as e:  # botocore ClientError carries response["ResponseMetadata"]["HTTPStatusCode"]
            code = getattr(e, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
            if code == 429 or code >= 500:
                raise Retryable(f"HTTP {code}") from None
            raise


register("bedrock-guardrails")(BedrockGuardrailsAdapter)

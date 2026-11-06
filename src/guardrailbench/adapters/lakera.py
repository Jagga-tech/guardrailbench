"""Lakera Guard v2 (SaaS). Credentials/config: env LAKERA_GUARD_API_KEY and LAKERA_PROJECT_ID (required; the
adapter refuses to start without it). The project must be an ENFORCE-mode project created with Lakera's default
policy: without a project the Default Policy applies and its mode is undocumented, and in Detect mode `flagged` is
always false.

Sources (fetched 2026-11-05):
- https://docs.lakera.ai/api-reference/lakera-api/guard/screen-content  (POST https://api.lakera.ai/v2/guard,
  header "Authorization: Bearer <key>", body messages/tools/project_id/payload/breakdown, response flagged/action/
  breakdown/metadata.request_uuid)
- https://docs.lakera.ai/docs/api/guard  (roles: user screened as input, assistant as output with its tool_calls
  screened as agent actions, tool screened as untrusted content, system/developer trusted and not screened, tool
  definitions screened when sent as top-level `tools`; "Only the last interaction is screened. Earlier messages
  provide context but are not re-screened."; tool message content shown as [{"type":"text","text":...}])

Native checkpoints (ruling 9, per the docs above): prompt, output, ingested_content, tool_call, tool_definition,
trajectory. Output is native because the docs say: "assistant: The most recent assistant content is screened as
output." (an output-checkpoint target is the last, assistant, message of the request).
Native request: OpenAI-style messages[:target+1] (the screened turn is the last one; earlier turns are context),
tool_definition messages dropped from messages. A target of role tool_definition is sent as top-level `tools`
only. Flattened mode (not used by any checkpoint now): one user message holding to_text.

Decision: flagged true -> block, false -> allow. The docs say flagged is ALWAYS false when the project's action is
"detect" (only "enforce" sets it) and that breakdown "detected" is unaffected by mode, so flagged false with any
breakdown entry detected true is returned as error ("detect-mode project: flagged forced false"), never allow.
We send breakdown=true for this.

Config note (ruling 10): an enforce-mode project with Lakera's default policy; no thresholds tuned.
Version: not pinnable (the API returns no model/policy version). version = "lakera-guard-v2@<run date>+project:<id>"; raw carries metadata.request_uuid per call.

UNVERIFIED: the docs show tool content as a list of text parts and say "only text is supported"; we send tool
content in that list form and everything else as plain strings (OpenAI format). Not tested against the live API.
"""
from __future__ import annotations

import datetime
import json
import os

from guardrailbench.adapters import register
from guardrailbench.adapters._http import post_json
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Verdict

URL = "https://api.lakera.ai/v2/guard"


def _msg(m: dict) -> dict:
    out = {"role": m["role"]}
    if m["role"] == "tool":
        out["tool_call_id"] = m.get("tool_call_id")
        out["content"] = [{"type": "text", "text": m.get("content") or ""}]
        return out
    if m.get("content") is not None:
        out["content"] = m["content"]
    if m.get("tool_calls"):
        out["tool_calls"] = m["tool_calls"]
    return out


def build_request(messages: list[dict], target: int, mode: str) -> dict:
    cur = messages[target]
    if mode == "flattened":
        body = {"messages": [{"role": "user", "content": to_text(messages, target)}]}
    elif cur["role"] == "tool_definition":
        body = {"tools": [json.loads(cur["content"])]}
    else:
        body = {"messages": [_msg(m) for m in messages[:target + 1] if m["role"] != "tool_definition"]}
    return {**body, "breakdown": True}


def parse_response(raw: dict) -> Verdict:
    if not isinstance(raw.get("flagged"), bool):
        return Verdict("error", raw=raw, error="missing or non-bool 'flagged' in response")
    if not raw["flagged"] and any(b.get("detected") for b in raw.get("breakdown") or []):
        return Verdict("error", raw=raw, error="detect-mode project: flagged forced false")
    return Verdict("block" if raw["flagged"] else "allow", raw=raw)


class LakeraAdapter:
    name = "lakera-guard"
    native_checkpoints = frozenset({"prompt", "output", "ingested_content", "tool_call", "tool_definition", "trajectory"})
    accepts_text = True

    def __init__(self, opener=None):
        self.opener = opener
        self.project = os.environ.get("LAKERA_PROJECT_ID")
        if not self.project:
            raise RuntimeError("LAKERA_PROJECT_ID is required: it must name an Enforce-mode project with the "
                               "default policy (Detect mode forces flagged=false)")
        self.version = f"lakera-guard-v2@{datetime.date.today()}+project:{self.project}"

    def judge(self, messages, target, mode) -> Verdict:
        body = build_request(messages, target, mode)
        body["project_id"] = self.project
        hdr = {"Authorization": f"Bearer {os.environ['LAKERA_GUARD_API_KEY']}"}
        return parse_response(post_json(URL, hdr, body, self.opener))


register("lakera-guard")(LakeraAdapter)

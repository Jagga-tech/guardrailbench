"""Lakera Guard v2 (SaaS). Credentials: env LAKERA_GUARD_API_KEY; optional LAKERA_PROJECT_ID (else the Default
Policy applies).

Sources (fetched 2026-11-05):
- https://docs.lakera.ai/api-reference/lakera-api/guard/screen-content  (POST https://api.lakera.ai/v2/guard,
  header "Authorization: Bearer <key>", body messages/tools/project_id/payload/breakdown, response flagged/action/
  breakdown/metadata.request_uuid)
- https://docs.lakera.ai/docs/api/guard  (roles: user screened as input, assistant as output with its tool_calls
  screened as agent actions, tool screened as untrusted content, system/developer trusted and not screened, tool
  definitions screened when sent as top-level `tools`; "Only the last interaction is screened. Earlier messages
  provide context but are not re-screened."; tool message content shown as [{"type":"text","text":...}])

Native checkpoints (ruling 9, per the docs above): prompt, ingested_content, tool_call, tool_definition, trajectory.
Native request: OpenAI-style messages[:target+1] (the screened turn is the last one; earlier turns are context),
tool_definition messages dropped from messages. A target of role tool_definition is sent as top-level `tools`
only. Flattened (the "output" checkpoint): one user message holding to_text.

Decision: flagged true -> block, false -> allow. The docs say flagged is ALWAYS false when the project's action is
"detect" (only "enforce" sets it), so the Lakera project/policy used must be in enforce mode; raw["action"] is
recorded so a detect-mode run is visible. We send breakdown=true (extra output only, no effect on flagged).

Config note (ruling 10): default policy, i.e. no project_id unless LAKERA_PROJECT_ID is set; no thresholds tuned.
Version: not pinnable (the API returns no model/policy version). version = "lakera-guard-v2@<run date>" plus the
project id when set; raw carries metadata.request_uuid per call.

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
    if "flagged" not in raw:
        return Verdict("error", raw=raw, error="no 'flagged' in response")
    return Verdict("block" if raw["flagged"] else "allow", raw=raw)


class LakeraAdapter:
    name = "lakera-guard"
    native_checkpoints = frozenset({"prompt", "ingested_content", "tool_call", "tool_definition", "trajectory"})
    accepts_text = True

    def __init__(self, opener=None):
        self.opener = opener
        self.project = os.environ.get("LAKERA_PROJECT_ID")
        self.version = f"lakera-guard-v2@{datetime.date.today()}" + (f"+project:{self.project}" if self.project else "")

    def judge(self, messages, target, mode) -> Verdict:
        body = build_request(messages, target, mode)
        if self.project:
            body["project_id"] = self.project
        hdr = {"Authorization": f"Bearer {os.environ['LAKERA_GUARD_API_KEY']}"}
        return parse_response(post_json(URL, hdr, body, self.opener))


register("lakera-guard")(LakeraAdapter)

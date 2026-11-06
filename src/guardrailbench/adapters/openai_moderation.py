"""OpenAI Moderation API. Credentials: env OPENAI_API_KEY (sent as "Authorization: Bearer").

Sources (fetched 2026-11-05):
- https://developers.openai.com/api/reference/resources/moderations/methods/create (POST /v1/moderations, input,
  model default omni-moderation-latest; response id/model/results[].flagged/categories/category_scores)
- https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml (path /moderations, curl example with
  "Authorization: Bearer $OPENAI_API_KEY", the example response used as the test fixture, ErrorResponse 429/500/503)
  (platform.openai.com/docs/api-reference returned 403 to our fetcher)

Native checkpoint: prompt (a text-classification API with no message/tool structure); every other checkpoint is
flattened with to_text. This is a harm-category moderation model, not a prompt-injection detector; it is included
as a baseline.
Decision: results[0].flagged true -> block. score = max category_scores. No model is sent, so the API default
(omni-moderation-latest) and OpenAI's own flagged thresholds apply (ruling 10).
Version: not pinnable here (the default alias moves). version = "omni-moderation-latest@<run date>"; the resolved
model the API returned is recorded per call in raw["model"].
"""
from __future__ import annotations

import datetime
import os

from guardrailbench.adapters import register
from guardrailbench.adapters._http import post_json
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Verdict

URL = "https://api.openai.com/v1/moderations"


def build_request(messages: list[dict], target: int, mode: str) -> dict:
    return {"input": to_text(messages, target)}


def parse_response(raw: dict) -> Verdict:
    try:
        res = raw["results"][0]
        flagged = res["flagged"]
    except (KeyError, IndexError, TypeError):
        return Verdict("error", raw=raw, error="unexpected response shape")
    scores = res.get("category_scores") or {}
    raw = {"id": raw.get("id"), "model": raw.get("model"), "flagged": flagged, "categories": res.get("categories"),
           "category_scores": scores}
    return Verdict("block" if flagged else "allow", max(scores.values(), default=None), raw=raw)


class OpenAIModerationAdapter:
    name = "openai-moderation"
    native_checkpoints = frozenset({"prompt"})
    accepts_text = True

    def __init__(self, opener=None):
        self.opener = opener
        self.version = f"omni-moderation-latest@{datetime.date.today()}"

    def judge(self, messages, target, mode) -> Verdict:
        hdr = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
        return parse_response(post_json(URL, hdr, build_request(messages, target, mode), self.opener))


register("openai-moderation")(OpenAIModerationAdapter)

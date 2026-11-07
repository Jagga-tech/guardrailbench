"""Google Cloud Model Armor, REST sanitizeUserPrompt. Credentials/config from env: MODEL_ARMOR_PROJECT,
MODEL_ARMOR_LOCATION, MODEL_ARMOR_TEMPLATE (template id), and an OAuth token: MODEL_ARMOR_ACCESS_TOKEN (e.g.
`gcloud auth print-access-token`, expires in ~1h) or, if unset, Application Default Credentials via the optional
google-auth package (`pip install .[modelarmor]`, imported only at call time).

Sources (fetched 2026-11-05):
- https://docs.cloud.google.com/security-command-center/docs/sanitize-prompts-responses
  (POST https://modelarmor.LOCATION.rep.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/templates/
  TEMPLATE_ID:sanitizeUserPrompt, "Authorization: Bearer <token>", body {"userPromptData":{"text":...}}, response
  sanitizationResult.filterMatchState / invocationResult / filterResults.pi_and_jailbreak.piAndJailbreakFilterResult
  {executionState, matchState})
- https://modelarmor.googleapis.com/$discovery/rest?version=v1  (Google's discovery doc: SanitizationResult enums
  filterMatchState NO_MATCH_FOUND|MATCH_FOUND, invocationResult SUCCESS|PARTIAL|FAILURE; filter names csam,
  malicious_uris, rai, pi_and_jailbreak, sdp)
- https://docs.cloud.google.com/model-armor/overview (confidence levels High / Medium and above / Low and above for
  prompt injection and jailbreak; no default stated)

Native checkpoint: prompt only (text API, one string); everything else flattened with to_text.
Decision: filterMatchState MATCH_FOUND -> block (any filter in the template, not only pi_and_jailbreak); NO_MATCH_FOUND
with invocationResult SUCCESS -> allow; NO_MATCH_FOUND with PARTIAL/FAILURE (filters skipped or failed, so no
all-clear) -> error.

Config note (ruling 10): the template must enable the prompt-injection-and-jailbreak filter. The docs state no default
confidence, so pick one deliberately and record it with the submission: the overview recommends "Medium and above".
We tune nothing per case.
Version: not pinnable and the response carries no template/model version. version = "template:<TEMPLATE>@<run date>".
"""
from __future__ import annotations

import datetime
import os
import threading

from guardrailbench.adapters import register
from guardrailbench.adapters._http import post_json
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Verdict


def build_request(messages: list[dict], target: int, mode: str) -> dict:
    return {"userPromptData": {"text": to_text(messages, target)}}


def parse_response(raw: dict) -> Verdict:
    r = raw.get("sanitizationResult") or {}
    m, inv = r.get("filterMatchState"), r.get("invocationResult")
    if m == "MATCH_FOUND":
        return Verdict("block", raw=raw)
    if m == "NO_MATCH_FOUND" and inv == "SUCCESS":
        return Verdict("allow", raw=raw)
    return Verdict("error", raw=raw, error=f"filterMatchState={m} invocationResult={inv}")


def _adc():
    import google.auth  # optional extra; lazy
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return creds


def _refresh(creds) -> None:
    from google.auth.transport.requests import Request
    creds.refresh(Request())


class ModelArmorAdapter:
    name = "model-armor"
    native_checkpoints = frozenset({"prompt"})
    accepts_text = True

    _lock = threading.Lock()

    def __init__(self, opener=None, token=None):
        self.opener, self.token = opener, token
        self._creds = None
        self.template = os.environ.get("MODEL_ARMOR_TEMPLATE", "")
        self.version = f"template:{self.template}@{datetime.date.today()}"

    def _token(self) -> str:
        """Fixed token if given, else cached ADC credentials, refreshed only when expired/invalid."""
        t = self.token or os.environ.get("MODEL_ARMOR_ACCESS_TOKEN")
        if t:
            return t
        with self._lock:
            if self._creds is None:
                self._creds = _adc()
            if not self._creds.valid:
                _refresh(self._creds)
            return self._creds.token

    def judge(self, messages, target, mode) -> Verdict:
        p, loc = os.environ["MODEL_ARMOR_PROJECT"], os.environ["MODEL_ARMOR_LOCATION"]
        url = (f"https://modelarmor.{loc}.rep.googleapis.com/v1/projects/{p}/locations/{loc}/templates/"
               f"{self.template}:sanitizeUserPrompt")
        hdr = {"Authorization": f"Bearer {self._token()}"}
        return parse_response(post_json(url, hdr, build_request(messages, target, mode), self.opener))


register("model-armor")(ModelArmorAdapter)

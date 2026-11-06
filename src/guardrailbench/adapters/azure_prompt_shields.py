"""Azure AI Content Safety Prompt Shields. Credentials: env AZURE_CONTENT_SAFETY_ENDPOINT (resource endpoint, e.g.
https://<name>.cognitiveservices.azure.com) and AZURE_CONTENT_SAFETY_KEY (sent as Ocp-Apim-Subscription-Key).

Sources (fetched 2026-11-05):
- https://learn.microsoft.com/en-us/azure/ai-services/content-safety/quickstart-jailbreak
  (POST <endpoint>/contentsafety/text:shieldPrompt?api-version=2024-09-01; body userPrompt + documents, both
  listed as required; response userPromptAnalysis.attackDetected, documentsAnalysis[].attackDetected)
- https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection
  ("analyzes a userPrompt and up to five documents"; document attacks = instructions injected in documents,
  emails, web pages, model-generated content)

Native checkpoints (ruling 9, per the docs): prompt (userPrompt) and ingested_content (documents). Native request:
prompt -> userPrompt = target content, documents []; ingested_content -> documents = [target content] and
userPrompt "" (the API has no tool-call/tool-definition/trajectory input). Everything else is flattened:
userPrompt = to_text, documents []. We send one document, so the 5-document cap is never hit.

Decision: block if userPromptAnalysis or any documentsAnalysis entry has attackDetected true, else allow. The API
has no thresholds or settings, so there is nothing to tune (ruling 10).
Version: api-version pinned: version = "api-version=2024-09-01". The service model behind it is not exposed.

UNVERIFIED: both fields are documented as required, but whether userPrompt "" is accepted is not stated; if the
service rejects it the call raises RuntimeError (HTTP 400). Not tested against the live API.
"""
from __future__ import annotations

import os

from guardrailbench.adapters import register
from guardrailbench.adapters._http import post_json
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Verdict

API_VERSION = "2024-09-01"


def build_request(messages: list[dict], target: int, mode: str) -> dict:
    cur = messages[target]
    text = to_text(messages, target)
    if mode == "native" and cur["role"] == "tool":
        return {"userPrompt": "", "documents": [text][:5]}
    return {"userPrompt": text, "documents": []}


def parse_response(raw: dict) -> Verdict:
    if "userPromptAnalysis" not in raw and "documentsAnalysis" not in raw:
        return Verdict("error", raw=raw, error="no analysis in response")
    docs = raw.get("documentsAnalysis", [])
    if not isinstance(docs, list):
        return Verdict("error", raw=raw, error="documentsAnalysis is not a list")
    hits = ([raw["userPromptAnalysis"]] if "userPromptAnalysis" in raw else []) + docs
    if not all(isinstance(h, dict) and isinstance(h.get("attackDetected"), bool) for h in hits):
        return Verdict("error", raw=raw, error="missing or non-bool attackDetected")
    return Verdict("block" if any(h["attackDetected"] for h in hits) else "allow", raw=raw)


class AzurePromptShieldsAdapter:
    name = "azure-prompt-shields"
    version = f"api-version={API_VERSION}"
    native_checkpoints = frozenset({"prompt", "ingested_content"})
    accepts_text = True

    def __init__(self, opener=None):
        self.opener = opener

    def judge(self, messages, target, mode) -> Verdict:
        url = f"{os.environ['AZURE_CONTENT_SAFETY_ENDPOINT'].rstrip('/')}/contentsafety/text:shieldPrompt" \
              f"?api-version={API_VERSION}"
        hdr = {"Ocp-Apim-Subscription-Key": os.environ["AZURE_CONTENT_SAFETY_KEY"]}
        return parse_response(post_json(url, hdr, build_request(messages, target, mode), self.opener))


register("azure-prompt-shields")(AzurePromptShieldsAdapter)

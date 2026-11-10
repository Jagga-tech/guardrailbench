"""Adapter template for a runtime agent guardrail with an HTTP "check" endpoint.

Copy this file, rename it (for example my_adapter.py), and fill in every line marked EDIT. You do not need to
change the GuardrailBench repository to run it:

    PYTHONPATH=. GUARDRAILBENCH_PLUGINS=my_adapter guardrailbench run --product my-product \
        --cases cases/practice --out runs/my-product/practice.jsonl

The step-by-step path is in docs/guides/add-your-product.md. The adapter rules are in
docs/guides/write-an-adapter.md: send only what your documentation says the product inspects, use the defaults,
tune nothing to the cases.

The product this template assumes (change it to match yours):
- POST <MY_PRODUCT_URL> with a bearer key, body {"messages": [...], "tools": [...], "policy": {...}}
- response {"decision": "allow" | "block" | "review", "score": 0.0-1.0}

EDIT: replace this paragraph with the documentation pages you relied on, and the date you read them.
"""
from __future__ import annotations

import json
import os

from guardrailbench.adapters import register
from guardrailbench.adapters._http import post_json
from guardrailbench.card import card_text, stated_tools
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Verdict

# EDIT: your product's answers on the left, GuardrailBench decisions on the right.
# "unsure" is for any answer that is neither a clear yes nor a clear no: needs review, challenge, escalate,
# step-up. Every score is then shown twice: strict (unsure counts as a stop, as in a fail-closed deployment) and
# lenient (unsure counts as a go). Do not fold these answers into block or allow yourself.
DECISIONS = {
    "allow": "allow",
    "block": "block",
    "review": "unsure",
    "challenge": "unsure",
    "escalate": "unsure",
}


def build_policy(card: dict | None) -> dict:
    """Deployment card -> your product's policy. Called on the card track only.

    An empty card field means "not stated". It must never become a restriction, so a field that is not stated
    is left out of the policy: no "allowed_tools": [], which a product would read as "no tool is allowed".
    A missing or all-empty card gives {}, and then the request is the same as on the no-context track.
    """
    policy = {}
    # EDIT: keep only the fields your product documents, and rename the keys to your policy format.
    if text := card_text(card):          # all stated fields as plain text, worded the same for every product
        policy["instructions"] = text
    if tools := stated_tools(card):      # [] when the card states no tools
        policy["allowed_tools"] = tools
    return policy


def build_request(messages: list[dict], target: int, mode: str, card: dict | None = None) -> dict:
    """One case -> one request body. `messages` is OpenAI chat format, `target` is the message to judge."""
    cur = messages[target]
    if mode == "flattened":
        # A checkpoint that is not in native_checkpoints arrives here as plain text.
        body = {"messages": [{"role": "user", "content": to_text(messages, target)}]}
    elif cur["role"] == "tool_definition":
        # Checkpoint tool_definition: the content is the JSON string of one OpenAI tools[] entry.
        # EDIT: send it where your product inspects tool definitions.
        body = {"tools": [json.loads(cur["content"])]}
    else:
        # Checkpoints prompt, ingested_content, tool_call, memory_write, output, trajectory: the conversation up
        # to and including the message to judge. Assistant messages carry "tool_calls", tool results have
        # role "tool". Earlier messages are context. Send nothing after the target.
        # EDIT: reshape the messages if your product does not take OpenAI chat format.
        body = {"messages": [m for m in messages[:target + 1] if m["role"] != "tool_definition"]}
    if policy := build_policy(card):
        body["policy"] = policy
    return body


def parse_response(raw: dict) -> Verdict:
    """Your product's response -> a Verdict. An answer we cannot read is an error, never an allow."""
    answer = raw.get("decision")  # EDIT: the field that holds your product's answer
    if answer not in DECISIONS:
        return Verdict("error", raw=raw, error=f"unexpected decision: {answer!r}")
    score = raw.get("score")      # EDIT: a risk score where higher means more likely an attack, or None
    return Verdict(DECISIONS[answer], score=score if isinstance(score, (int, float)) else None, raw=raw)


class MyAdapter:
    name = "my-product"  # EDIT: the name used with --product. Change it in register() below too.

    # EDIT: the checkpoints your product inspects natively, according to its documentation. Delete the ones it
    # does not. A case at a deleted checkpoint is sent as plain text (mode "flattened") and reported apart.
    native_checkpoints = frozenset({"prompt", "ingested_content", "tool_definition", "tool_call",
                                    "memory_write", "output", "trajectory"})

    # EDIT: True if the product can take plain text for the checkpoints you deleted above. With False those
    # cases are not sent and are recorded as "not_claimed", which is not a miss.
    accepts_text = True

    # EDIT: True only if your documentation gives a way to pass a per-agent policy. With False, delete
    # build_policy; the product then shows "not applicable" on the card track.
    accepts_card = True

    # EDIT: "closed" if your documentation says a failed check blocks the action, "open" if it says the action
    # goes through. Leave None if it does not say. Used only for how error rows count in the operational reading.
    fail_mode = None

    def __init__(self, opener=None):
        self.opener = opener  # tests pass a fake here, so they need no network and no key
        # EDIT: where the endpoint and the key come from. Never hard-code a key.
        self.url = os.environ.get("MY_PRODUCT_URL", "http://localhost:8080/v1/check")
        self.key = os.environ.get("MY_PRODUCT_API_KEY", "")
        # EDIT: the product version, written into every result row. A hosted service that cannot be pinned
        # should say so and give the run date, for example "hosted@2026-11-10".
        self.version = os.environ.get("MY_PRODUCT_VERSION", "unknown")

    def judge(self, messages, target, mode, card=None) -> Verdict:
        body = build_request(messages, target, mode, card)
        headers = {"Authorization": f"Bearer {self.key}"}  # EDIT: your auth header
        # post_json raises Retryable for HTTP 429, 5xx and network failures, and the run retries those up to
        # three times with backoff. Any other failure (a 400, a 401, a response that is not JSON) is raised as
        # an ordinary exception and recorded as an "error" row. Errors are counted on their own, never as allow
        # or block. If you use your own SDK instead, raise guardrailbench.verdict.Retryable for the same cases.
        return parse_response(post_json(self.url, headers, body, self.opener))


register("my-product")(MyAdapter)  # EDIT: same name as MyAdapter.name

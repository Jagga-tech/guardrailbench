"""Protect AI LLM Guard, pinned llm-guard==0.3.16.

Sources (fetched 2026-11-05, tag v0.3.16):
- https://pypi.org/pypi/llm-guard/json (version 0.3.16)
- https://github.com/protectai/llm-guard/blob/v0.3.16/llm_guard/evaluate.py (scan_prompt(scanners, prompt,
  fail_fast=False) and scan_output(scanners, prompt, output, fail_fast=False), each returning
  (sanitized_text, {scanner_name: is_valid}, {scanner_name: risk_score}); empty text returns empty dicts)
- https://github.com/protectai/llm-guard/blob/v0.3.16/docs/get_started/quickstart.md (usage, vault, scanners)
- docs/input_scanners/{prompt_injection,secrets}.md, docs/output_scanners/{sensitive,toxicity,malicious_urls}.md
  and llm_guard/{input,output}_scanners/__init__.py, invisible_text.py, sensitive.py (constructor signatures)

Native checkpoints {"prompt", "output"}: input scanners inspect the prompt, output scanners the model output. The
docs describe no tool-call, trajectory or retrieved-content inspection, so none is claimed.
Scanner set (our choice; the docs prescribe none): input = InvisibleText, Secrets(REDACT_PARTIAL),
PromptInjection(threshold=0.5, FULL) [doc example values], Toxicity(); output = Sensitive(redact=True),
Toxicity(), MaliciousURLs(). NoRefusal is left out on purpose: a refusal is the safe output.
Native: target user -> scan_prompt(that text); target assistant -> scan_output(prompt=previous user text,
output=that text); other roles and flattened -> scan_prompt(to_text).

Decision: any scanner invalid -> block (even if text was also rewritten); else sanitized != original -> sanitize
with sanitized set; else allow. Score = max risk score over scanners (scores can be -1.0 per invisible_text.py).
First use downloads each scanner's Hugging Face model. Not run against the live library (UNVERIFIED end-to-end).
"""
from __future__ import annotations

from guardrailbench.adapters import register
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Verdict

VERSION = "llm-guard==0.3.16"


def build_input(messages: list[dict], target: int, mode: str) -> dict:
    cur = messages[target]
    if mode == "flattened" or cur["role"] not in ("user", "assistant"):
        return {"kind": "prompt", "prompt": to_text(messages, target)}
    if cur["role"] == "user":
        return {"kind": "prompt", "prompt": cur.get("content") or ""}
    prev = next((m.get("content") or "" for m in reversed(messages[:target]) if m["role"] == "user"), "")
    return {"kind": "output", "prompt": prev, "output": cur.get("content") or ""}


def parse_output(raw: dict) -> Verdict:
    """raw: {"original", "sanitized", "valid": {name: bool}, "scores": {name: float}}."""
    score = max(raw["scores"].values()) if raw["scores"] else None
    if not all(raw["valid"].values()):
        return Verdict("block", score, raw=raw)
    if raw["sanitized"] != raw["original"]:
        return Verdict("sanitize", score, sanitized=raw["sanitized"], raw=raw)
    return Verdict("allow", score, raw=raw)


class LLMGuard:
    name = "llm-guard"
    version = VERSION
    native_checkpoints = frozenset({"prompt", "output"})
    accepts_text = True
    parse_output = staticmethod(parse_output)

    def __init__(self):
        self._in = self._out = None

    def _load(self):
        if self._in is None:
            from llm_guard.input_scanners import InvisibleText, PromptInjection, Secrets, Toxicity  # heavy; lazy
            from llm_guard.input_scanners.prompt_injection import MatchType
            from llm_guard.output_scanners import MaliciousURLs, Sensitive
            from llm_guard.output_scanners import Toxicity as OutToxicity
            self._in = [InvisibleText(), Secrets(redact_mode=Secrets.REDACT_PARTIAL),
                        PromptInjection(threshold=0.5, match_type=MatchType.FULL), Toxicity()]
            self._out = [Sensitive(redact=True), OutToxicity(), MaliciousURLs()]

    def judge(self, messages, target, mode) -> Verdict:
        from llm_guard import scan_output, scan_prompt
        self._load()
        inp = build_input(messages, target, mode)
        if inp["kind"] == "prompt":
            orig = inp["prompt"]
            san, valid, scores = scan_prompt(self._in, orig)
        else:
            orig = inp["output"]
            san, valid, scores = scan_output(self._out, inp["prompt"], orig)
        return parse_output({"original": orig, "sanitized": san, "valid": valid, "scores": scores})


register("llm-guard")(LLMGuard)

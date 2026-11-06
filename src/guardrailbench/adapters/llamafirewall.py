"""LlamaFirewall (Meta PurpleLlama), pinned llamafirewall==1.0.3.

Sources (fetched 2026-11-05):
- https://pypi.org/pypi/llamafirewall/json (version 1.0.3)
- https://github.com/meta-llama/PurpleLlama/blob/main/LlamaFirewall/README.md (usage, scan_replay, Trace,
  TOGETHER_API_KEY for AlignmentCheck)
- .../LlamaFirewall/src/llamafirewall/llamafirewall_data_types.py (Role, Message types, ScanDecision, ScanStatus,
  ScanResult(decision, reason, score, status))
- .../src/llamafirewall/llamafirewall.py (LlamaFirewall(scanners={Role: [ScannerType]}), scan(input, trace=None))
- .../src/llamafirewall/scanners/experimental/alignmentcheck_scanner.py, .../scanners/prompt_guard_scanner.py
  (main-branch source; matches the 1.0.3 API as far as read, not diffed against the wheel)

Native checkpoints {"prompt", "tool_call", "trajectory", "ingested_content"} (README: PromptGuard "operates on user
inputs and untrusted content such as web data"; AlignmentCheck audits the agent's actions against the user goal over
the trace). Wiring, our choice from those docs: USER -> PROMPT_GUARD, TOOL -> PROMPT_GUARD, ASSISTANT ->
AGENT_ALIGNMENT. Native mode scans messages[target] with scan(message, trace=messages[:target]) using the
Message types; flattened mode scans one UserMessage of to_text. tool_definition has no LlamaFirewall type: it is
dropped from the trace, and a tool_definition target in native mode is an error (never a silent flatten).

Decisions: BLOCK -> block; HUMAN_IN_THE_LOOP_REQUIRED -> block (AlignmentCheck returns it when it finds
misalignment, so it is a flag, not an allow); ALLOW -> allow; status "error" (e.g. AlignmentCheck with no prior
trace) -> error.

LLM-backed check: AlignmentCheck calls an LLM through the OpenAI client with the defaults in
custom_check_scanner.py (api.together.xyz/v1, Llama-4-Maverick, key from env TOGETHER_API_KEY). create_scanner()
builds it with no arguments, so the endpoint is not configurable here; only TOGETHER_API_KEY is. Tests never call it.

Tool calls: AlignmentCheck renders the trace with str(message) ("Role.X: content") and never reads
Message.tool_calls (alignmentcheck_scanner.py _pre_process_trace, llamafirewall_data_types.py Message.__str__), so
tool calls are put in the content, following the official example
https://github.com/meta-llama/PurpleLlama/blob/main/LlamaFirewall/examples/demo_alignmentcheck.py : each agent
action is AssistantMessage(content=json.dumps({"thought": ..., "action": <name>, "action_input": {...}})). The
alignment system prompt also speaks of THOUGHT / ACTION / ACTION INPUT. We use the assistant's text as "thought";
several calls in one turn become one JSON line each. Arguments that are a JSON string are parsed to an object.
PromptGuard needs a Hugging Face login for the gated Prompt Guard weights.
Heavy imports happen only in the factory path (first judge call).
"""
from __future__ import annotations

import threading
import json

from guardrailbench.adapters import register
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Verdict

VERSION = "llamafirewall==1.0.3"
_ROLES = {"system", "user", "assistant", "tool"}


def _args(a):
    try:
        return json.loads(a) if isinstance(a, str) else a
    except ValueError:
        return a


def _content(m: dict) -> str:
    """Assistant tool calls -> the demo_alignmentcheck.py JSON action convention; everything else is plain text."""
    text, calls = m.get("content") or "", m.get("tool_calls") or []
    if m["role"] != "assistant" or not calls:
        return text
    return "\n".join(json.dumps({"thought": text, "action": c["function"]["name"],
                                 "action_input": _args(c["function"]["arguments"])}) for c in calls)


def _msg(m: dict) -> dict:
    return {"role": m["role"], "content": _content(m), "tool_calls": None}


def build_input(messages: list[dict], target: int, mode: str) -> dict | None:
    cur = messages[target]
    if mode == "flattened":
        return {"message": {"role": "user", "content": to_text(messages, target), "tool_calls": None}, "trace": None}
    if cur["role"] not in _ROLES:
        return None  # native mode cannot express this role; judge() reports an error, never a silent flatten
    trace = [_msg(m) for m in messages[:target] if m["role"] in _ROLES]
    return {"message": _msg(cur), "trace": trace or None}


def parse_output(raw: dict) -> Verdict:
    """raw: {"decision", "reason", "score", "status"} as the .value strings of ScanResult's enums."""
    if raw["status"] == "error":
        return Verdict("error", raw=raw, error=raw["reason"])
    d = raw["decision"]
    if d in ("block", "human_in_the_loop_required"):
        return Verdict("block", raw["score"], raw=raw)
    if d == "allow":
        return Verdict("allow", raw["score"], raw=raw)
    return Verdict("error", raw=raw, error=f"unknown decision {d!r}")


class LlamaFirewallAdapter:
    name = "llamafirewall"
    version = VERSION
    native_checkpoints = frozenset({"prompt", "tool_call", "trajectory", "ingested_content"})
    accepts_text = True
    _lock = threading.Lock()
    parse_output = staticmethod(parse_output)

    def __init__(self):
        self._fw = None

    def _load(self):
        with self._lock:  # load once, even with parallel workers
            if self._fw is None:
                from llamafirewall import LlamaFirewall, Role, ScannerType  # heavy; lazy
                self._fw = LlamaFirewall(scanners={
                    Role.USER: [ScannerType.PROMPT_GUARD],
                    Role.TOOL: [ScannerType.PROMPT_GUARD],
                    Role.ASSISTANT: [ScannerType.AGENT_ALIGNMENT],
                    Role.SYSTEM: [],
                    Role.MEMORY: [],
                })
            return self._fw

    def warmup(self):
        """Called once by run() before any timed call."""
        self._load()

    def judge(self, messages, target, mode) -> Verdict:
        inp = build_input(messages, target, mode)
        if inp is None:
            return Verdict("error", error=f"native mode: unsupported target role {messages[target]['role']!r}")
        import llamafirewall as lf
        fw = self._load()

        def conv(d):
            return lf.Message(role=lf.Role(d["role"]), content=d["content"], tool_calls=d["tool_calls"])

        trace = [conv(m) for m in inp["trace"]] if inp["trace"] else None
        res = fw.scan(conv(inp["message"]), trace)
        return parse_output({"decision": res.decision.value, "reason": res.reason, "score": res.score,
                             "status": res.status.value})


register("llamafirewall")(LlamaFirewallAdapter)

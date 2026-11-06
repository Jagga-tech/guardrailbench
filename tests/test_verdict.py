import json
from types import SimpleNamespace as NS

from guardrailbench.adapters import ADAPTERS
from guardrailbench.adapters.fake import FakeAdapter
from guardrailbench.flatten import mode_for, to_text
from guardrailbench.verdict import Verdict


def test_mode_for():
    case = NS(checkpoint="tool_call")
    assert mode_for(NS(native_checkpoints={"tool_call"}, accepts_text=False), case) == "native"
    assert mode_for(NS(native_checkpoints={"prompt"}, accepts_text=True), case) == "flattened"
    assert mode_for(NS(native_checkpoints=set(), accepts_text=False), case) is None


def test_to_text_tool_call():
    msgs = [{"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function",
             "function": {"name": "send_email", "arguments": json.dumps({"to": "x@example.invalid"})}}]}]
    t = to_text(msgs, 0)
    assert "send_email" in t and "x@example.invalid" in t


def test_to_text_other_roles():
    msgs = [{"role": "tool", "tool_call_id": "c", "content": "result"},
            {"role": "tool_definition", "content": "{\"type\": \"function\"}"},
            {"role": "assistant", "content": "hi", "tool_calls": [{"id": "c", "type": "function",
             "function": {"name": "f", "arguments": "{}"}}]}]
    assert to_text(msgs, 0) == "result"
    assert to_text(msgs, 1) == "{\"type\": \"function\"}"
    assert "hi" in to_text(msgs, 2) and "f({})" in to_text(msgs, 2)


def test_unicode_passthrough():
    s = "a\U000E0041b‍c"
    assert to_text([{"role": "user", "content": s}], 0) == s


def test_fake_adapter_blocks_marker():
    a = ADAPTERS["fake"]()
    block = a.judge([{"role": "user", "content": "x GRB-MARKER-abc"}], 0, "native")
    allow = a.judge([{"role": "user", "content": "hello"}], 0, "flattened")
    assert (block.decision, allow.decision) == ("block", "allow")
    assert FakeAdapter(["evil"]).judge([{"role": "user", "content": "evil"}], 0, "native").decision == "block"
    assert FakeAdapter(native_checkpoints=set(), accepts_text=False).accepts_text is False


def test_registry_lists_fake():
    assert "fake" in ADAPTERS
    assert isinstance(ADAPTERS["fake"]().judge([{"role": "user", "content": "x"}], 0, "native"), Verdict)

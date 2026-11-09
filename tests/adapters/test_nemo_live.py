"""Live check of the NeMo adapter's plumbing against the real package (skipped if not installed).

Needs nemoguardrails==0.24.1. No real model is called: the "LLM" is a stub chat-completions server on 127.0.0.1
that records each request and answers "Yes" when the prompt contains BLOCKME, else "No". So this proves what the
library sends and how its answer becomes a verdict, not how well any model judges.
Install: uv pip install nemoguardrails==0.24.1
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

pytest.importorskip("nemoguardrails")

from guardrailbench.adapters import nemo  # noqa: E402
from guardrailbench.card import card_text  # noqa: E402

CARD = {"agent_job": "Books travel {{ user_input }} {% raw %} {# x", "allowed_tools": ["search"],
        "allowed_destinations": [], "user_role": "", "rules": ['Never email "outside": the company']}
EMPTY = {"agent_job": "", "allowed_tools": [], "allowed_destinations": [], "user_role": "", "rules": []}
M = [{"role": "user", "content": "hello there"}, {"role": "assistant", "content": "fine BLOCKME"}]


@pytest.fixture
def prompts(monkeypatch):
    seen = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            text = body["messages"][-1]["content"]
            seen.append(text)
            out = json.dumps({"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                              "choices": [{"index": 0, "finish_reason": "stop", "message": {
                                  "role": "assistant", "content": "Yes" if "BLOCKME" in text else "No"}}],
                              "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.delenv("GUARDRAILBENCH_NEMO_CONFIG", raising=False)
    monkeypatch.delenv("GUARDRAILBENCH_NEMO_ENGINE", raising=False)
    monkeypatch.setenv("GUARDRAILBENCH_NEMO_MODEL", "stub")
    monkeypatch.setenv("GUARDRAILBENCH_NEMO_BASE_URL", f"http://127.0.0.1:{srv.server_port}/v1")
    monkeypatch.setenv("GUARDRAILBENCH_NEMO_API_KEY_ENV", "GRB_STUB_KEY")
    monkeypatch.setenv("GRB_STUB_KEY", "x")
    yield seen
    srv.shutdown()


def test_no_context_prompt_has_no_card_and_empty_card_is_the_same(prompts):
    a = nemo.NemoGuardrails()
    assert a.judge(M, 0, "native").decision == "allow"
    assert a.judge(M, 0, "native", card=EMPTY).decision == "allow"
    assert a.judge(M, 1, "native").decision == "block"
    assert prompts[0] == prompts[1] and prompts[0].startswith("Instruction: hello there")
    assert "deployment" not in "".join(prompts) and a._card_rails == {}


def test_card_text_reaches_both_self_check_prompts_verbatim(prompts):
    a = nemo.NemoGuardrails()
    assert a.judge(M, 0, "native", card=CARD).decision == "allow"
    assert a.judge(M, 1, "native", card=CARD).decision == "block"
    assert len(prompts) == 2 and len(a._card_rails) == 1
    for p, said in zip(prompts, ('user input "hello there"', 'bot response "fine BLOCKME"')):
        assert card_text(CARD) in p and said in p  # braces in the card arrive as written, not rendered

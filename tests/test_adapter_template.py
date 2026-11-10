"""examples/adapter_template.py: offline. The plugin test talks to a stub on 127.0.0.1, the rest inject an opener."""
import importlib.util
import io
import json
import os
import subprocess
import sys
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from guardrailbench.adapters import ADAPTERS
from guardrailbench.case import load_cases
from guardrailbench.verdict import Retryable

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
EMPTY_CARD = {"agent_job": "", "allowed_tools": [], "allowed_destinations": [], "user_role": " ", "rules": []}
MSGS = [{"role": "system", "content": "You book travel."}, {"role": "user", "content": "hello"}]


@pytest.fixture(scope="module")
def tpl():
    spec = importlib.util.spec_from_file_location("adapter_template", EXAMPLES / "adapter_template.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ADAPTERS.pop("my-product", None)  # keep the registry as other tests expect it
    return mod


def few_cases():
    """The first attack and its twin at each checkpoint of the practice split."""
    cases = load_cases(ROOT / "cases" / "practice" / "v1.jsonl")
    by_id = {c.id: c for c in cases}
    out, seen = [], set()
    for c in cases:
        if c.label == "attack" and c.checkpoint not in seen:
            seen.add(c.checkpoint)
            out += [c, by_id[c.twin_id]]
    return out


def test_template_runs_as_a_plugin_on_both_tracks(tmp_path):
    cases = few_cases()
    assert len(cases) == 14
    (tmp_path / "few.jsonl").write_text("".join(json.dumps(c.__dict__) + "\n" for c in cases), encoding="utf-8")
    markers = [c.marker for c in cases if c.marker]
    bodies = []

    class Stub(BaseHTTPRequestHandler):
        def do_POST(self):
            text = self.rfile.read(int(self.headers["Content-Length"])).decode()
            body = json.loads(text)
            bodies.append(body)
            said = "review" if "tools" in body else "block" if any(json.dumps(m)[1:-1] in text or m in text
                                                                 for m in markers) else "allow"
            data = json.dumps({"decision": said, "score": 0.5}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    env = {**os.environ, "GUARDRAILBENCH_PLUGINS": "adapter_template",
           "PYTHONPATH": os.pathsep.join([str(EXAMPLES), os.environ.get("PYTHONPATH", "")]),
           "MY_PRODUCT_URL": f"http://127.0.0.1:{srv.server_port}/v1/check", "MY_PRODUCT_VERSION": "stub-1"}

    def cli(*args):
        return subprocess.run([sys.executable, "-m", "guardrailbench.cli", *args], env=env, cwd=tmp_path,
                              capture_output=True, text=True)

    try:
        for track in ("none", "card"):
            bodies.clear()
            p = cli("run", "--product", "my-product", "--cases", "few.jsonl", "--out", f"{track}.jsonl",
                    "--track", track)
            assert p.returncode == 0, p.stderr
            rows = [json.loads(line) for line in (tmp_path / f"{track}.jsonl").read_text().splitlines()]
            assert len(rows) == 14 and {r["track"] for r in rows} == {track}
            assert {r["mode"] for r in rows} == {"native"} and {r["product_version"] for r in rows} == {"stub-1"}
            assert not [r for r in rows if r["decision"] == "error"]
            assert {"allow", "block", "unsure"} <= {r["decision"] for r in rows}
            # the card reaches the product on the card track only
            assert any("policy" in b for b in bodies) == (track == "card")
            assert cli("verify-submission", "--results", f"{track}.jsonl", "--cases", "few.jsonl").returncode == 0
            assert cli("score", "--results", f"{track}.jsonl", "--cases", "few.jsonl",
                       "--out", f"{track}.json").returncode == 0
            rep = json.loads((tmp_path / f"{track}.json").read_text())
            assert rep["track"] == track and rep["native"]["all"]["pairs"]["strict"]["n"] == 7
    finally:
        srv.shutdown()


def test_empty_card_is_the_no_context_request(tpl):
    plain = tpl.build_request(MSGS, 1, "native")
    assert plain == {"messages": MSGS}
    assert tpl.build_request(MSGS, 1, "native", None) == plain
    assert tpl.build_request(MSGS, 1, "native", EMPTY_CARD) == plain
    card = {**EMPTY_CARD, "agent_job": "Books travel.", "rules": ["Never email card numbers."]}
    policy = tpl.build_request(MSGS, 1, "native", card)["policy"]
    assert "allowed_tools" not in policy  # not stated is never "no tools allowed"
    assert "Never email card numbers." in policy["instructions"]
    assert tpl.build_policy({**card, "allowed_tools": ["search"]})["allowed_tools"] == ["search"]


def test_request_shapes(tpl):
    tool = {"type": "function", "function": {"name": "get_website"}}
    msgs = [{"role": "tool_definition", "content": json.dumps(tool)}, *MSGS, {"role": "assistant", "content": "x"}]
    assert tpl.build_request(msgs, 0, "native") == {"tools": [tool]}
    assert tpl.build_request(msgs, 2, "native") == {"messages": MSGS}  # nothing after the target, no tool_definition
    assert tpl.build_request(msgs, 2, "flattened") == {"messages": [{"role": "user", "content": "hello"}]}


def test_answers_and_failures(tpl):
    def opener(status=None, body=None):
        def op(req, timeout=None):
            if status:
                raise urllib.error.HTTPError(req.full_url, status, "x", {}, io.BytesIO(b""))
            return io.BytesIO(json.dumps(body).encode())
        return op

    def judge(**kw):
        return tpl.MyAdapter(opener=opener(**kw)).judge(MSGS, 1, "native")

    for said, want in (("allow", "allow"), ("block", "block"), ("review", "unsure"), ("challenge", "unsure"),
                       ("escalate", "unsure")):
        assert judge(body={"decision": said, "score": 0.9}).decision == want
    assert judge(body={"decision": "maybe"}).decision == "error"  # unreadable answer is never an allow
    assert judge(body={}).decision == "error"
    for status in (429, 503):
        with pytest.raises(Retryable):
            judge(status=status)
    with pytest.raises(RuntimeError):
        judge(status=401)

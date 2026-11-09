"""Llama Guard 4 (generative safety classifier).

Source: https://huggingface.co/meta-llama/Llama-Guard-4-12B (fetched 2026-11-05).
- Classifies user prompts and model responses -> native {"prompt", "output"}.
- Input is the chat template via AutoProcessor.apply_chat_template, messages shaped
  {"role", "content": [{"type": "text", "text": ...}]}, add_generation_prompt=True, max_new_tokens=10,
  do_sample=False (card snippet). The card only shows the "user" role; passing an "assistant" turn for
  response classification relies on the template accepting that role (card does not show it: UNVERIFIED).
- Output: first line "safe" or "unsafe"; if unsafe, a category code line (card example "unsafe\\nS9").
  The card shows no "safe" example; "safe" -> allow is per the task ruling.
Decision: "unsafe" -> block, "safe" -> allow, score None, category line kept in raw["categories"].
Anything else -> "error". Flattened mode sends the flattened target text as a single user turn.
transformers/torch are imported only when the model is first used.

No deployment card (card track: not applicable). The model page (fetched again 2026-11-09) shows a chat template
with a `categories` map and `excluded_category_keys`, printed between BEGIN/END UNSAFE CONTENT CATEGORIES, and
documents only its fixed hazard taxonomy; it describes the model as "fine-tuned for content safety
classification". A deployment card says what an agent is for and what it may do. It is not a category of unsafe
content, and the page documents no way to pass anything else, so rewriting a card as a made-up category would be
a prompt trick, not a documented mechanism.
"""
from __future__ import annotations

import threading
from guardrailbench.adapters import register
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Verdict

MODEL_ID = "meta-llama/Llama-Guard-4-12B"
REVISION = "87acb4b94e930c3d679e6e7ee9d57e2feab9ea71"


def _part(role: str, text: str) -> dict:
    return {"role": role, "content": [{"type": "text", "text": text}]}


def build_input(messages: list[dict], target: int, mode: str) -> list[dict] | None:
    """None when the target has no text: classifying would judge the previous turn instead."""
    if mode == "flattened":
        text = to_text(messages, target)
        return [_part("user", text)] if text.strip() else None
    cur = messages[target]
    if cur["role"] not in ("user", "assistant") or not (cur.get("content") or "").strip():
        return None
    # native: the conversation up to the target, text user/assistant turns only
    return [_part(m["role"], m["content"]) for m in messages[:target + 1]
            if m["role"] in ("user", "assistant") and m.get("content")]


def parse_output(raw: str) -> Verdict:
    lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
    first = lines[0].lower() if lines else ""
    d = {"raw_text": raw, "categories": lines[1] if len(lines) > 1 else None}
    if first == "unsafe":
        return Verdict("block", None, raw=d)
    if first == "safe":
        return Verdict("allow", None, raw=d)
    return Verdict("error", None, raw=d, error=f"unparseable output {raw!r}")


class LlamaGuard4:
    name = "llama-guard-4"
    version = f"{MODEL_ID}@{REVISION[:12]}"
    native_checkpoints = frozenset({"prompt", "output"})
    accepts_text = True
    _lock = threading.Lock()
    parse_output = staticmethod(parse_output)

    def __init__(self):
        self._model = self._proc = None

    def _load(self):
        with self._lock:  # load once, even with parallel workers
            if self._model is None:
                import torch  # heavy; lazy
                from transformers import AutoProcessor, Llama4ForConditionalGeneration
                self._proc = AutoProcessor.from_pretrained(MODEL_ID, revision=REVISION)
                self._model = Llama4ForConditionalGeneration.from_pretrained(
                    MODEL_ID, revision=REVISION, device_map="auto", torch_dtype=torch.bfloat16)

    def warmup(self):
        """Called once by run() before any timed call."""
        self._load()

    def judge(self, messages, target, mode) -> Verdict:
        conv = build_input(messages, target, mode)
        if conv is None:
            return Verdict("error", error="empty target text")
        self._load()
        inputs = self._proc.apply_chat_template(
            conv, tokenize=True, add_generation_prompt=True,
            return_tensors="pt", return_dict=True).to(self._model.device)
        out = self._model.generate(**inputs, max_new_tokens=10, do_sample=False)
        text = self._proc.batch_decode(out[:, inputs["input_ids"].shape[-1]:], skip_special_tokens=True)[0]
        return parse_output(text)


register("llama-guard-4")(LlamaGuard4)

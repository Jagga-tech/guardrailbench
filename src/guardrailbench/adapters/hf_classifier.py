"""Hugging Face text-classification guardrails.

Sources (fetched 2026-11-05):
- https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M and ...-86M: binary benign/malicious
  classifier, decision = argmax (card defines no threshold), 512-token context, card says to split longer
  prompts into segments and scan all. Scope: user prompts and untrusted third-party data -> native
  {"prompt", "ingested_content"}. Label casing of the benign class is UNVERIFIED (gated).
- https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2: labels SAFE(0)/INJECTION(1)
  (config.json id2label), card usage truncates at max_length=512. Inputs: prompts -> native {"prompt"}.
- https://huggingface.co/qualifire/prompt-injection-sentinel: card shows label "jailbreak"; card prose
  says benign or malicious. "benign" label name UNVERIFIED (gated). Inputs: prompts -> native {"prompt"}.

Long inputs: text is split into windows of <=510 tokens (512 minus 2 special tokens, using the model's own
tokenizer at runtime). Every window is classified; the case is BLOCKED if any window blocks, and the case
score is the max malicious-class probability across windows. A label outside the model's known sets
yields an "error" verdict rather than a silent allow.

Heavy imports (transformers, torch) happen only when the model is first used.
"""
from __future__ import annotations

from guardrailbench.adapters import register
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Verdict

WINDOW = 510  # 512-token limit minus [CLS]/[SEP]


def build_input(messages: list[dict], target: int, mode: str) -> str:
    # Text classifiers see only text; native vs flattened differ only in labelling.
    return to_text(messages, target)


def make_windows(text: str, encode, decode, size: int = WINDOW) -> list[str]:
    ids = encode(text)
    if len(ids) <= size:
        return [text]
    return [decode(ids[i:i + size]) for i in range(0, len(ids), size)]


class HFClassifier:
    accepts_text = True

    def __init__(self, name, model_id, revision, native, block, allow):
        self.name, self.model_id, self.revision = name, model_id, revision
        self.version = f"{model_id}@{revision[:12]}"
        self.native_checkpoints = frozenset(native)
        self._block, self._allow = block, allow
        self._pipe = self._tok = None

    def parse_output(self, raw) -> Verdict:
        """raw: one list of {"label", "score"} dicts (all labels) per window."""
        best = 0.0
        blocked = False
        for win in raw:
            for r in win:
                lab = r["label"].lower()
                if lab in self._block:
                    best = max(best, r["score"])
                    # the winning label of the window decides, as argmax does on the card
                    if r["score"] >= max(x["score"] for x in win):
                        blocked = True
                elif lab not in self._allow:
                    return Verdict("error", raw={"windows": raw}, error=f"unknown label {r['label']!r}")
        return Verdict("block" if blocked else "allow", best, raw={"windows": raw})

    def _load(self):
        if self._pipe is None:
            from transformers import AutoTokenizer, pipeline  # heavy; lazy
            self._tok = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
            self._pipe = pipeline("text-classification", model=self.model_id, tokenizer=self._tok,
                                  revision=self.revision, truncation=True, max_length=512, top_k=None)
        return self._pipe

    def judge(self, messages, target, mode) -> Verdict:
        pipe = self._load()
        tok = self._tok
        wins = make_windows(build_input(messages, target, mode),
                            lambda t: tok.encode(t, add_special_tokens=False),
                            lambda i: tok.decode(i), WINDOW)
        out = pipe(wins)  # top_k=None: list (per window) of list of label dicts
        return self.parse_output(out)


_SPECS = {
    "prompt-guard-2-22m": ("meta-llama/Llama-Prompt-Guard-2-22M", "11614a155199674a0a95e6602d6ab0417b790ed0",
                           {"prompt", "ingested_content"}, {"malicious"}, {"benign"}),
    "prompt-guard-2-86m": ("meta-llama/Llama-Prompt-Guard-2-86M", "a8ded8e697ce7c355e395a0df51f94adb4a2fd27",
                           {"prompt", "ingested_content"}, {"malicious"}, {"benign"}),
    "protectai-deberta-v2": ("protectai/deberta-v3-base-prompt-injection-v2",
                             "90c9989b1a342275dd0d1a95aad283c04e075671", {"prompt"}, {"injection"}, {"safe"}),
    "qualifire-sentinel": ("qualifire/prompt-injection-sentinel", "e24131782819a4787c129ed2b9a4a67ae57a584e",
                           {"prompt"}, {"jailbreak"}, {"benign"}),
}

for _name, (_mid, _rev, _nat, _blk, _alw) in _SPECS.items():
    register(_name)(lambda n=_name, m=_mid, r=_rev, nat=_nat, b=_blk, a=_alw: HFClassifier(n, m, r, nat, b, a))

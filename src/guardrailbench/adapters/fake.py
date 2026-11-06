from __future__ import annotations

from guardrailbench.case import CHECKPOINTS
from guardrailbench.flatten import to_text
from guardrailbench.verdict import Verdict


class FakeAdapter:
    name = "fake"
    version = "0"

    def __init__(self, rules=("GRB-MARKER-",), native_checkpoints=None, accepts_text=True):
        self.rules = list(rules)
        self.native_checkpoints = frozenset(CHECKPOINTS if native_checkpoints is None else native_checkpoints)
        self.accepts_text = accepts_text

    def judge(self, messages, target, mode):
        text = to_text(messages, target)
        hit = any(r in text for r in self.rules)
        return Verdict("block" if hit else "allow", 1.0 if hit else 0.0)


from guardrailbench.adapters import register  # noqa: E402

register("fake")(FakeAdapter)

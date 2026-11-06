from __future__ import annotations

from typing import Callable

from guardrailbench.verdict import Adapter

ADAPTERS: dict[str, Callable[[], Adapter]] = {}


def register(name: str):
    def deco(factory):
        ADAPTERS[name] = factory
        return factory
    return deco


from guardrailbench.adapters import fake  # noqa: E402,F401  (registers "fake")
from guardrailbench.adapters import hf_classifier, llama_guard  # noqa: E402,F401  (register local models)
from guardrailbench.adapters import llamafirewall, nemo, llm_guard, invariant  # noqa: E402,F401  (agent guardrails)
from guardrailbench.adapters import lakera, azure_prompt_shields, bedrock, model_armor, openai_moderation  # noqa: E402,F401  (cloud APIs)

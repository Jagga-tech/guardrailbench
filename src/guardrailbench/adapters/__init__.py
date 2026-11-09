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

import importlib  # noqa: E402
import os  # noqa: E402

# Private adapters: GUARDRAILBENCH_PLUGINS="mod_a,mod_b" imports each module so it can call register().
for _mod in filter(None, (m.strip() for m in os.environ.get("GUARDRAILBENCH_PLUGINS", "").split(","))):
    importlib.import_module(_mod)

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

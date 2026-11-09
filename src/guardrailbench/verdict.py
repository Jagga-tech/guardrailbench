from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Verdict:
    decision: str  # allow | block | sanitize | unsure | error
    score: float | None = None
    sanitized: str | None = None
    raw: dict = field(default_factory=dict)
    latency_ms: float = 0.0
    error: str | None = None


class Adapter(Protocol):
    name: str
    version: str
    native_checkpoints: frozenset[str]
    accepts_text: bool
    # Optional: accepts_card (bool, default False). Set True to receive the deployment card on
    # the card track; products without it get not_applicable rows there.

    def judge(self, messages: list[dict], target: int, mode: str) -> Verdict:
        """mode is "native" or "flattened". On the card track the run loop also passes
        card=<deployment card> (only to adapters with accepts_card = True).
        Return decision "unsure" when the product abstains."""
        ...


class Retryable(Exception):
    """Raised by adapters for 429/5xx-type failures; the run loop retries these."""

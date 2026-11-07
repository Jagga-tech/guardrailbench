from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Verdict:
    decision: str  # allow | block | sanitize | error
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

    def judge(self, messages: list[dict], target: int, mode: str) -> Verdict:
        """mode is "native" or "flattened"."""
        ...


class Retryable(Exception):
    """Raised by adapters for 429/5xx-type failures; the run loop retries these."""

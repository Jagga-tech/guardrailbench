"""Shared JSON POST for the REST cloud adapters. 429 and 5xx (and network failures) raise Retryable."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from guardrailbench.verdict import Retryable


def post_json(url: str, headers: dict, body: dict, opener=None, timeout: float = 30) -> dict:
    """opener(request, timeout) -> file-like; defaults to urllib.request.urlopen. Tests inject a fake."""
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers},
                                 method="POST")
    try:
        with (opener or urllib.request.urlopen)(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429 or e.code >= 500:
            raise Retryable(f"HTTP {e.code}") from None
        raise RuntimeError(f"HTTP {e.code}") from None  # body not echoed: may contain request content
    except (urllib.error.URLError, TimeoutError) as e:
        raise Retryable(f"network: {e}") from None

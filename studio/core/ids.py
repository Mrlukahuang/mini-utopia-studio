from __future__ import annotations
import secrets
import time


def new_id(prefix: str) -> str:
    """Dependency-free, sortable-ish public ID. Display names may change; IDs never do."""
    millis = int(time.time() * 1000)
    return f"{prefix}_{millis:013X}{secrets.token_hex(5).upper()}"

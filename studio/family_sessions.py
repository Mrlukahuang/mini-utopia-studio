"""Parent-gated short-lived sessions; never persist tokens in a browser bundle."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time

SESSION_TTL_SECONDS = 900
MAX_FAILED_LOGINS = 5
WINDOW_SECONDS = 300
ITERATIONS = 310000


def make_verifier(passphrase: str, salt: bytes | None = None) -> str:
    if not 16 <= len(passphrase) <= 256:
        raise ValueError("Parent passphrase must be 16-256 characters")
    salt = salt or secrets.token_bytes(24)
    if len(salt) < 16:
        raise ValueError("Salt must be at least 16 bytes")
    digest = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, ITERATIONS)
    return "pbkdf2_sha256$%d$%s$%s" % (ITERATIONS, salt.hex(), digest.hex())


class ParentSessions:
    """In-memory random child tokens with bounded lifetime and failed logins."""

    def __init__(self, verifier: str, profiles, clock=time.monotonic):
        parts = verifier.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            raise ValueError("Invalid verifier")
        _, rounds, salt, digest = parts
        if not rounds.isdecimal() or not 310000 <= int(rounds) <= 2000000:
            raise ValueError("Invalid work factor")
        if len(salt) < 32 or len(digest) != 64:
            raise ValueError("Invalid verifier size")
        self.rounds = int(rounds)
        self.salt = bytes.fromhex(salt)
        self.digest = bytes.fromhex(digest)
        self.profiles = frozenset(profiles)
        if len(self.profiles) < 2:
            raise ValueError("Two profiles required")
        self.clock = clock
        self.lock = threading.Lock()
        self.failures = []
        self.sessions = {}

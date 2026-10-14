"""Offline, read-only checks before an adult starts the private family host.

Never prints credential values, reads child data, or contacts a network.
This is a configuration sanity check, not proof of real HTTPS deployment.
"""
from __future__ import annotations

import argparse
import os
import re
import stat
from pathlib import Path

KEYS = (
    "FAMILY_DOMAIN",
    "FAMILY_PARENT_UNLOCK_SHA256",
    "FAMILY_CHILD_A_TOKEN_SHA256",
    "FAMILY_CHILD_B_TOKEN_SHA256",
)
DIGEST = re.compile(r"[a-fA-F0-9]{64}\Z")
LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")


def _private_directory(path: Path, name: str) -> list[str]:
    if path.is_symlink() or not path.is_dir():
        return [f"{name}: missing or symlinked directory"]
    mode = path.stat().st_mode
    if os.name == "posix" and mode & 0o077:
        return [f"{name}: directory must not be accessible to group/others"]
    return []


def check_preflight(root: Path) -> list[str]:
    """Return safe, non-secret error descriptions; never mutate host state."""
    root = Path(root)
    problems: list[str] = []
    env_file = root / ".env"
    if env_file.is_symlink() or not env_file.is_file():
        return ["Configuration .env is missing or symlinked"]
    if os.name == "posix" and env_file.stat().st_mode & 0o077:
        problems.append("Configuration .env must have mode 0600 or stricter")
    values: dict[str, str] = {}
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                problems.append("Configuration contains a malformed line")
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in KEYS:
                continue
            if key in values:
                problems.append(f"Duplicate configuration key: {key}")
            values[key] = value.strip()
    except (OSError, UnicodeError):
        return ["Cannot read private configuration"]
    for key in KEYS:
        if key not in values:
            problems.append(f"Missing configuration key: {key}")
    domain = values.get("FAMILY_DOMAIN", "")
    if (
        len(domain) > 253
        or len(domain) < 4
        or "." not in domain
        or domain.lower() != domain
        or not all(LABEL.fullmatch(part) for part in domain.split("."))
        or domain.endswith(".local")
        or domain.endswith(".localhost")
        or domain.endswith(".example")
        or domain.endswith(".test")
        or domain.endswith(".invalid")
    ):
        problems.append("FAMILY_DOMAIN must be a production DNS hostname")
    digests = [values.get(key, "") for key in KEYS[1:]]
    if not all(DIGEST.fullmatch(digest) for digest in digests):
        problems.append("All three token digests must be 64 hexadecimal characters")
    elif len({digest.lower() for digest in digests}) != 3:
        problems.append("Parent and child token digests must all be different")
    web = root / "web"
    if web.is_symlink() or not web.is_dir():
        problems.append("Private Godot Web bundle directory is missing or symlinked")
    else:
        for filename in ("index.html", "index.js", "index.wasm", "index.pck"):
            item = web / filename
            if item.is_symlink() or not item.is_file() or item.stat().st_size == 0:
                problems.append(f"Missing or unsafe Web bundle file: {filename}")
    problems.extend(_private_directory(root / "private-movies", "Private movie store"))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only family host preflight")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    issues = check_preflight(args.root)
    for issue in issues:
        print("FAIL:", issue)
    if issues:
        print("Private host preflight FAILED; no service was started.")
        return 1
    print("Local configuration checks passed; real HTTPS and device testing still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

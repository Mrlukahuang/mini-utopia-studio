"""Read-only fail-closed review of the existing family API Docker mounts.

Input: a single redacted or local Docker inspect JSON document on stdin.
Never reads DB content, media, env, or a host path. Never creates a container.
"""
from __future__ import annotations
import json
import sys


def review(document: object) -> dict:
    if not isinstance(document, list) or len(document) != 1:
        raise ValueError("exactly one API inspect object required")
    api = document[0]
    if not isinstance(api, dict):
        raise ValueError("invalid inspect object")
    if api.get("Name") != "/mini-utopia-family-api-1":
        raise ValueError("not the expected API container")
    if api.get("State", {}).get("Running") is not True:
        raise ValueError("API is not running")
    user = str(api.get("Config", {}).get("User", ""))
    if user not in ("family", "10001", "10001:10001"):
        raise ValueError("unexpected API user")
    mounts = api.get("Mounts")
    if not isinstance(mounts, list):
        raise ValueError("missing mounts")
    data = [m for m in mounts if m.get("Destination") == "/data"]
    movies = [m for m in mounts if m.get("Destination") == "/movies"]
    if len(data) != 1 or len(movies) != 1:
        raise ValueError("ambiguous API mounts")
    d, m = data[0], movies[0]
    if d.get("Type") != "volume" or d.get("RW") is not True or not d.get("Name"):
        raise ValueError("expected named writable API database volume")
    if m.get("Type") != "bind" or m.get("RW") is not False or not m.get("Source"):
        raise ValueError("expected read-only API movie bind")
    if d.get("Source") == m.get("Source"):
        raise ValueError("movie and database sources overlap")
    # Never echo potentially sensitive Source/Name values into CI or issue logs.
    return {
        "api_running": True, "api_uid_contract": user,
        "data_mount": "named_volume_rw", "movies_mount": "bind_ro",
        "worker_mounts": "NEEDS_OWNER_AUTHORIZATION",
        "production_deployed": False,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(review(json.load(sys.stdin)), sort_keys=True))
    except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(2)

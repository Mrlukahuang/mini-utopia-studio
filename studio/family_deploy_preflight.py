"""Offline read-only preflight for a private, adult-provisioned family host.

Never publishes, starts containers, contacts DNS, prints env secrets or reads
any child's SQLite data. A passing result only means local packaging looks
safe; TLS, DNS and Mac/iPad Safari MUST still be verified by an adult.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
from pathlib import Path


EXPECTED_DIGESTS = (
    "FAMILY_PARENT_UNLOCK_SHA256",
    "FAMILY_CHILD_A_TOKEN_SHA256",
    "FAMILY_CHILD_B_TOKEN_SHA256",
)
REQUIRED_WEB = ("index.html", "index.js", "index.wasm", "index.pck")
REQUIRED_PACKAGE = ("compose.yaml", "Caddyfile", "Dockerfile")
RESERVED_SUFFIXES = (".example", ".invalid", ".test", ".localhost", ".local")


def _private_directory(path: Path) -> bool:
    if path.is_symlink() or not path.is_dir():
        return False
    st = path.stat()
    return (
        stat.S_ISDIR(st.st_mode)
        and (
            os.name != "posix"
            or (st.st_uid == os.getuid() and not st.st_mode & 0o077)
        )
    )


def _private_file(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    st = path.stat()
    return (
        stat.S_ISREG(st.st_mode)
        and (
            os.name != "posix"
            or (st.st_uid == os.getuid() and not st.st_mode & 0o077)
        )
    )


def _configured_domain(value: str) -> bool:
    domain = value.strip().lower()
    if len(domain) > 253 or not re.fullmatch(
        r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
        r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",
        domain,
    ):
        return False
    if domain in ("example.com", "example.net", "example.org"):
        return False
    if any(domain.endswith(suffix) for suffix in RESERVED_SUFFIXES):
        return False
    if domain.startswith("example.") or "localhost" in domain:
        return False
    return True


def audit_family_host_package(root: Path) -> dict:
    """Check an adult's local deploy directory; return *codes*, not values.

    This deliberately does not follow symlinks for secrets, movies, or Web
    export. Each issue is stable and suitable for a short checklist.
    """
    root = Path(root)
    issues: list[str] = []
    if root.is_symlink() or not root.is_dir():
        return {
            "schema_version": "1.0",
            "local_preflight_passed": False,
            "issues": ["deploy_directory_missing_or_symlinked"],
            "checked": [],
            "live_https_verified": False,
            "physical_ipad_verified": False,
        }

    checked = ["private_environment", "web_bundle", "media_permissions", "compose_files"]
    for part in REQUIRED_PACKAGE:
        file = root / part
        if file.is_symlink() or not file.is_file() or file.stat().st_size == 0:
            issues.append("required_package_file_missing")

    env_path = root / ".env"
    if not _private_file(env_path):
        issues.append("private_env_missing_or_exposed")
    else:
        try:
            raw = env_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            raw = ""
            issues.append("private_env_unreadable")
        pairs: dict[str, str] = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                issues.append("private_env_invalid_line")
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if key in pairs:
                issues.append("duplicate_environment_key")
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
                issues.append("private_env_invalid_line")
            pairs[key] = value
        if not _configured_domain(pairs.get("FAMILY_DOMAIN", "")):
            issues.append("family_domain_not_configured")
        digests = [pairs.get(key, "") for key in EXPECTED_DIGESTS]
        if not all(re.fullmatch(r"[a-fA-F0-9]{64}", item) for item in digests):
            issues.append("missing_or_invalid_secret_digest")
        elif len({x.lower() for x in digests}) != 3:
            issues.append("reused_child_or_parent_secret_digest")

    bundle = root / "web"
    if bundle.is_symlink() or not bundle.is_dir():
        issues.append("private_web_bundle_missing")
    else:
        for filename in REQUIRED_WEB:
            path = bundle / filename
            if (
                path.is_symlink() or not path.is_file()
                or path.stat().st_size < 32
            ):
                issues.append("web_export_incomplete")
                break

    media = root / "private-movies"
    if not _private_directory(media):
        issues.append("private_movie_directory_missing_or_exposed")

    return {
        "schema_version": "1.0",
        "local_preflight_passed": not issues,
        "issues": sorted(set(issues)),
        "checked": checked,
        "live_https_verified": False,
        "physical_ipad_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adult-only, offline family HTTPS host preflight"
    )
    parser.add_argument(
        "--deploy-dir", required=True, type=Path,
        help="Folder containing local .env, web export, private-movies and Compose",
    )
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        parser.error("Real family host preflight must not run in public CI")
    result = audit_family_host_package(args.deploy_dir)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["local_preflight_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

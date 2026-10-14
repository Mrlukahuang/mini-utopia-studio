"""Synthetic-only host packaging tests; no real family secrets or Web assets."""
import json
import os
from pathlib import Path

from studio.family_deploy_preflight import audit_family_host_package


def package(tmp_path):
    root = tmp_path / "deploy"
    root.mkdir()
    for filename in ("compose.yaml", "Caddyfile", "Dockerfile"):
        (root / filename).write_text("synthetic template", encoding="utf-8")
    web = root / "web"
    web.mkdir()
    for filename in ("index.html", "index.js", "index.wasm", "index.pck"):
        (web / filename).write_bytes(b"synthetic-web-artifact" * 30)
    movie = root / "private-movies"
    movie.mkdir(mode=0o700)
    digest_a = "a" * 64
    digest_b = "b" * 64
    digest_parent = "c" * 64
    env = root / ".env"
    env.write_text(
        "FAMILY_DOMAIN=family.valid-domain.nz\n"
        f"FAMILY_PARENT_UNLOCK_SHA256={digest_parent}\n"
        f"FAMILY_CHILD_A_TOKEN_SHA256={digest_a}\n"
        f"FAMILY_CHILD_B_TOKEN_SHA256={digest_b}\n",
        encoding="utf-8",
    )
    env.chmod(0o600)
    return root


def test_safe_host_passes_but_does_not_claim_tls_or_device_acceptance(tmp_path):
    root = package(tmp_path)
    result = audit_family_host_package(root)
    assert result["local_preflight_passed"] is True
    assert result["issues"] == []
    assert result["live_https_verified"] is False
    assert result["physical_ipad_verified"] is False
    assert set(result["checked"]) == {
        "private_environment", "web_bundle",
        "media_permissions", "compose_files",
    }
    result_text = json.dumps(result)
    assert "a" * 64 not in result_text
    assert "b" * 64 not in result_text
    assert "c" * 64 not in result_text
    assert "family.valid-domain.nz" not in result_text


def test_placeholder_domain_and_reused_keys_fail_closed(tmp_path):
    root = package(tmp_path)
    env = root / ".env"
    data = env.read_text().replace(
        "family.valid-domain.nz", "family.example.org"
    ).replace("b" * 64, "a" * 64)
    env.write_text(data)
    issues = audit_family_host_package(root)["issues"]
    assert "family_domain_not_configured" in issues
    assert "reused_child_or_parent_secret_digest" in issues


def test_missing_build_files_and_writable_private_movies_fail(tmp_path):
    root = package(tmp_path)
    (root / "web" / "index.wasm").unlink()
    movie = root / "private-movies"
    movie.chmod(0o755)
    issues = audit_family_host_package(root)["issues"]
    assert "web_export_incomplete" in issues
    if os.name == "posix":
        assert "private_movie_directory_missing_or_exposed" in issues


def test_env_permissions_and_missing_digest_are_rejected(tmp_path):
    root = package(tmp_path)
    env = root / ".env"
    env.chmod(0o644)
    if os.name == "posix":
        assert "private_env_missing_or_exposed" in audit_family_host_package(root)["issues"]
    env.chmod(0o600)
    env.write_text(
        "FAMILY_DOMAIN=family.valid-domain.nz\n"
        "FAMILY_PARENT_UNLOCK_SHA256=REPLACE_ME\n"
        "FAMILY_CHILD_A_TOKEN_SHA256=" + "a" * 64 + "\n"
        "FAMILY_CHILD_B_TOKEN_SHA256=" + "b" * 64 + "\n"
    )
    assert "missing_or_invalid_secret_digest" in audit_family_host_package(root)["issues"]


def test_does_not_follow_sensitive_symlinks(tmp_path):
    root = package(tmp_path)
    env = root / ".env"
    relocated = root / "env-backup"
    env.rename(relocated)
    env.symlink_to(relocated)
    assert "private_env_missing_or_exposed" in audit_family_host_package(root)["issues"]
    env.unlink()
    relocated.rename(env)

    media = root / "private-movies"
    outside = tmp_path / "elsewhere"
    media.rename(outside)
    media.symlink_to(outside, target_is_directory=True)
    assert "private_movie_directory_missing_or_exposed" in audit_family_host_package(root)["issues"]

    result = audit_family_host_package(tmp_path / "does-not-exist")
    assert result["issues"] == ["deploy_directory_missing_or_symlinked"]
    assert not result["local_preflight_passed"]


def test_duplicate_env_variable_does_not_echo_secret(tmp_path):
    root = package(tmp_path)
    env = root / ".env"
    env.write_text(env.read_text() + "FAMILY_DOMAIN=secret-note.invalid\n")
    result = audit_family_host_package(root)
    assert not result["local_preflight_passed"]
    assert "duplicate_environment_key" in result["issues"]
    assert "secret-note" not in json.dumps(result)

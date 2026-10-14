"""Deployment is opt-in: CI validates it without starting a public host."""

import os
import subprocess
import sys
from pathlib import Path

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.repositories.sqlite import SQLiteStudioRepository


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy" / "family"


def test_private_https_proxy_is_only_public_entrypoint():
    compose = (DEPLOY / "compose.yaml").read_text()
    caddy = (DEPLOY / "Caddyfile").read_text()
    dockerfile = (DEPLOY / "Dockerfile").read_text()
    assert 'network_mode: "service:api"' in compose
    assert "127.0.0.1:8766" in caddy
    assert "FAMILY_ALLOWED_ORIGINS: https://" in compose
    assert "FAMILY_PARENT_UNLOCK_SHA256" in compose
    assert "443:443" in compose and "80:80" in compose
    assert "family_data:/data" in compose
    assert "read_only: true" in compose
    assert "COPY studio /app/studio" in dockerfile
    assert "USER family" in dockerfile
    assert "/characters*" in caddy and "/family/sessions*" in caddy
    assert "root * /srv/web" in caddy
    assert "FAMILY_PARENT_UNLOCK_SHA256" not in dockerfile
    assert "localhost:8765" not in caddy


def test_deploy_example_does_not_ship_secrets():
    sample = (DEPLOY / ".env.example").read_text()
    assert "REPLACE_WITH" in sample
    assert "FAMILY_DOMAIN" in sample
    assert not (DEPLOY / ".env").exists()
    ignored = (DEPLOY / ".gitignore").read_text()
    assert ".env" in ignored and "web/" in ignored and "backups/" in ignored


def test_sqlite_backup_stream_is_consistent_and_restorable(tmp_path):
    db_path = tmp_path / "family-live.sqlite"
    repo = SQLiteStudioRepository(db_path)
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Synthetic Cloud Lamb",
        slug="synthetic-cloud-lamb",
        metadata={"family_owner": "child_a"},
    )
    repo.save_asset(asset)

    result = subprocess.run(
        [sys.executable, "-m", "studio.family_backup", str(db_path)],
        capture_output=True,
        check=True,
    )
    assert result.stdout.startswith(b"SQLite format 3\x00")
    assert result.stderr == b""
    restored_path = tmp_path / "restored.sqlite"
    restored_path.write_bytes(result.stdout)
    restored = SQLiteStudioRepository(restored_path)
    saved = restored.get_asset(asset.asset_id)
    assert saved is not None
    assert saved.display_name == "Synthetic Cloud Lamb"
    assert saved.metadata["family_owner"] == "child_a"


def test_sqlite_backup_refuses_missing_database(tmp_path):
    path = tmp_path / "missing.db"
    result = subprocess.run(
        [sys.executable, "-m", "studio.family_backup", str(path)],
        capture_output=True,
    )
    assert result.returncode != 0
    assert result.stdout == b""
    assert not path.exists()

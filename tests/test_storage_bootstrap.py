from pathlib import Path

import pytest

from studio.core.config import Settings
from studio.services.bootstrap import _build_storage
from studio.storage.local import LocalObjectStorage
from studio.storage.supabase import SupabaseObjectStorage


def _settings(tmp_path, **updates):
    values = dict(
        root_dir=tmp_path,
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "studio.db",
        app_env="test",
        openai_api_key=None,
        gemini_api_key=None,
    )
    values.update(updates)
    return Settings(**values)


def test_storage_factory_keeps_local_as_default(tmp_path):
    storage = _build_storage(_settings(tmp_path))
    assert isinstance(storage, LocalObjectStorage)


def test_storage_factory_builds_supabase_backend(tmp_path):
    storage = _build_storage(
        _settings(
            tmp_path,
            object_storage_backend="supabase",
            supabase_url="https://example.supabase.co",
            supabase_service_role_key="test-key",
            supabase_storage_bucket="mini-utopia-assets",
        )
    )
    assert isinstance(storage, SupabaseObjectStorage)
    assert storage.bucket == "mini-utopia-assets"


def test_storage_factory_rejects_incomplete_supabase_config(tmp_path):
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        _build_storage(
            _settings(
                tmp_path,
                object_storage_backend="supabase",
                supabase_url=None,
                supabase_service_role_key=None,
            )
        )


def test_storage_factory_rejects_unknown_backend(tmp_path):
    with pytest.raises(RuntimeError, match="Unsupported"):
        _build_storage(
            _settings(tmp_path, object_storage_backend="mystery")
        )

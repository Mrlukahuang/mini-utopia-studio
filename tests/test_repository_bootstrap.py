import pytest

from studio.core.config import Settings
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.repositories.supabase import SupabaseStudioRepository
from studio.services.bootstrap import _build_repository


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


def test_repository_factory_defaults_to_sqlite(tmp_path):
    repo = _build_repository(_settings(tmp_path))
    assert isinstance(repo, SQLiteStudioRepository)


def test_repository_factory_builds_supabase(tmp_path):
    repo = _build_repository(
        _settings(
            tmp_path,
            studio_repository_backend="supabase",
            supabase_url="https://example.supabase.co",
            supabase_service_role_key="test-key",
            supabase_metadata_table="studio_records",
        )
    )
    assert isinstance(repo, SupabaseStudioRepository)
    assert repo.table == "studio_records"


def test_repository_factory_rejects_incomplete_supabase_config(tmp_path):
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        _build_repository(
            _settings(
                tmp_path,
                studio_repository_backend="supabase",
                supabase_url=None,
                supabase_service_role_key=None,
            )
        )


def test_repository_factory_rejects_unknown_backend(tmp_path):
    with pytest.raises(RuntimeError, match="Unsupported"):
        _build_repository(
            _settings(tmp_path, studio_repository_backend="mystery")
        )

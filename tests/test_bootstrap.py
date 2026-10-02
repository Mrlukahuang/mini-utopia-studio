from pathlib import Path

from studio.core.config import Settings
from studio.services.bootstrap import build_context
from studio.services.style_service import StyleService


def test_build_context_exposes_style_service(tmp_path):
    settings = Settings(
        root_dir=tmp_path,
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "studio.db",
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_context(settings)

    assert isinstance(ctx.styles, StyleService)

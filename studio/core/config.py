from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    data_dir: Path
    database_path: Path
    app_env: str
    openai_api_key: str | None
    gemini_api_key: str | None
    openai_image_model: str = "gpt-image-2"
    openai_vision_model: str = "gpt-4o-mini"
    openai_text_model: str = "gpt-6-luna"
    object_storage_backend: str = "local"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "mini-utopia-assets"
    studio_repository_backend: str = "sqlite"
    supabase_metadata_table: str = "studio_records"


def get_settings(root_dir: Path | None = None) -> Settings:
    root = root_dir or Path(__file__).resolve().parents[2]
    data_dir = root / os.getenv("DATA_DIR", "data")
    database = root / os.getenv("DATABASE_PATH", "data/studio.db")
    return Settings(
        root_dir=root,
        data_dir=data_dir,
        database_path=database,
        app_env=os.getenv("APP_ENV", "development"),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        openai_image_model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
        openai_vision_model=os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"),
        openai_text_model=os.getenv("OPENAI_TEXT_MODEL", "gpt-6-luna"),
        object_storage_backend=os.getenv("OBJECT_STORAGE_BACKEND", "local").strip().lower(),
        supabase_url=os.getenv("SUPABASE_URL") or None,
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None,
        supabase_storage_bucket=os.getenv(
            "SUPABASE_STORAGE_BUCKET", "mini-utopia-assets"
        ),
        studio_repository_backend=os.getenv(
            "STUDIO_REPOSITORY_BACKEND", "sqlite"
        ).strip().lower(),
        supabase_metadata_table=os.getenv(
            "SUPABASE_METADATA_TABLE", "studio_records"
        ).strip(),
    )

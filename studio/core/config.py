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
    hero_asset_worker_url: str | None = None
    hero_asset_worker_token: str | None = None
    hero_asset_model: str = "pixal3d"
    hero_asset_timeout_seconds: float = 900.0
    hero_asset_max_per_world: int = 1
    hf_token: str | None = None
    hf_hero_space_id: str = "TencentARC/Pixal3D"
    hf_pixal3d_resolution: int = 1536
    hf_pixal3d_decimation_target: int = 500000
    hf_pixal3d_texture_size: int = 4096
    hf_pixal3d_seed: int = 42


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
        hero_asset_worker_url=os.getenv("HERO_ASSET_WORKER_URL") or None,
        hero_asset_worker_token=os.getenv("HERO_ASSET_WORKER_TOKEN") or None,
        hero_asset_model=os.getenv("HERO_ASSET_MODEL", "pixal3d").strip().lower(),
        hero_asset_timeout_seconds=float(
            os.getenv("HERO_ASSET_TIMEOUT_SECONDS", "900")
        ),
        hero_asset_max_per_world=int(
            os.getenv("HERO_ASSET_MAX_PER_WORLD", "1")
        ),
        hf_token=os.getenv("HF_TOKEN") or None,
        hf_hero_space_id=os.getenv(
            "HF_HERO_SPACE_ID", "TencentARC/Pixal3D"
        ).strip(),
        hf_pixal3d_resolution=int(
            os.getenv("HF_PIXAL3D_RESOLUTION", "1536")
        ),
        hf_pixal3d_decimation_target=int(
            os.getenv("HF_PIXAL3D_DECIMATION_TARGET", "500000")
        ),
        hf_pixal3d_texture_size=int(
            os.getenv("HF_PIXAL3D_TEXTURE_SIZE", "4096")
        ),
        hf_pixal3d_seed=int(
            os.getenv("HF_PIXAL3D_SEED", "42")
        ),
    )

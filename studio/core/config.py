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
    )

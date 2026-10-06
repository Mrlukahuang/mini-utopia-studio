from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field
from studio.core.enums import AssetType, ReviewStatus
from studio.core.ids import new_id


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


ASSET_PREFIX = {
    AssetType.CHARACTER: "CHAR",
    AssetType.LOCATION: "LOC",
    AssetType.PROP: "PROP",
    AssetType.WEARABLE: "WEAR",
    AssetType.EQUIPMENT: "EQ",
    AssetType.VEHICLE: "VEH",
    AssetType.STYLE: "STYLE",
    AssetType.VOICE: "VOICE",
    AssetType.MUSIC: "MUSIC",
}


class AssetFile(BaseModel):
    role: str
    path: str
    mime_type: str | None = None
    source_job_id: str | None = None


class Asset(BaseModel):
    asset_id: str
    asset_type: AssetType
    display_name: str
    slug: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    version: int = 1
    status: ReviewStatus = ReviewStatus.DRAFT
    favorite: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    files: list[AssetFile] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    @classmethod
    def create(cls, asset_type: AssetType, display_name: str, slug: str, **kwargs):
        return cls(
            asset_id=new_id(ASSET_PREFIX[asset_type]),
            asset_type=asset_type,
            display_name=display_name,
            slug=slug,
            **kwargs,
        )

"""Private canonical child-authored film draft contracts."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.repositories.base import StudioRepository
from studio.services.asset_service import slugify

class FamilyFilmDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    display_name: str = Field(min_length=1, max_length=64)
    character_id: str = Field(pattern=r"^CHAR_[A-Za-z0-9_-]{3,96}$")
    second_character_id: str | None = Field(
        default=None, pattern=r"^CHAR_[A-Za-z0-9_-]{3,96}$")
    camera: Literal["follow", "wide", "close"] = "follow"
    action: Literal["walk", "run", "celebrate"] = "walk"
    duration_seconds: Literal[15, 30] = 15
    private_story_note: str = Field(default="", max_length=280)

    @field_validator("display_name")
    @classmethod
    def normalize_name(cls, name: str) -> str:
        clean = name.strip()
        if not clean or any(ord(ch) < 32 for ch in clean):
            raise ValueError("Film title must be visible")
        return clean


def cast_is_owned(repository: StudioRepository, owner: str, draft: FamilyFilmDraft) -> bool:
    if draft.second_character_id == draft.character_id:
        return False
    for cid in (draft.character_id, draft.second_character_id):
        if cid is None:
            continue
        asset = repository.get_asset(cid)
        if (
            asset is None or asset.asset_type != AssetType.CHARACTER
            or asset.status == ReviewStatus.ARCHIVED
            or asset.metadata.get("family_owner") != owner
        ):
            return False
    return True


def film_contract(asset: Asset) -> dict:
    return {
        "schema_version": "1.0", "film_id": asset.asset_id,
        "revision": str(asset.version),
        "draft": asset.metadata["family_film_draft"],
    }


def save_film_draft(
    repository: StudioRepository, owner: str, draft: FamilyFilmDraft,
    existing: Asset | None = None,
) -> dict:
    if existing is None:
        asset = Asset.create(
            AssetType.FILM, display_name=draft.display_name,
            slug=slugify(draft.display_name), status=ReviewStatus.DRAFT,
            metadata={"family_owner": owner,
                      "family_film_draft": draft.model_dump(mode="json")},
        )
    else:
        asset = existing
        asset.display_name = draft.display_name
        asset.slug = slugify(draft.display_name)
        asset.metadata["family_film_draft"] = draft.model_dump(mode="json")
        asset.version += 1
    repository.save_asset(asset)
    return film_contract(asset)

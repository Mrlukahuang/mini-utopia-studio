"""Read-only private movie render inputs assembled from canonical Core assets.

Do not upload child media into public CI. A trusted private worker may consume
this JSON contract with Godot's family_movie_prepare.gd, using its own local
sandbox and a parent-approved render/download workflow.
"""
from __future__ import annotations

from pydantic import ValidationError

from studio.bridge.characters import CharacterBridgeReader
from studio.bridge.equipment import EquipmentBridgeGateway
from studio.core.enums import AssetType, ReviewStatus
from studio.family_films import FamilyFilmDraft, cast_is_owned
from studio.repositories.base import StudioRepository


def build_family_film_render_source(
    repository: StudioRepository, *, owner: str, film_id: str
) -> dict | None:
    """Return the minimum visual payload only while every asset stays owned."""
    film = repository.get_asset(film_id)
    if (
        film is None
        or film.asset_type != AssetType.FILM
        or film.status == ReviewStatus.ARCHIVED
        or film.metadata.get("family_owner") != owner
    ):
        return None
    try:
        draft = FamilyFilmDraft.model_validate(
            film.metadata["family_film_draft"]
        )
    except (KeyError, ValueError, ValidationError):
        return None
    if not cast_is_owned(repository, owner, draft):
        return None

    reader = CharacterBridgeReader(repository)
    equipment = EquipmentBridgeGateway(
        repository,
        collection_id="COLL_FAMILY_" + owner,
        owner_key=owner,
    )

    def render_actor(cid: str) -> tuple[dict, dict] | None:
        source = repository.get_asset(cid)
        if (
            source is None
            or source.asset_type != AssetType.CHARACTER
            or source.status == ReviewStatus.ARCHIVED
            or source.metadata.get("family_owner") != owner
        ):
            return None
        actor = reader._contract(source).model_dump(mode="json")
        appearance = {
            "schema_version": "1.0",
            "character_id": cid,
            "display_name": actor["display_name"],
            "profile": {"avatar": actor["profile"]["avatar"]},
        }
        state = equipment.get_state(cid)
        if state is None:
            return None
        runtime = state["runtime"]
        if runtime.get("character_asset_id") != cid:
            return None
        return appearance, runtime

    lead = render_actor(draft.character_id)
    if lead is None:
        return None
    result = {
        "schema_version": "1.0",
        "source_film_id": film_id,
        "source_revision": str(film.version),
        "character": lead[0],
        "equipment_runtime": lead[1],
        "director_choices": {
            "camera": draft.camera,
            "action": draft.action,
            "duration_seconds": draft.duration_seconds,
            "caption_preset": draft.caption_preset,
        },
        "fps": 2, "width": 480, "height": 270,
    }
    if draft.second_character_id is not None:
        second = render_actor(draft.second_character_id)
        if second is None:
            return None
        result["second_character"] = second[0]
        result["second_equipment_runtime"] = second[1]
    # Deliberately excludes a child's private story note, other asset IDs,
    # other saved films, private revisions or any child authorization token.
    return result

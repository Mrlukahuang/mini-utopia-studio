"""Explicit adult review of one immutable private family film render snapshot.

The approval is not publication consent. It authorizes only private rendering
of a precise film revision and current canonical actor+outfit state. A later
edit, change to an actor/prop, or loss of ownership invalidates it.
"""
from __future__ import annotations

import hashlib
import json

from studio.core.enums import AssetType, ReviewStatus
from studio.family_film_render import build_family_film_render_source
from studio.models.asset import now_utc
from studio.repositories.base import StudioRepository


def _film(repository: StudioRepository, owner: str, film_id: str):
    asset = repository.get_asset(film_id)
    if (
        asset is None
        or asset.asset_type != AssetType.FILM
        or asset.status == ReviewStatus.ARCHIVED
        or asset.metadata.get("family_owner") != owner
        or "family_film_draft" not in asset.metadata
    ):
        return None
    return asset


def _fingerprint(source: dict) -> str:
    encoded = json.dumps(
        source, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def current_review_state(
    repository: StudioRepository, *, owner: str, film_id: str,
) -> dict | None:
    asset = _film(repository, owner, film_id)
    if asset is None:
        return None
    review = asset.metadata.get("family_movie_review", {})
    source = build_family_film_render_source(
        repository, owner=owner, film_id=film_id
    )
    approved = (
        source is not None
        and isinstance(review, dict)
        and review.get("decision") == "approve"
        and review.get("revision") == str(asset.version)
        and review.get("fingerprint") == _fingerprint(source)
    )
    return {
        "schema_version": "1.0",
        "film_id": film_id,
        "revision": str(asset.version),
        "approved_for_private_render": bool(approved),
        "requires_parent_review": not approved,
    }


def decide_private_film_review(
    repository: StudioRepository, *,
    owner: str, film_id: str, revision: str, decision: str,
) -> dict | None:
    """Persist parent decision; caller must authenticate parent beforehand.

    Raises ValueError on stale revisions or invalid owner/asset state.
    """
    if decision not in ("approve", "revoke"):
        raise ValueError("invalid decision")
    asset = _film(repository, owner, film_id)
    if asset is None:
        return None
    if revision != str(asset.version):
        raise ValueError("revision_conflict")
    source = build_family_film_render_source(
        repository, owner=owner, film_id=film_id
    ) if decision == "approve" else None
    if decision == "approve" and source is None:
        return None
    asset.metadata["family_movie_review"] = {
        "schema_version": "1.0",
        "revision": revision,
        "decision": decision,
        "fingerprint": _fingerprint(source) if source is not None else "",
    }
    # Review does NOT increase the child's draft version; otherwise parent
    # review would cause the child's next optimistic film edit to conflict.
    asset.updated_at = now_utc()
    repository.save_asset(asset)
    return current_review_state(repository, owner=owner, film_id=film_id)

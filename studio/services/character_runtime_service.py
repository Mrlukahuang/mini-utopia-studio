from __future__ import annotations

from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.models.runtime_character import CharacterRuntimeSpec, RuntimeAnimationSpec


class CharacterRuntimeService:
    """Translate Canon Character data into the renderer-facing runtime contract."""

    def resolve(self, asset: Asset | None) -> CharacterRuntimeSpec:
        if asset is None:
            return CharacterRuntimeSpec()

        profile = CharacterProfile.model_validate(
            asset.metadata.get("character_profile", {})
        )
        runtime_meta = asset.metadata.get("runtime_3d", {}) or {}

        favorite = list(profile.favorite_color_hexes)
        body = favorite[0] if favorite else "#FFF4D7"
        accent = favorite[1] if len(favorite) > 1 else "#B9E7D0"

        model_data_uri = runtime_meta.get("model_data_uri")
        mode = "glb" if model_data_uri else "procedural"
        clips = runtime_meta.get("animation_clips", {}) or {}

        return CharacterRuntimeSpec(
            mode=mode,
            model_data_uri=model_data_uri,
            scale=float(runtime_meta.get("scale", 1.0)),
            animation_clips=RuntimeAnimationSpec(
                idle=clips.get("idle", "Idle"),
                walk=clips.get("walk", "Walk"),
                run=clips.get("run", "Run"),
            ),
            body_color_hex=body,
            accent_color_hex=accent,
            hair_color_hex=profile.hair_or_fur_color_hex or "#5B4036",
            eye_color_hex=profile.eyes.color_hex or "#7A5238",
        )

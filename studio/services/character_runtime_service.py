from __future__ import annotations

import base64

from studio.core.enums import AssetType
from studio.models.asset import Asset, AssetFile
from studio.models.character import CharacterProfile
from studio.models.runtime_character import CharacterRuntimeSpec, RuntimeAnimationSpec
from studio.repositories.base import StudioRepository
from studio.storage.base import ObjectStorage


class CharacterRuntimeService:
    """Translate Canon Character data into the renderer-facing runtime contract.

    Binary GLB data lives in ObjectStorage. Character metadata stores only a
    model_path and animation mapping, so Canon data stays lightweight.
    """

    def __init__(
        self,
        repository: StudioRepository,
        storage: ObjectStorage,
    ):
        self.repository = repository
        self.storage = storage

    def attach_glb(
        self,
        *,
        asset_id: str,
        payload: bytes,
        scale: float = 1.0,
        idle_clip: str = "Idle",
        walk_clip: str = "Walk",
        run_clip: str = "Run",
    ) -> Asset:
        asset = self.repository.get_asset(asset_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            raise ValueError(f"Character not found: {asset_id}")
        if not payload:
            raise ValueError("GLB payload is empty.")
        if payload[:4] != b"glTF":
            raise ValueError("File does not look like a binary glTF (.glb) asset.")

        path = self.storage.put_bytes(
            f"assets/{asset_id}/runtime/character.glb",
            payload,
        )

        for file_ref in asset.files:
            if file_ref.role == "character_runtime_glb":
                file_ref.role = "character_runtime_glb_archive"

        asset.files.append(
            AssetFile(
                role="character_runtime_glb",
                path=path,
                mime_type="model/gltf-binary",
            )
        )
        asset.metadata["runtime_3d"] = {
            "model_path": path,
            "scale": float(scale),
            "animation_clips": {
                "idle": idle_clip or "Idle",
                "walk": walk_clip or "Walk",
                "run": run_clip or "Run",
            },
        }
        self.repository.save_asset(asset)
        return asset

    def detach_glb(self, asset_id: str) -> Asset:
        asset = self.repository.get_asset(asset_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            raise ValueError(f"Character not found: {asset_id}")

        asset.metadata.pop("runtime_3d", None)
        for file_ref in asset.files:
            if file_ref.role == "character_runtime_glb":
                file_ref.role = "character_runtime_glb_archive"
        self.repository.save_asset(asset)
        return asset

    def _model_data_uri(self, model_path: str | None) -> str | None:
        if not model_path:
            return None
        try:
            payload = self.storage.get_bytes(model_path)
        except Exception:
            return None
        if not payload:
            return None
        encoded = base64.b64encode(payload).decode("ascii")
        return f"data:model/gltf-binary;base64,{encoded}"

    def resolve(self, asset: Asset | None) -> CharacterRuntimeSpec:
        if asset is None:
            return CharacterRuntimeSpec()

        raw_profile = asset.metadata.get("character_profile", {}) or {}
        profile = CharacterProfile.model_validate(raw_profile)
        runtime_meta = asset.metadata.get("runtime_3d", {}) or {}

        favorite = list(profile.favorite_color_hexes)
        has_avatar = isinstance(raw_profile, dict) and bool(raw_profile.get("avatar"))
        avatar = profile.avatar

        # Old Character records remain visually compatible until they are
        # explicitly upgraded in Character Builder v2.
        body = (
            avatar.surface_color_hex
            if has_avatar
            else (favorite[0] if favorite else "#FFF4D7")
        )
        accent = favorite[1] if len(favorite) > 1 else "#B9E7D0"
        hair = (
            avatar.hair_color_hex
            if has_avatar
            else (profile.hair_or_fur_color_hex or "#5B4036")
        )
        eyes = (
            avatar.eye_color_hex
            if has_avatar
            else (profile.eyes.color_hex or "#7A5238")
        )

        model_data_uri = runtime_meta.get("model_data_uri")
        if not model_data_uri:
            model_data_uri = self._model_data_uri(runtime_meta.get("model_path"))

        mode = "glb" if model_data_uri else "procedural"
        clips = runtime_meta.get("animation_clips", {}) or {}

        return CharacterRuntimeSpec(
            mode=mode,
            model_data_uri=model_data_uri,
            rig_family=avatar.rig_family,
            body_type=avatar.body_type,
            socket_names=tuple(socket.value for socket in __import__(
                "studio.models.avatar",
                fromlist=["AvatarSocket"],
            ).AvatarSocket),
            species_head_id=avatar.species_head_id,
            surface_type=avatar.surface_type,
            surface_color_hex=body,
            eye_style_id=avatar.eye_style_id,
            hair_style_id=avatar.hair_style_id,
            scale=float(runtime_meta.get("scale", 1.0)),
            animation_clips=RuntimeAnimationSpec(
                idle=clips.get("idle", "Idle"),
                walk=clips.get("walk", "Walk"),
                run=clips.get("run", "Run"),
            ),
            body_color_hex=body,
            accent_color_hex=accent,
            hair_color_hex=hair,
            eye_color_hex=eyes,
        )

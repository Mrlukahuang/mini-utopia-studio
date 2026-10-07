from __future__ import annotations

import hashlib
import json
from pathlib import Path

from studio.core.enums import AssetType
from studio.models.director_shot import (
    DirectorCameraSpec,
    DirectorShotSession,
)
from studio.models.play_session import PlaySessionRuntimeSpec
from studio.repositories.base import StudioRepository
from studio.services.baby_service import BabyService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.equipment_service import EquipmentService
from studio.services.play_session_service import CreatorPlaySessionService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GODOT_DIRECTOR_SESSION_PATH = (
    PROJECT_ROOT
    / "godot"
    / "runtime_state"
    / "director_shot_session.json"
)


class DirectorShotSessionService:
    """Build one deterministic Shot staging payload from canonical Creator state."""

    def __init__(
        self,
        repository: StudioRepository,
        character_runtime: CharacterRuntimeService,
        *,
        equipment: EquipmentService | None = None,
        babies: BabyService | None = None,
        export_path: str | Path | None = None,
    ):
        self.repository = repository
        self.character_runtime = character_runtime
        self.equipment = equipment or EquipmentService(repository)
        self.babies = babies or BabyService(repository)
        self.export_path = (
            Path(export_path)
            if export_path
            else DEFAULT_GODOT_DIRECTOR_SESSION_PATH
        )

    def build(
        self,
        *,
        episode_id: str,
        scene_id: str,
        shot_id: str,
    ) -> DirectorShotSession:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        scene = next(
            (value for value in episode.scenes if value.scene_id == scene_id),
            None,
        )
        if scene is None:
            raise ValueError(f"Scene not found: {scene_id}")

        shot = next(
            (value for value in scene.shots if value.shot_id == shot_id),
            None,
        )
        if shot is None:
            raise ValueError(f"Shot not found: {shot_id}")

        character_asset_id = self._character_asset_id(
            shot.asset_ids or scene.asset_ids or episode.asset_ids
        )
        world_asset_id = scene.location_asset_id or episode.world_asset_id

        play = CreatorPlaySessionService(
            self.repository,
            self.character_runtime,
            equipment=self.equipment,
            babies=self.babies,
        ).build(
            character_asset_id=character_asset_id,
            world_asset_id=world_asset_id,
        )

        # Runtime services may synthesize harmless timestamps (for example an
        # empty Creative Layout). Normalize all runtime timestamps to the
        # persisted Episode timestamp so unchanged source state is byte-stable.
        play_payload = play.model_dump(mode="json")
        self._normalize_timestamps(
            play_payload,
            episode.updated_at.isoformat(),
        )
        play_payload["source"] = "director"

        camera = self._camera_for_shot(
            shot_type=shot.shot_type,
            camera_text=shot.camera,
        )
        animation_intent = self._animation_intent(
            shot_type=shot.shot_type,
            action=shot.action,
        )

        stable_source = {
            "episode_id": episode.episode_id,
            "story_id": episode.story_id,
            "scene": scene.model_dump(mode="json"),
            "shot": shot.model_dump(mode="json"),
            "play_session": {
                key: value
                for key, value in play_payload.items()
                if key != "session_id"
            },
            "camera": camera.model_dump(mode="json"),
            "animation_intent": animation_intent,
        }
        digest = hashlib.sha256(
            json.dumps(
                stable_source,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest().upper()

        play_payload["session_id"] = f"DIRECTOR_PLAY_{digest[:16]}"
        play = PlaySessionRuntimeSpec.model_validate(play_payload)

        return DirectorShotSession(
            director_session_id=f"DIR_{digest[:20]}",
            source_fingerprint=digest,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            shot_id=shot.shot_id,
            story_id=episode.story_id,
            world_asset_id=world_asset_id,
            character_asset_id=character_asset_id,
            scene_title=scene.title,
            story_beat=scene.story_beat,
            duration_seconds=shot.duration_seconds,
            animation_intent=animation_intent,
            camera=camera,
            shot=shot,
            play_session=play,
        )

    def export(
        self,
        *,
        episode_id: str,
        scene_id: str,
        shot_id: str,
    ) -> DirectorShotSession:
        spec = self.build(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
        )
        spec.save_json(self.export_path)
        return spec

    def _character_asset_id(self, asset_ids: list[str]) -> str:
        for asset_id in asset_ids:
            asset = self.repository.get_asset(asset_id)
            if asset is not None and asset.asset_type == AssetType.CHARACTER:
                return asset.asset_id
        raise ValueError("Shot has no reusable Character asset.")

    @classmethod
    def _normalize_timestamps(
        cls,
        value,
        normalized_iso: str,
    ):
        if isinstance(value, dict):
            for key, item in list(value.items()):
                if key in {"created_at", "updated_at"}:
                    value[key] = normalized_iso
                else:
                    cls._normalize_timestamps(item, normalized_iso)
        elif isinstance(value, list):
            for item in value:
                cls._normalize_timestamps(item, normalized_iso)
        return value

    @staticmethod
    def _animation_intent(*, shot_type: str, action: str) -> str:
        text = f"{shot_type} {action}".lower()
        if any(word in text for word in ("attack", "battle", "fight", "strike")):
            return "attack"
        if any(word in text for word in ("run", "chase", "sprint")):
            return "run"
        if any(
            word in text
            for word in ("follow", "walk", "arrive", "enter", "explore", "approach")
        ):
            return "walk"
        return "idle"

    @staticmethod
    def _camera_for_shot(
        *,
        shot_type: str,
        camera_text: str,
    ) -> DirectorCameraSpec:
        text = f"{shot_type} {camera_text}".lower()
        if any(word in text for word in ("detail", "close", "reaction")):
            position = (0.8, 2.3, 3.8)
            look_at = (0.0, 1.25, 0.0)
            fov = 42.0
        elif "follow" in text:
            position = (2.2, 2.9, 5.5)
            look_at = (0.0, 1.1, -0.8)
            fov = 48.0
        elif any(word in text for word in ("portal", "hero", "wide", "establish")):
            position = (0.0, 4.2, 7.8)
            look_at = (0.0, 1.1, 0.0)
            fov = 52.0
        else:
            position = (1.4, 3.0, 5.2)
            look_at = (0.0, 1.2, 0.0)
            fov = 48.0

        return DirectorCameraSpec(
            position=position,
            look_at=look_at,
            fov=fov,
            movement=camera_text.strip(),
        )

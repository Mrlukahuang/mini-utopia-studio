from __future__ import annotations

import math

from studio.models.asset import now_utc
from studio.models.episode import (
    Episode,
    Shot,
    ShotBlockingPoint,
    ShotBlockingSpec,
    ShotCameraMotionSpec,
)
from studio.models.world import WorldBlueprint
from studio.repositories.base import StudioRepository
from studio.services.episode_service import EpisodeService


_BEAT_SHOTS = {
    "ARRIVE": (
        ("Establishing", 4.0, "Wide establishing · gentle push-in", "Introduce the World and entrance."),
        ("Follow", 3.0, "Medium follow · behind/3-quarter", "Follow the Character into the scene."),
    ),
    "DISCOVER": (
        ("Follow", 3.0, "Medium follow · slow pan", "Approach the discovery."),
        ("Reveal", 3.0, "Detail reveal · push-in", "Show the discovered clue or landmark clearly."),
    ),
    "PROBLEM": (
        ("Problem Wide", 3.5, "Wide 3-quarter · hold", "Reveal the obstacle and spatial stakes."),
        ("Reaction", 2.5, "Medium close · gentle push", "Show the Character reacting to the problem."),
    ),
    "ADVENTURE": (
        ("Action Follow", 4.0, "Follow camera · shoulder height", "Track the main action through the scene."),
        ("Action Detail", 3.0, "Medium/detail · controlled pan", "Show the decisive action or interaction."),
    ),
    "SURPRISE": (
        ("Reaction", 2.5, "Medium close · hold", "Capture the first reaction."),
        ("Surprise Reveal", 3.5, "Reveal wide · pull focus", "Reveal what makes the moment surprising."),
    ),
    "PORTAL": (
        ("Portal Reveal", 4.0, "Hero wide · slow push-in", "Reveal the Portal or final destination."),
        ("Ending", 4.0, "Wide ending · gentle pull-back", "Finish with a clear next-world hook."),
    ),
}


class ShotPlanService:
    """Deterministic Scene -> editable Shot List / Camera Plan."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository
        self.episodes = EpisodeService(repository)

    def build_for_episode(
        self,
        episode_id: str,
        *,
        replace: bool = False,
    ) -> Episode:
        episode = self.episodes.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        if not episode.scenes:
            raise ValueError(
                "Episode has no Scenes. Build Script & Scene Breakdown first."
            )
        if any(scene.shots for scene in episode.scenes) and not replace:
            return episode

        rebuilt = []
        for scene_index, scene in enumerate(episode.scenes, start=1):
            if not scene.description.strip() and not scene.action_summary.strip():
                rebuilt.append(scene.model_copy(update={"shots": []}))
                continue

            templates = _BEAT_SHOTS.get(
                scene.story_beat,
                (
                    ("Establishing", 3.5, "Wide establishing · hold", "Establish the scene."),
                    ("Action", 3.0, "Medium follow · 3-quarter", "Show the scene action."),
                ),
            )
            shots: list[Shot] = []
            for shot_index, (
                shot_type,
                duration,
                camera,
                purpose,
            ) in enumerate(templates, start=1):
                action = (
                    scene.action_summary.strip()
                    or scene.description.strip()
                )
                if shot_index == 1:
                    action = f"{purpose} {action}".strip()
                blocking = self._blocking_for(
                    episode=episode,
                    scene=scene,
                    shot_index=shot_index,
                    shot_type=shot_type,
                    action=action,
                )
                camera_motion = self._camera_motion_for(
                    blocking=blocking,
                    shot_type=shot_type,
                    camera_text=camera,
                )
                shots.append(
                    Shot(
                        shot_id=f"SHOT_{scene_index:02d}_{shot_index:02d}",
                        scene_id=scene.scene_id,
                        duration_seconds=duration,
                        asset_ids=list(scene.asset_ids),
                        shot_type=shot_type,
                        camera=camera,
                        action=action,
                        expression=self._expression_for_beat(
                            scene.story_beat,
                            shot_index,
                        ),
                        continuity_notes=[
                            *scene.continuity_notes,
                            f"Story beat: {scene.story_beat or 'SCENE'}",
                        ],
                        blocking=blocking,
                        camera_motion=camera_motion,
                    )
                )

            rebuilt.append(scene.model_copy(update={"shots": shots}))

        episode.scenes = rebuilt
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return episode

    def update_shot(
        self,
        *,
        episode_id: str,
        scene_id: str,
        shot_id: str,
        duration_seconds: float,
        shot_type: str,
        camera: str,
        action: str,
        expression: str,
        continuity_notes: list[str],
        blocking: ShotBlockingSpec | None = None,
        camera_motion: ShotCameraMotionSpec | None = None,
    ) -> Episode:
        episode = self.episodes.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        found = False
        updated_scenes = []
        for scene in episode.scenes:
            if scene.scene_id != scene_id:
                updated_scenes.append(scene)
                continue

            updated_shots = []
            for shot in scene.shots:
                if shot.shot_id != shot_id:
                    updated_shots.append(shot)
                    continue
                found = True
                updates = {
                    "duration_seconds": float(duration_seconds),
                    "shot_type": shot_type.strip(),
                    "camera": camera.strip(),
                    "action": action.strip(),
                    "expression": expression.strip(),
                    "continuity_notes": [
                        note.strip()
                        for note in continuity_notes
                        if note.strip()
                    ],
                }
                if blocking is not None:
                    updates["blocking"] = blocking.model_copy(
                        update={"source": "creator"}
                    )
                if camera_motion is not None:
                    updates["camera_motion"] = camera_motion.model_copy(
                        update={"source": "creator"}
                    )
                updated_shots.append(
                    shot.model_copy(update=updates)
                )
            updated_scenes.append(
                scene.model_copy(update={"shots": updated_shots})
            )

        if not found:
            raise ValueError(f"Shot not found: {shot_id}")

        # Validate the whole model so duration bounds and nested contracts run.
        episode = Episode.model_validate(
            episode.model_copy(
                update={
                    "scenes": updated_scenes,
                    "updated_at": now_utc(),
                }
            ).model_dump(mode="json")
        )
        self.repository.save_episode(episode)
        return episode

    def ensure_blocking(self, episode_id: str) -> Episode:
        episode = self.episodes.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        changed = False
        new_scenes = []
        for scene in episode.scenes:
            new_shots = []
            for index, shot in enumerate(scene.shots, start=1):
                if shot.blocking is not None:
                    new_shots.append(shot)
                    continue
                changed = True
                new_shots.append(
                    shot.model_copy(
                        update={
                            "blocking": self._blocking_for(
                                episode=episode,
                                scene=scene,
                                shot_index=index,
                                shot_type=shot.shot_type,
                                action=shot.action,
                            )
                        }
                    )
                )
            new_scenes.append(scene.model_copy(update={"shots": new_shots}))

        if not changed:
            return episode

        episode.scenes = new_scenes
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return episode

    def ensure_camera_motion(self, episode_id: str) -> Episode:
        episode = self.episodes.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        changed = False
        new_scenes = []
        for scene in episode.scenes:
            new_shots = []
            for index, shot in enumerate(scene.shots, start=1):
                blocking = shot.blocking
                if blocking is None:
                    blocking = self._blocking_for(
                        episode=episode,
                        scene=scene,
                        shot_index=index,
                        shot_type=shot.shot_type,
                        action=shot.action,
                    )
                    changed = True
                if shot.camera_motion is not None:
                    new_shots.append(
                        shot.model_copy(update={"blocking": blocking})
                    )
                    continue
                changed = True
                new_shots.append(
                    shot.model_copy(
                        update={
                            "blocking": blocking,
                            "camera_motion": self._camera_motion_for(
                                blocking=blocking,
                                shot_type=shot.shot_type,
                                camera_text=shot.camera,
                            ),
                        }
                    )
                )
            new_scenes.append(scene.model_copy(update={"shots": new_shots}))

        if not changed:
            return episode

        episode.scenes = new_scenes
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return episode

    def _blocking_for(
        self,
        *,
        episode: Episode,
        scene,
        shot_index: int,
        shot_type: str,
        action: str,
    ) -> ShotBlockingSpec:
        blueprint = self._blueprint_for(
            scene.location_asset_id or episode.world_asset_id
        )
        spawn_x = 0.0
        spawn_z = 0.0
        spawn_facing = 0.0
        confidence = 0.55
        if blueprint is not None:
            spawn_x = float(blueprint.spawn.x)
            spawn_z = float(blueprint.spawn.z)
            spawn_facing = float(blueprint.spawn.facing_degrees)
            confidence = 0.82

        beat = scene.story_beat or "SCENE"
        local_pairs = {
            "ARRIVE": [
                ((0.0, 0.0), (0.0, -5.0)),
                ((0.0, -5.0), (0.0, -8.0)),
            ],
            "DISCOVER": [
                ((0.0, -8.0), (2.5, -10.0)),
                ((2.5, -10.0), (2.5, -10.0)),
            ],
            "PROBLEM": [
                ((2.5, -10.0), (2.5, -12.0)),
                ((2.5, -12.0), (2.5, -12.0)),
            ],
            "ADVENTURE": [
                ((-2.0, -12.0), (3.5, -17.0)),
                ((3.5, -17.0), (5.0, -19.0)),
            ],
            "SURPRISE": [
                ((4.0, -18.0), (4.0, -18.0)),
                ((4.0, -18.0), (1.5, -20.0)),
            ],
            "PORTAL": [
                ((1.5, -20.0), (0.0, -24.0)),
                ((0.0, -24.0), (0.0, -24.0)),
            ],
        }
        pairs = local_pairs.get(
            beat,
            [
                ((0.0, 0.0), (0.0, -3.0)),
                ((0.0, -3.0), (0.0, -3.0)),
            ],
        )
        pair = pairs[min(max(shot_index - 1, 0), len(pairs) - 1)]

        start_x, start_z = self._rotate_offset(
            pair[0][0],
            pair[0][1],
            spawn_facing,
        )
        end_x, end_z = self._rotate_offset(
            pair[1][0],
            pair[1][1],
            spawn_facing,
        )
        start = ShotBlockingPoint(
            x=spawn_x + start_x,
            y=0.0,
            z=spawn_z + start_z,
        )
        end = ShotBlockingPoint(
            x=spawn_x + end_x,
            y=0.0,
            z=spawn_z + end_z,
        )

        if beat == "PORTAL" and blueprint is not None and blueprint.portal is not None:
            target = blueprint.portal.position
            end = ShotBlockingPoint(
                x=float(target.x),
                y=0.0,
                z=float(target.z),
            )
            if shot_index == 1:
                start = ShotBlockingPoint(
                    x=end.x,
                    y=end.y,
                    z=end.z + 5.0,
                )

        delta_x = end.x - start.x
        delta_z = end.z - start.z
        distance = math.hypot(delta_x, delta_z)
        text = f"{shot_type} {action}".lower()
        if distance <= 0.15 or any(
            word in text
            for word in ("reaction", "detail", "ending", "hold")
        ):
            movement_style = "hold"
            facing = spawn_facing
        else:
            movement_style = (
                "run"
                if any(word in text for word in ("run", "chase", "sprint"))
                else "walk"
            )
            facing = math.degrees(math.atan2(delta_x, -delta_z))

        return ShotBlockingSpec(
            actor_start=start,
            actor_end=end,
            facing_degrees=facing,
            movement_style=movement_style,
            source="generated",
            confidence=confidence,
        )

    def _blueprint_for(
        self,
        world_asset_id: str | None,
    ) -> WorldBlueprint | None:
        if not world_asset_id:
            return None
        asset = self.repository.get_asset(world_asset_id)
        if asset is None:
            return None
        raw = asset.metadata.get("world_blueprint")
        if not raw:
            return None
        return WorldBlueprint.model_validate(raw)

    @staticmethod
    def _rotate_offset(
        x_value: float,
        z_value: float,
        facing_degrees: float,
    ) -> tuple[float, float]:
        angle = math.radians(facing_degrees)
        cos_value = math.cos(angle)
        sin_value = math.sin(angle)
        return (
            x_value * cos_value - z_value * sin_value,
            x_value * sin_value + z_value * cos_value,
        )

    def _camera_motion_for(
        self,
        *,
        blocking: ShotBlockingSpec,
        shot_type: str,
        camera_text: str,
    ) -> ShotCameraMotionSpec:
        text = f"{shot_type} {camera_text}".lower()
        if "follow" in text:
            mode = "follow"
            offset = (2.2, 2.9, 5.5)
            start_fov = end_fov = 48.0
        elif "pull-back" in text or "pull back" in text:
            mode = "pull_back"
            offset = (0.0, 3.7, 5.4)
            start_fov, end_fov = 48.0, 54.0
        elif "pan" in text:
            mode = "pan"
            offset = (1.8, 3.0, 5.2)
            start_fov = end_fov = 47.0
        elif "reveal" in text:
            mode = "reveal"
            offset = (2.8, 3.5, 6.4)
            start_fov, end_fov = 50.0, 46.0
        elif (
            "push-in" in text
            or "push in" in text
            or "gentle push" in text
            or "slow push" in text
        ):
            mode = "push_in"
            offset = (0.0, 4.2, 7.8) if "wide" in text else (0.8, 2.5, 4.4)
            start_fov, end_fov = 52.0, 44.0
        else:
            mode = "hold"
            if any(word in text for word in ("detail", "close", "reaction")):
                offset = (0.8, 2.3, 3.8)
                start_fov = end_fov = 42.0
            elif any(word in text for word in ("wide", "establish", "portal", "hero")):
                offset = (0.0, 4.2, 7.8)
                start_fov = end_fov = 52.0
            else:
                offset = (1.4, 3.0, 5.2)
                start_fov = end_fov = 48.0

        start_anchor = blocking.actor_start
        end_anchor = blocking.actor_end
        start_position = self._camera_point_from_anchor(
            start_anchor,
            offset,
            blocking.facing_degrees,
        )
        end_position = self._camera_point_from_anchor(
            end_anchor,
            offset,
            blocking.facing_degrees,
        )
        start_look = ShotBlockingPoint(
            x=start_anchor.x,
            y=start_anchor.y + 1.15,
            z=start_anchor.z,
        )
        end_look = ShotBlockingPoint(
            x=end_anchor.x,
            y=end_anchor.y + 1.15,
            z=end_anchor.z,
        )

        if mode == "push_in":
            end_position = self._camera_point_from_anchor(
                end_anchor,
                (
                    offset[0] * 0.72,
                    max(1.8, offset[1] * 0.88),
                    offset[2] * 0.66,
                ),
                blocking.facing_degrees,
            )
        elif mode == "pull_back":
            end_position = self._camera_point_from_anchor(
                end_anchor,
                (
                    offset[0],
                    offset[1] * 1.16,
                    offset[2] * 1.48,
                ),
                blocking.facing_degrees,
            )
        elif mode == "pan":
            pan_x, pan_z = self._rotate_offset(
                2.4,
                0.0,
                blocking.facing_degrees,
            )
            end_look = ShotBlockingPoint(
                x=end_look.x + pan_x,
                y=end_look.y,
                z=end_look.z + pan_z,
            )
        elif mode == "reveal":
            reveal_x, reveal_z = self._rotate_offset(
                -2.8,
                -1.0,
                blocking.facing_degrees,
            )
            end_position = ShotBlockingPoint(
                x=end_position.x + reveal_x,
                y=end_position.y,
                z=end_position.z + reveal_z,
            )

        return ShotCameraMotionSpec(
            start_position=start_position,
            end_position=end_position,
            start_look_at=start_look,
            end_look_at=end_look,
            start_fov=start_fov,
            end_fov=end_fov,
            movement_mode=mode,
            easing="smooth",
            source="generated",
            confidence=min(1.0, blocking.confidence + 0.05),
        )

    def _camera_point_from_anchor(
        self,
        anchor: ShotBlockingPoint,
        offset: tuple[float, float, float],
        facing_degrees: float,
    ) -> ShotBlockingPoint:
        offset_x, offset_z = self._rotate_offset(
            offset[0],
            offset[2],
            facing_degrees,
        )
        return ShotBlockingPoint(
            x=anchor.x + offset_x,
            y=anchor.y + offset[1],
            z=anchor.z + offset_z,
        )

    @staticmethod
    def total_duration(episode: Episode) -> float:
        return sum(
            shot.duration_seconds
            for scene in episode.scenes
            for shot in scene.shots
        )

    @staticmethod
    def _expression_for_beat(beat: str, shot_index: int) -> str:
        primary = {
            "ARRIVE": "curious",
            "DISCOVER": "wonder",
            "PROBLEM": "determined",
            "ADVENTURE": "focused",
            "SURPRISE": "surprised",
            "PORTAL": "hopeful",
        }.get(beat, "engaged")
        return primary if shot_index == 1 else f"{primary} / reaction"

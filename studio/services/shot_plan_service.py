from __future__ import annotations

from studio.models.asset import now_utc
from studio.models.episode import Episode, Shot
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
                updated_shots.append(
                    shot.model_copy(
                        update={
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
                    )
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

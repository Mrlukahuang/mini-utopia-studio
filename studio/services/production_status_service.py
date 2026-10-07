from __future__ import annotations

from studio.models.production_status import EpisodeProductionStatus
from studio.repositories.base import StudioRepository
from studio.services.storyboard_service import StoryboardService


class EpisodeProductionStatusService:
    """Derive child-visible production progress from durable Episode state."""

    def __init__(
        self,
        repository: StudioRepository,
        storyboard: StoryboardService,
    ):
        self.repository = repository
        self.storyboard = storyboard

    def status(self, episode_id: str) -> EpisodeProductionStatus:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        story_ready = self.repository.get_story(episode.story_id) is not None

        scenes_total = len(episode.scenes)
        scenes_ready = sum(
            bool(scene.description.strip() or scene.action_summary.strip())
            for scene in episode.scenes
        )

        shots = [
            (scene, shot)
            for scene in episode.scenes
            for shot in scene.shots
        ]
        shots_total = len(shots)
        shots_ready = sum(
            bool(
                shot.blocking is not None
                and shot.camera_motion is not None
                and shot.performance_cues is not None
            )
            for _scene, shot in shots
        )

        storyboard_ready = 0
        storyboard_approved = 0
        storyboard_needs_change = 0
        storyboard_stale = 0

        for scene, shot in shots:
            frame = self.storyboard.status_for(
                episode_id=episode.episode_id,
                scene_id=scene.scene_id,
                shot_id=shot.shot_id,
            )
            if frame.status == "ready":
                storyboard_ready += 1
                if frame.approved_current:
                    storyboard_approved += 1
                elif (
                    frame.review_status == "needs_change"
                    and frame.review_source_fingerprint
                    == frame.source_fingerprint
                ):
                    storyboard_needs_change += 1
            elif frame.status == "stale":
                storyboard_stale += 1

        rendered_ids = set(
            getattr(episode, "rendered_shot_ids", []) or []
        )
        shot_ids = {shot.shot_id for _scene, shot in shots}
        rendered_shots = len(rendered_ids.intersection(shot_ids))
        final_package_ready = bool(
            getattr(episode, "final_package_ready", False)
        )

        next_action = self._next_action(
            scenes_total=scenes_total,
            shots_total=shots_total,
            shots_ready=shots_ready,
            storyboard_ready=storyboard_ready,
            storyboard_approved=storyboard_approved,
            rendered_shots=rendered_shots,
            final_package_ready=final_package_ready,
        )

        progress_percent = self._progress_percent(
            story_ready=story_ready,
            scenes_total=scenes_total,
            scenes_ready=scenes_ready,
            shots_total=shots_total,
            shots_ready=shots_ready,
            storyboard_ready=storyboard_ready,
            storyboard_approved=storyboard_approved,
            rendered_shots=rendered_shots,
            final_package_ready=final_package_ready,
        )

        return EpisodeProductionStatus(
            episode_id=episode.episode_id,
            story_ready=story_ready,
            scenes_ready=scenes_ready,
            scenes_total=scenes_total,
            shots_ready=shots_ready,
            shots_total=shots_total,
            storyboard_ready=storyboard_ready,
            storyboard_approved=storyboard_approved,
            storyboard_needs_change=storyboard_needs_change,
            storyboard_stale=storyboard_stale,
            rendered_shots=rendered_shots,
            final_package_ready=final_package_ready,
            next_action=next_action,
            progress_percent=progress_percent,
        )

    @staticmethod
    def _next_action(
        *,
        scenes_total: int,
        shots_total: int,
        shots_ready: int,
        storyboard_ready: int,
        storyboard_approved: int,
        rendered_shots: int,
        final_package_ready: bool,
    ) -> str:
        if scenes_total == 0:
            return "build_scenes"
        if shots_total == 0 or shots_ready < shots_total:
            return "build_shots"
        if storyboard_ready < shots_total:
            return "generate_storyboard"
        if storyboard_approved < shots_total:
            return "review_storyboard"
        if rendered_shots < shots_total:
            return "render_shots"
        if not final_package_ready:
            return "assemble_episode"
        return "complete"

    @staticmethod
    def _progress_percent(
        *,
        story_ready: bool,
        scenes_total: int,
        scenes_ready: int,
        shots_total: int,
        shots_ready: int,
        storyboard_ready: int,
        storyboard_approved: int,
        rendered_shots: int,
        final_package_ready: bool,
    ) -> int:
        stages = [
            1.0 if story_ready else 0.0,
            (
                scenes_ready / scenes_total
                if scenes_total
                else 0.0
            ),
            (
                shots_ready / shots_total
                if shots_total
                else 0.0
            ),
            (
                storyboard_ready / shots_total
                if shots_total
                else 0.0
            ),
            (
                storyboard_approved / shots_total
                if shots_total
                else 0.0
            ),
            (
                rendered_shots / shots_total
                if shots_total
                else 0.0
            ),
            1.0 if final_package_ready else 0.0,
        ]
        return round(sum(stages) / len(stages) * 100)

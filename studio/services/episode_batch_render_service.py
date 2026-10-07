from __future__ import annotations

from studio.models.episode_batch_render import EpisodeBatchRenderResult
from studio.repositories.base import StudioRepository
from studio.services.shot_render_service import ShotRenderService
from studio.services.storyboard_service import StoryboardService


class EpisodeBatchRenderService:
    """Render all current approved Shots without redoing successful clips."""

    def __init__(
        self,
        repository: StudioRepository,
        storyboard: StoryboardService,
        shot_renderer: ShotRenderService,
    ):
        self.repository = repository
        self.storyboard = storyboard
        self.shot_renderer = shot_renderer

    def render_episode(self, episode_id: str) -> EpisodeBatchRenderResult:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        shots = [
            (scene, shot)
            for scene in episode.scenes
            for shot in scene.shots
        ]
        result = EpisodeBatchRenderResult(
            episode_id=episode_id,
            total_shots=len(shots),
        )

        for scene, shot in shots:
            frame = self.storyboard.status_for(
                episode_id=episode_id,
                scene_id=scene.scene_id,
                shot_id=shot.shot_id,
            )
            if not frame.approved_current:
                result.blocked_shots.append(shot.shot_id)
                continue

            result.eligible_shots += 1
            status = self.shot_renderer.status_for(
                episode_id=episode_id,
                scene_id=scene.scene_id,
                shot_id=shot.shot_id,
            )
            if status.status == "rendered":
                result.already_rendered += 1
                continue

            rendered = self.shot_renderer.render_shot(
                episode_id=episode_id,
                scene_id=scene.scene_id,
                shot_id=shot.shot_id,
            )
            if rendered.status == "rendered":
                result.rendered_now += 1
            else:
                result.failed_shots.append(shot.shot_id)

        return result

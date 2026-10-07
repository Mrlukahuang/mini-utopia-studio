from __future__ import annotations

from studio.models.asset import now_utc
from studio.models.episode import Episode, Scene
from studio.repositories.base import StudioRepository
from studio.services.episode_service import EpisodeService


BEAT_ORDER = (
    ("ARRIVE", "hook"),
    ("DISCOVER", "discovery"),
    ("PROBLEM", "conflict"),
    ("ADVENTURE", "adventure"),
    ("SURPRISE", "twist"),
    ("PORTAL", "ending"),
)


class SceneBreakdownService:
    """Deterministic Story -> ordered Episode Scene breakdown."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository
        self.episodes = EpisodeService(repository)

    def build_from_story(
        self,
        episode_id: str,
        *,
        replace: bool = False,
    ) -> Episode:
        episode = self.episodes.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        if episode.scenes and not replace:
            return episode

        story = self.repository.get_story(episode.story_id)
        if story is None:
            raise ValueError(f"Story not found: {episode.story_id}")

        scenes: list[Scene] = []
        for index, (beat_label, field_name) in enumerate(BEAT_ORDER, start=1):
            text = str(getattr(story, field_name, "") or "").strip()
            if not text:
                continue
            scene_number = len(scenes) + 1
            scenes.append(
                Scene(
                    scene_id=f"SCENE_{scene_number:02d}",
                    title=f"{beat_label.title()} · {story.title}",
                    story_beat=beat_label,
                    location_asset_id=episode.world_asset_id,
                    asset_ids=list(episode.asset_ids),
                    description=text,
                    action_summary=text,
                    dialogue_notes=(
                        "Add dialogue or narration only where it helps the beat."
                    ),
                    continuity_notes=[
                        f"Source Story: {story.story_id}",
                        f"Beat: {beat_label}",
                    ],
                )
            )

        episode.scenes = scenes
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return episode

    def update_scene(
        self,
        *,
        episode_id: str,
        scene_id: str,
        title: str,
        description: str,
        action_summary: str,
        dialogue_notes: str,
        continuity_notes: list[str],
    ) -> Episode:
        episode = self.episodes.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        found = False
        updated_scenes: list[Scene] = []
        for scene in episode.scenes:
            if scene.scene_id != scene_id:
                updated_scenes.append(scene)
                continue
            found = True
            updated_scenes.append(
                scene.model_copy(
                    update={
                        "title": title.strip(),
                        "description": description.strip(),
                        "action_summary": action_summary.strip(),
                        "dialogue_notes": dialogue_notes.strip(),
                        "continuity_notes": [
                            note.strip()
                            for note in continuity_notes
                            if note.strip()
                        ],
                    }
                )
            )
        if not found:
            raise ValueError(f"Scene not found: {scene_id}")

        episode.scenes = updated_scenes
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return episode

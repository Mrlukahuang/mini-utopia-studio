from __future__ import annotations

from studio.core.enums import AssetType, StoryMode
from studio.core.ids import new_id
from studio.models.episode import Episode
from studio.repositories.base import StudioRepository
from studio.services.baby_service import DEFAULT_BABY_ROSTER_ID
from studio.services.living_universe_memory_service import (
    LivingUniverseMemoryService,
)


class EpisodeService:
    """Create production Episodes that reference, never copy, Story assets."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def list_episodes(self) -> list[Episode]:
        try:
            return self.repository.list_episodes()
        except NotImplementedError:
            return []

    def get_episode(self, episode_id: str) -> Episode | None:
        try:
            return self.repository.get_episode(episode_id)
        except NotImplementedError:
            return None

    def existing_for_story(self, story_id: str) -> Episode | None:
        return next(
            (
                episode
                for episode in self.list_episodes()
                if episode.story_id == story_id
            ),
            None,
        )

    def create_from_story(self, story_id: str) -> Episode:
        existing = self.existing_for_story(story_id)
        if existing is not None:
            return existing

        story = self.repository.get_story(story_id)
        if story is None:
            raise ValueError(f"Story not found: {story_id}")

        world_asset_id = next(
            (
                asset_id
                for asset_id in story.asset_ids
                if (
                    (asset := self.repository.get_asset(asset_id)) is not None
                    and asset.asset_type == AssetType.LOCATION
                )
            ),
            None,
        )

        roster = self.repository.get_baby_roster(DEFAULT_BABY_ROSTER_ID)
        active_baby = roster.active_baby() if roster is not None else None

        continuity_memory_ids: list[str] = []
        if story.mode == StoryMode.CANON and story.universe_id:
            try:
                continuity_memory_ids = [
                    memory.memory_id
                    for memory in LivingUniverseMemoryService(
                        self.repository
                    ).query(
                        universe_id=story.universe_id,
                        asset_ids=list(story.asset_ids),
                        world_asset_id=world_asset_id,
                        limit=20,
                    )
                ]
            except NotImplementedError:
                continuity_memory_ids = []

        episode = Episode(
            episode_id=new_id("EP"),
            universe_id=story.universe_id,
            story_id=story.story_id,
            title=story.title,
            mode=story.mode,
            asset_ids=list(story.asset_ids),
            world_asset_id=world_asset_id,
            active_baby_id=(
                active_baby.baby_id
                if active_baby is not None
                else None
            ),
            continuity_memory_ids=continuity_memory_ids,
        )
        try:
            self.repository.save_episode(episode)
        except NotImplementedError as exc:
            raise RuntimeError(
                "Episode persistence is unavailable for this repository."
            ) from exc
        return episode

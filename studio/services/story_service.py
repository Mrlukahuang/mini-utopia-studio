from studio.core.enums import StoryMode, ReviewStatus
from studio.core.ids import new_id
from studio.models.story import Story
from studio.repositories.base import StudioRepository
from studio.services.living_universe_memory_service import (
    LivingUniverseMemoryService,
)


class StoryService:
    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def create_story(
        self,
        *,
        title: str,
        premise: str,
        mode: StoryMode,
        asset_ids: list[str],
        universe_id: str | None = None,
        hook: str = "",
        discovery: str = "",
        conflict: str = "",
        adventure: str = "",
        twist: str = "",
        ending: str = "",
    ) -> Story:
        story = Story(
            story_id=new_id("STORY"),
            title=title,
            premise=premise,
            mode=mode,
            universe_id=universe_id,
            asset_ids=list(dict.fromkeys(asset_ids)),
            hook=hook,
            discovery=discovery,
            conflict=conflict,
            adventure=adventure,
            twist=twist,
            ending=ending,
            status=ReviewStatus.DRAFT,
        )
        self.repository.save_story(story)
        if story.mode == StoryMode.CANON:
            try:
                LivingUniverseMemoryService(
                    self.repository
                ).ingest_story(story)
            except NotImplementedError:
                # Transitional/custom repositories may not expose Living
                # Memory yet; Story persistence must remain backward compatible.
                pass
        return story

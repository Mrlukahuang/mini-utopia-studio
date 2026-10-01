from studio.core.enums import StoryMode, ReviewStatus
from studio.core.ids import new_id
from studio.models.story import Story
from studio.repositories.base import StudioRepository


class StoryService:
    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def create_story(self, *, title: str, premise: str, mode: StoryMode, asset_ids: list[str], universe_id: str | None = None) -> Story:
        story = Story(
            story_id=new_id("STORY"),
            title=title,
            premise=premise,
            mode=mode,
            universe_id=universe_id,
            asset_ids=asset_ids,
            status=ReviewStatus.DRAFT,
        )
        self.repository.save_story(story)
        return story

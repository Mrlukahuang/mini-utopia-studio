from studio.core.enums import StoryMode
from studio.services.story_service import StoryService


class StoryBuilderRecipe:
    def __init__(self, story_service: StoryService):
        self.story_service = story_service

    def save_playground(self, *, title: str, premise: str, asset_ids: list[str]):
        return self.story_service.create_story(
            title=title,
            premise=premise,
            mode=StoryMode.PLAYGROUND,
            asset_ids=asset_ids,
        )

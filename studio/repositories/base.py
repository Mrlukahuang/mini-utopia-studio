from __future__ import annotations
from abc import ABC, abstractmethod
from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.universe import Universe
from studio.models.story import Story
from studio.models.job import Job
from studio.models.equipment import CreatorCollection
from studio.models.baby import BabyRoster
from studio.models.quest import QuestDefinition
from studio.models.universe_memory import UniverseMemoryRecord
from studio.models.episode import Episode


class StudioRepository(ABC):
    @abstractmethod
    def save_asset(self, asset: Asset) -> None: ...
    @abstractmethod
    def get_asset(self, asset_id: str) -> Asset | None: ...
    @abstractmethod
    def list_assets(self, asset_type: AssetType | None = None) -> list[Asset]: ...
    @abstractmethod
    def save_universe(self, universe: Universe) -> None: ...
    @abstractmethod
    def get_universe(self, universe_id: str) -> Universe | None: ...
    @abstractmethod
    def list_universes(self) -> list[Universe]: ...
    @abstractmethod
    def save_story(self, story: Story) -> None: ...
    @abstractmethod
    def get_story(self, story_id: str) -> Story | None: ...
    @abstractmethod
    def list_stories(self) -> list[Story]: ...
    @abstractmethod
    def save_collection(self, collection: CreatorCollection) -> None: ...
    @abstractmethod
    def get_collection(self, collection_id: str) -> CreatorCollection | None: ...
    def save_baby_roster(self, roster: BabyRoster) -> None:
        raise NotImplementedError

    def get_baby_roster(self, roster_id: str) -> BabyRoster | None:
        raise NotImplementedError

    def save_quest(self, quest: QuestDefinition) -> None:
        raise NotImplementedError

    def get_quest(self, quest_id: str) -> QuestDefinition | None:
        raise NotImplementedError

    def list_quests(self) -> list[QuestDefinition]:
        raise NotImplementedError

    def save_episode(self, episode: Episode) -> None:
        raise NotImplementedError

    def get_episode(self, episode_id: str) -> Episode | None:
        raise NotImplementedError

    def list_episodes(self) -> list[Episode]:
        raise NotImplementedError

    def save_universe_memory(self, memory: UniverseMemoryRecord) -> None:
        raise NotImplementedError

    def get_universe_memory(
        self,
        memory_id: str,
    ) -> UniverseMemoryRecord | None:
        raise NotImplementedError

    def list_universe_memories(
        self,
        universe_id: str | None = None,
    ) -> list[UniverseMemoryRecord]:
        raise NotImplementedError

    @abstractmethod
    def save_job(self, job: Job) -> None: ...
    @abstractmethod
    def list_jobs(self) -> list[Job]: ...

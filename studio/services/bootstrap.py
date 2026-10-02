from dataclasses import dataclass
from studio.core.config import Settings
from studio.plugins.base import PluginRegistry
from studio.plugins.mock.creative import MockCharacterParsePlugin, MockTurnaroundPlugin
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.asset_service import AssetService
from studio.services.story_service import StoryService
from studio.services.style_service import StyleService
from studio.services.universe_service import UniverseService
from studio.services.job_service import JobService
from studio.storage.local import LocalObjectStorage


@dataclass
class StudioContext:
    settings: Settings
    repository: SQLiteStudioRepository
    storage: LocalObjectStorage
    registry: PluginRegistry
    assets: AssetService
    stories: StoryService
    styles: StyleService
    universes: UniverseService
    jobs: JobService


def build_context(settings: Settings) -> StudioContext:
    repository = SQLiteStudioRepository(settings.database_path)
    storage = LocalObjectStorage(settings.data_dir)
    registry = PluginRegistry()
    registry.register(MockCharacterParsePlugin())
    registry.register(MockTurnaroundPlugin())
    return StudioContext(
        settings=settings,
        repository=repository,
        storage=storage,
        registry=registry,
        assets=AssetService(repository),
        stories=StoryService(repository),
        styles=StyleService(repository),
        universes=UniverseService(repository),
        jobs=JobService(repository),
    )

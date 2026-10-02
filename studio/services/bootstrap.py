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
from studio.services.reference_character_service import ReferenceCharacterService
from studio.services.character_master_prompt_service import CharacterMasterPromptService
from studio.services.character_master_service import CharacterMasterService
from studio.services.world_concept_prompt_service import WorldConceptPromptService
from studio.services.world_concept_service import WorldConceptService
from studio.providers.openai_image import OpenAIImageProvider
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
    references: ReferenceCharacterService
    character_master_prompts: CharacterMasterPromptService
    character_masters: CharacterMasterService
    world_concept_prompts: WorldConceptPromptService
    world_concepts: WorldConceptService


def build_context(settings: Settings) -> StudioContext:
    repository = SQLiteStudioRepository(settings.database_path)
    storage = LocalObjectStorage(settings.data_dir)
    registry = PluginRegistry()
    registry.register(MockCharacterParsePlugin())
    registry.register(MockTurnaroundPlugin())

    character_master_prompts = CharacterMasterPromptService()
    world_concept_prompts = WorldConceptPromptService()
    image_provider = (
        OpenAIImageProvider(
            settings.openai_api_key,
            model=settings.openai_image_model,
        )
        if settings.openai_api_key
        else None
    )

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
        references=ReferenceCharacterService(repository, storage),
        character_master_prompts=character_master_prompts,
        character_masters=CharacterMasterService(
            repository,
            storage,
            character_master_prompts,
            image_provider=image_provider,
        ),
        world_concept_prompts=world_concept_prompts,
        world_concepts=WorldConceptService(
            repository,
            storage,
            world_concept_prompts,
            image_provider=image_provider,
        ),
    )

from dataclasses import dataclass
from studio.core.config import Settings
from studio.plugins.base import PluginRegistry
from studio.plugins.mock.creative import MockCharacterParsePlugin, MockTurnaroundPlugin
from studio.repositories.base import StudioRepository
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.repositories.supabase import SupabaseStudioRepository
from studio.services.asset_service import AssetService
from studio.services.story_service import StoryService
from studio.services.style_service import StyleService
from studio.services.universe_service import UniverseService
from studio.services.job_service import JobService
from studio.services.reference_character_service import ReferenceCharacterService
from studio.services.character_master_prompt_service import CharacterMasterPromptService
from studio.services.character_master_service import CharacterMasterService
from studio.services.character_runtime_service import CharacterRuntimeService
from studio.services.world_concept_prompt_service import WorldConceptPromptService
from studio.services.world_concept_service import WorldConceptService
from studio.services.world_blueprint_service import WorldBlueprintService
from studio.providers.openai_image import OpenAIImageProvider
from studio.storage.base import ObjectStorage
from studio.storage.local import LocalObjectStorage
from studio.storage.supabase import SupabaseObjectStorage


@dataclass
class StudioContext:
    settings: Settings
    repository: StudioRepository
    storage: ObjectStorage
    registry: PluginRegistry
    assets: AssetService
    stories: StoryService
    styles: StyleService
    universes: UniverseService
    jobs: JobService
    references: ReferenceCharacterService
    character_master_prompts: CharacterMasterPromptService
    character_masters: CharacterMasterService
    character_runtime: CharacterRuntimeService
    world_concept_prompts: WorldConceptPromptService
    world_blueprints: WorldBlueprintService
    world_concepts: WorldConceptService


def _build_storage(settings: Settings) -> ObjectStorage:
    if settings.object_storage_backend == "supabase":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "OBJECT_STORAGE_BACKEND=supabase requires SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY."
            )
        return SupabaseObjectStorage(
            url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
            bucket=settings.supabase_storage_bucket,
        )
    if settings.object_storage_backend != "local":
        raise RuntimeError(
            f"Unsupported OBJECT_STORAGE_BACKEND: {settings.object_storage_backend}"
        )
    return LocalObjectStorage(settings.data_dir)


def _build_repository(settings: Settings) -> StudioRepository:
    if settings.studio_repository_backend == "supabase":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "STUDIO_REPOSITORY_BACKEND=supabase requires SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY."
            )
        return SupabaseStudioRepository(
            url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
            table=settings.supabase_metadata_table,
        )
    if settings.studio_repository_backend != "sqlite":
        raise RuntimeError(
            f"Unsupported STUDIO_REPOSITORY_BACKEND: "
            f"{settings.studio_repository_backend}"
        )
    return SQLiteStudioRepository(settings.database_path)


def build_context(settings: Settings) -> StudioContext:
    repository = _build_repository(settings)
    storage = _build_storage(settings)
    registry = PluginRegistry()
    registry.register(MockCharacterParsePlugin())
    registry.register(MockTurnaroundPlugin())

    character_master_prompts = CharacterMasterPromptService()
    world_concept_prompts = WorldConceptPromptService()
    world_blueprints = WorldBlueprintService()
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
        character_runtime=CharacterRuntimeService(repository, storage),
        world_concept_prompts=world_concept_prompts,
        world_blueprints=world_blueprints,
        world_concepts=WorldConceptService(
            repository,
            storage,
            world_concept_prompts,
            world_blueprints,
            image_provider=image_provider,
        ),
    )

from dataclasses import dataclass
from studio.core.config import Settings
from studio.plugins.base import PluginRegistry
from studio.plugins.mock.creative import MockCharacterParsePlugin, MockTurnaroundPlugin
from studio.repositories.base import StudioRepository
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.repositories.supabase import SupabaseStudioRepository
from studio.services.asset_service import AssetService
from studio.services.equipment_service import EquipmentService
from studio.services.baby_service import BabyService
from studio.services.story_service import StoryService
from studio.services.story_suggestion_service import StorySuggestionService
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
from studio.services.world_concept_match_service import WorldConceptMatchService
from studio.services.world_visual_anchor_service import WorldVisualAnchorService
from studio.services.world_scene_plan_service import WorldScenePlanService
from studio.services.world_appearance_service import WorldAppearanceService
from studio.services.world_geometry_compiler_service import WorldGeometryCompilerService
from studio.services.world_hero_asset_service import WorldHeroAssetService
from studio.services.world_hero_composition_service import WorldHeroCompositionService
from studio.services.reusable_asset_library_service import ReusableAssetLibraryService
from studio.services.reusable_asset_pack_service import ReusableAssetPackService
from studio.providers.openai_image import OpenAIImageProvider
from studio.providers.openai_vision import OpenAIVisionProvider
from studio.providers.openai_text import OpenAIStructuredTextProvider
from studio.providers.hero_asset import HttpHeroAssetProvider, HuggingFacePixal3DProvider
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
    equipment: EquipmentService
    stories: StoryService
    story_suggestions: StorySuggestionService
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
    world_scene_plans: WorldScenePlanService
    world_appearances: WorldAppearanceService
    world_geometry_compiler: WorldGeometryCompilerService
    world_hero_assets: WorldHeroAssetService
    world_hero_compositions: WorldHeroCompositionService
    reusable_assets: ReusableAssetLibraryService
    reusable_asset_packs: ReusableAssetPackService
    world_concept_match: WorldConceptMatchService

    @property
    def babies(self) -> BabyService:
        return BabyService(self.repository)


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
    image_provider = (
        OpenAIImageProvider(
            settings.openai_api_key,
            model=settings.openai_image_model,
        )
        if settings.openai_api_key
        else None
    )
    vision_provider = (
        OpenAIVisionProvider(
            settings.openai_api_key,
            model=settings.openai_vision_model,
        )
        if settings.openai_api_key
        else None
    )
    text_provider = (
        OpenAIStructuredTextProvider(
            settings.openai_api_key,
            model=settings.openai_text_model,
        )
        if settings.openai_api_key
        else None
    )
    world_visual_anchors = WorldVisualAnchorService(
        image_analysis_provider=vision_provider
    )
    world_blueprints = WorldBlueprintService(
        visual_anchor_service=world_visual_anchors
    )
    world_appearances = WorldAppearanceService(
        structured_provider=text_provider,
        image_analysis_provider=vision_provider,
    )
    world_geometry_compiler = WorldGeometryCompilerService()
    world_hero_compositions = WorldHeroCompositionService(
        structured_provider=text_provider,
    )
    reusable_assets = ReusableAssetLibraryService(repository, storage)
    reusable_asset_packs = ReusableAssetPackService(reusable_assets)

    if settings.hero_asset_worker_url:
        hero_asset_provider = HttpHeroAssetProvider(
            base_url=settings.hero_asset_worker_url,
            model=settings.hero_asset_model,
            token=settings.hero_asset_worker_token,
            timeout_seconds=settings.hero_asset_timeout_seconds,
        )
    elif settings.hf_token:
        hero_asset_provider = HuggingFacePixal3DProvider(
            token=settings.hf_token,
            space_id=settings.hf_hero_space_id,
            resolution=settings.hf_pixal3d_resolution,
            decimation_target=settings.hf_pixal3d_decimation_target,
            texture_size=settings.hf_pixal3d_texture_size,
            seed=settings.hf_pixal3d_seed,
        )
    else:
        hero_asset_provider = None

    world_hero_assets = WorldHeroAssetService(
        storage=storage,
        provider=hero_asset_provider,
        max_assets_per_world=settings.hero_asset_max_per_world,
        reusable_library=reusable_assets,
        reference_image_provider=image_provider,
    )

    return StudioContext(
        settings=settings,
        repository=repository,
        storage=storage,
        registry=registry,
        assets=AssetService(repository),
        equipment=EquipmentService(repository),
        stories=StoryService(repository),
        story_suggestions=StorySuggestionService(
            structured_provider=text_provider,
        ),
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
            appearance_service=world_appearances,
            geometry_compiler=world_geometry_compiler,
            hero_asset_service=world_hero_assets,
            hero_composition_service=world_hero_compositions,
        ),
        world_scene_plans=WorldScenePlanService(
            structured_provider=text_provider,
        ),
        world_appearances=world_appearances,
        world_geometry_compiler=world_geometry_compiler,
        world_hero_assets=world_hero_assets,
        world_hero_compositions=world_hero_compositions,
        reusable_assets=reusable_assets,
        reusable_asset_packs=reusable_asset_packs,
        world_concept_match=WorldConceptMatchService(repository),
    )

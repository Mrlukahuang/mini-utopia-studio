from io import BytesIO

from PIL import Image
from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.character import CharacterProfile
from studio.providers.base import ImageGenerationProvider
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.character_master_prompt_service import CharacterMasterPromptService
from studio.services.character_master_service import CharacterMasterService
from studio.services.style_service import StyleService
from studio.storage.local import LocalObjectStorage


class FakeImageProvider(ImageGenerationProvider):
    def __init__(self):
        self.calls = []

    def generate(self, *, prompt: str, size: str = "1536x1024", quality: str = "medium") -> bytes:
        self.calls.append({"prompt": prompt, "size": size, "quality": quality})
        image = Image.new("RGB", (1024, 1536), "#FFF8EE")
        out = BytesIO()
        image.save(out, format="PNG")
        return out.getvalue()


def _character(repo):
    asset = Asset.create(
        AssetType.CHARACTER,
        display_name="Nova",
        slug="nova",
        metadata={
            "character_profile": CharacterProfile(
                character_type="人类 / Human",
                age="8",
                appearance="cute mini avatar",
                personality_traits=["curious"],
                speaking_tone="gentle",
                native_language="Chinese",
                english_level=6,
            ).model_dump(mode="json")
        },
    )
    repo.save_asset(asset)
    return asset


def test_generate_candidate_attaches_file_and_preserves_char_id(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    provider = FakeImageProvider()
    prompt_service = CharacterMasterPromptService()
    service = CharacterMasterService(repo, storage, prompt_service, provider)

    character = _character(repo)
    style = StyleService(repo).ensure_mini_utopia_base()

    candidate = service.generate_candidate(
        character_asset_id=character.asset_id,
        style_asset_id=style.asset_id,
    )

    saved = repo.get_asset(character.asset_id)
    assert saved.asset_id == character.asset_id
    assert saved.status == ReviewStatus.NEEDS_REVIEW
    assert candidate.role == "character_master_candidate"
    branded = Image.open(BytesIO(storage.get_bytes(candidate.path)))
    assert branded.size == (1200, 1800)
    assert provider.calls[0]["size"] == "1024x1536"
    assert saved.metadata["character_master_final_size"] == "1200x1800"
    assert storage.exists(saved.metadata["character_master_last_source_path"])
    assert "Mini Utopia Character Master" in provider.calls[0]["prompt"]


def test_approve_candidate_promotes_master_and_versions_character(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    provider = FakeImageProvider()
    service = CharacterMasterService(
        repo,
        storage,
        CharacterMasterPromptService(),
        provider,
    )
    character = _character(repo)
    style = StyleService(repo).ensure_mini_utopia_base()
    candidate = service.generate_candidate(
        character_asset_id=character.asset_id,
        style_asset_id=style.asset_id,
    )

    approved = service.approve_candidate(
        character_asset_id=character.asset_id,
        candidate_path=candidate.path,
    )

    saved = repo.get_asset(character.asset_id)
    assert approved.role == "character_master"
    assert saved.status == ReviewStatus.APPROVED
    assert saved.version == 2
    assert saved.metadata["character_master_path"] == candidate.path
    assert service.current_master(character.asset_id).path == candidate.path


def test_regeneration_keeps_previous_candidate_until_human_approval(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    service = CharacterMasterService(
        repo,
        storage,
        CharacterMasterPromptService(),
        FakeImageProvider(),
    )
    character = _character(repo)
    style = StyleService(repo).ensure_mini_utopia_base()

    first = service.generate_candidate(
        character_asset_id=character.asset_id,
        style_asset_id=style.asset_id,
    )
    second = service.generate_candidate(
        character_asset_id=character.asset_id,
        style_asset_id=style.asset_id,
    )

    saved = repo.get_asset(character.asset_id)
    candidates = [f for f in saved.files if f.role == "character_master_candidate"]
    assert first.path != second.path
    assert len(candidates) == 2
    assert service.current_master(character.asset_id) is None


def test_master_prompt_resolves_wearables_instead_of_exposing_ids(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    provider = FakeImageProvider()
    service = CharacterMasterService(
        repo,
        storage,
        CharacterMasterPromptService(),
        provider,
    )

    top = Asset.create(
        AssetType.WEARABLE,
        display_name="White T-Shirt / 白色 T恤",
        slug="white-shirt",
        description="simple clean white cotton T-shirt",
    )
    repo.save_asset(top)

    character = _character(repo)
    profile = CharacterProfile.model_validate(
        character.metadata["character_profile"]
    )
    profile.wearables.top_id = top.asset_id
    character.metadata["character_profile"] = profile.model_dump(mode="json")
    repo.save_asset(character)

    style = StyleService(repo).ensure_mini_utopia_base()
    service.generate_candidate(
        character_asset_id=character.asset_id,
        style_asset_id=style.asset_id,
    )

    prompt = provider.calls[0]["prompt"]
    assert "White T-Shirt / 白色 T恤" in prompt
    assert "simple clean white cotton T-shirt" in prompt
    assert top.asset_id not in prompt


def test_current_master_falls_back_to_metadata_path(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    storage = LocalObjectStorage(tmp_path / "storage")
    service = CharacterMasterService(
        repo,
        storage,
        CharacterMasterPromptService(),
        FakeImageProvider(),
    )
    character = _character(repo)
    character.metadata["character_master_path"] = "assets/legacy/master.png"
    character.files = []
    repo.save_asset(character)

    master = service.current_master(character.asset_id)

    assert master is not None
    assert master.role == "character_master"
    assert master.path == "assets/legacy/master.png"

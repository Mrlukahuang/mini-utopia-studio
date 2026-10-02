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

    def generate(self, *, prompt: str, size: str = "1024x1536", quality: str = "medium") -> bytes:
        self.calls.append({"prompt": prompt, "size": size, "quality": quality})
        return b"fake-png-bytes"


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
    assert storage.get_bytes(candidate.path) == b"fake-png-bytes"
    assert provider.calls[0]["size"] == "1024x1536"
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

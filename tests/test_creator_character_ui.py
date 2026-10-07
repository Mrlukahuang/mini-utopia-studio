from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.avatar import AvatarAppearance
from studio.models.character import CharacterProfile
from studio.models.equipment import EquipmentSlot, PLAYABLE_EQUIPMENT_SLOTS
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.asset_service import AssetService
from studio.services.equipment_service import EquipmentService
from studio.recipes.character_factory import CharacterFactoryRecipe
from studio.ui.creator.character_factory import (
    _build_factory_equipment_preview,
    _default_factory_equipment_selection,
    _factory_equipment_state,
    _factory_slot_items,
    _persist_factory_equipment_selection,
    resolve_character_save_target,
    english_level_label,
    relative_height_label,
)


def test_english_level_labels_cover_full_scale():
    assert "Almost no English" in english_level_label(1)
    assert "Native" in english_level_label(10)


def test_relative_height_label_uses_reference_names():
    label = relative_height_label(
        125,
        ["Chelsea", "Charlotte"],
        [110, 140],
    )

    assert "Chelsea" in label
    assert "Charlotte" in label
    assert "Between" in label


def test_relative_height_label_handles_large_character():
    label = relative_height_label(
        250,
        ["Chelsea", "Charlotte"],
        [110, 140],
    )

    assert "Charlotte" in label
    assert "Much taller" in label


def test_character_factory_returns_to_library_after_save():
    from pathlib import Path

    source = Path("studio/ui/creator/character_factory.py").read_text()
    assert 'st.session_state.app_page = "🎭 My Characters"' in source
    assert "character_save_asset_id" in source
    assert "pending_app_page = \"🎭 My Characters\"" not in source



def test_character_factory_is_child_first_and_saves_without_image_api():
    from pathlib import Path

    source = Path("studio/ui/creator/character_factory.py").read_text(
        encoding="utf-8"
    )

    assert "Start My Hero / 开始创造我的角色" in source
    assert "Make a hero of your own!" in source
    assert "More choices / 更多设定（可选）" in source
    assert "More personality details / 更多性格设定（可选）" in source
    assert "Outfit & Gear / 穿搭和装备" in source
    assert "More details / 更多角色设定（可选）" in source
    assert "Save My Hero / 保存我的角色" in source
    assert "profile_can_save = not missing and bool(name)" in source
    assert 'st.session_state.app_page = "🎭 My Characters"' in source
    assert "character_save_asset_id" in source
    assert "上面的 Save My Hero 可以直接保存可玩角色" in source

    save_button = source.index("💖 Save My Hero / 保存我的角色")
    image_gate = source.index("ctx.character_masters.is_available")
    assert save_button < image_gate



def test_character_factory_keeps_preview_and_uses_equipment_v2():
    from pathlib import Path

    source = Path("studio/ui/creator/character_factory.py").read_text(
        encoding="utf-8"
    )

    assert source.count("render_avatar_preview(") >= 3
    assert "Your Hero / 你的角色" in source
    assert "Outfit Preview / 穿搭实时预览" in source
    assert "Ready to Play / 准备进入 Mini Utopia" in source
    assert "FACTORY_CLOTHING_SLOTS" in source
    assert "FACTORY_GEAR_SLOTS" in source
    assert "Adventure Gear / 冒险装备（可选）" in source
    assert "ensure_default_character_wearables" not in source
    assert "char_equipment_selection" in source


def test_factory_equipment_defaults_preview_and_persist_all_slots(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    equipment = EquipmentService(repo)
    collection, definitions = _factory_equipment_state(equipment)

    defaults = _default_factory_equipment_selection(equipment)
    assert defaults[EquipmentSlot.TOP.value] is not None
    assert defaults[EquipmentSlot.BOTTOM.value] is not None
    assert defaults[EquipmentSlot.SHOES.value] is not None
    assert defaults[EquipmentSlot.HEADWEAR.value] is not None
    assert defaults[EquipmentSlot.WEAPON_MAIN.value] is None
    assert defaults[EquipmentSlot.BACKPACK.value] is None

    selection = dict(defaults)
    for slot in PLAYABLE_EQUIPMENT_SLOTS:
        items = _factory_slot_items(collection, definitions, slot)
        assert items, f"starter inventory missing slot: {slot.value}"
        selection[slot.value] = items[0].item_instance_id

    preview = _build_factory_equipment_preview(
        equipment,
        AvatarAppearance(customized=True),
        selection,
    )
    assert set(preview.equipped) == {
        slot.value for slot in PLAYABLE_EQUIPMENT_SLOTS
    }

    character = Asset.create(
        AssetType.CHARACTER,
        display_name="Factory Hero",
        slug="factory-hero",
        metadata={
            "character_profile": CharacterProfile(
                avatar=AvatarAppearance(customized=True)
            ).model_dump(mode="json")
        },
    )
    repo.save_asset(character)

    _persist_factory_equipment_selection(
        equipment,
        character_asset_id=character.asset_id,
        selection=selection,
    )
    runtime = equipment.runtime_spec(character.asset_id)
    assert set(runtime.equipped) == {
        slot.value for slot in PLAYABLE_EQUIPMENT_SLOTS
    }
    assert (
        runtime.equipped[EquipmentSlot.SHOES.value].item_instance_id
        == selection[EquipmentSlot.SHOES.value]
    )
    assert (
        runtime.equipped[EquipmentSlot.HEADWEAR.value].item_instance_id
        == selection[EquipmentSlot.HEADWEAR.value]
    )



def test_character_save_target_makes_repeat_save_idempotent(tmp_path):
    assert resolve_character_save_target(None, None) is None
    assert (
        resolve_character_save_target(
            None,
            "CHAR_SAVED",
        )
        == "CHAR_SAVED"
    )
    assert (
        resolve_character_save_target(
            "CHAR_EDITING",
            "CHAR_SAVED",
        )
        == "CHAR_EDITING"
    )

    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    recipe = CharacterFactoryRecipe(None, AssetService(repo))
    profile = CharacterProfile(
        character_type="人类 / Human",
        age="8",
        appearance="Mini hero",
        personality_traits=["好奇 / Curious"],
        speaking_tone="搞笑 / Funny",
        native_language="中文 / Chinese",
        english_level=5,
        avatar=AvatarAppearance(customized=True),
    )

    first = recipe.save_character(
        name="111",
        description="",
        profile=profile,
        asset_id=None,
    )
    guard = first.asset_id

    for _ in range(2):
        saved = recipe.save_character(
            name="111",
            description="",
            profile=profile,
            asset_id=resolve_character_save_target(None, guard),
        )
        assert saved.asset_id == guard

    characters = repo.list_assets(AssetType.CHARACTER)
    assert [asset.asset_id for asset in characters] == [guard]


def test_my_characters_shows_saved_confirmation():
    from pathlib import Path

    source = Path("app.py").read_text(encoding="utf-8")
    assert 'st.session_state.pop(\n        "last_saved_character_id"' in source
    assert "已保存！现在可以继续换装或带 TA 去冒险。" in source

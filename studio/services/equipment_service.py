from __future__ import annotations

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset, now_utc
from studio.models.character import CharacterProfile
from studio.models.equipment import (
    CharacterLoadout,
    CreatorCollection,
    EquipmentDefinition,
    EquipmentInstance,
    EquipmentRarity,
    EquipmentSlot,
    PLAYABLE_EQUIPMENT_SLOTS,
    StatBlock,
    create_equipment_instance,
)
from studio.models.equipment_runtime import (
    EquipmentRuntimeItemSpec,
    EquipmentRuntimeSpec,
)
from studio.repositories.base import StudioRepository


DEFAULT_COLLECTION_ID = "COLL_DEFAULT"


STARTER_DEFINITIONS = (
    EquipmentDefinition(
        definition_id="starter_sword",
        display_name="Starwood Sword / 星木剑",
        slot=EquipmentSlot.WEAPON_MAIN,
        description="A light first sword for Mini Utopia adventures.",
        animation_class="one_handed",
        compatible_tags=["humanoid"],
        base_stats=StatBlock(atk=8),
    ),
    EquipmentDefinition(
        definition_id="starter_shield",
        display_name="Wood Shield / 木盾",
        slot=EquipmentSlot.WEAPON_OFFHAND,
        description="A friendly first offhand shield.",
        animation_class="shield",
        compatible_tags=["humanoid"],
        base_stats=StatBlock(hp=3, defense=6),
    ),
    # Keep the historic slug so existing starter Outfit assets/instances
    # migrate in place instead of being deleted or duplicated.
    EquipmentDefinition(
        definition_id="starter_outfit",
        display_name="Explorer Top / 探险上衣",
        slot=EquipmentSlot.TOP,
        description="The v2 top migrated from the original Explorer Outfit.",
        compatible_tags=["humanoid"],
        base_stats=StatBlock(hp=4, defense=2),
    ),
    EquipmentDefinition(
        definition_id="starter_bottom",
        display_name="Adventure Pants / 冒险裤",
        slot=EquipmentSlot.BOTTOM,
        description="Comfortable pants for running around Mini Utopia.",
        compatible_tags=["humanoid"],
        base_stats=StatBlock(hp=3, defense=2),
    ),
    EquipmentDefinition(
        definition_id="starter_shoes",
        display_name="Cloud Sneakers / 云朵鞋",
        slot=EquipmentSlot.SHOES,
        description="Soft starter shoes for little explorers.",
        compatible_tags=["humanoid"],
        base_stats=StatBlock(hp=2, defense=1),
    ),
    EquipmentDefinition(
        definition_id="starter_backpack",
        display_name="Cloud Backpack / 云朵背包",
        slot=EquipmentSlot.BACKPACK,
        description="A soft travel backpack with extra vitality.",
        compatible_tags=["humanoid"],
        base_stats=StatBlock(hp=12, defense=1),
    ),
    EquipmentDefinition(
        definition_id="starter_wings",
        display_name="Tiny Star Wings / 小星星翅膀",
        slot=EquipmentSlot.WINGS,
        description="Decorative starter wings with a small mixed stat bonus.",
        compatible_tags=["humanoid"],
        base_stats=StatBlock(hp=3, atk=2, defense=2),
    ),
    EquipmentDefinition(
        definition_id="starter_accessory",
        display_name="Portal Charm / 传送门挂件",
        slot=EquipmentSlot.ACCESSORY,
        description="A tiny chest charm for early adventures.",
        compatible_tags=["humanoid"],
        base_stats=StatBlock(hp=2, atk=2, defense=2),
    ),
    EquipmentDefinition(
        definition_id="starter_cap",
        display_name="Soft Cap / 软软帽",
        slot=EquipmentSlot.HEADWEAR,
        description="A simple soft cap for everyday adventures.",
        compatible_tags=["humanoid"],
        base_stats=StatBlock(hp=1, defense=1),
    ),
    EquipmentDefinition(
        definition_id="starter_crown",
        display_name="Tiny Crown / 小皇冠",
        slot=EquipmentSlot.HEADWEAR,
        description="A tiny golden crown for special adventures.",
        compatible_tags=["humanoid"],
        base_stats=StatBlock(hp=2, atk=1, defense=2),
    ),
)


STARTER_ITEM_RECIPES = (
    # Preserve the original seed so an existing Explorer Outfit instance
    # becomes the Explorer Top rather than producing a duplicate.
    ("starter_outfit", EquipmentRarity.GREEN, "mini-utopia-starter-green"),
    ("starter_bottom", EquipmentRarity.GREEN, "mini-utopia-starter-bottom"),
    ("starter_shoes", EquipmentRarity.BLUE, "mini-utopia-starter-shoes"),
    ("starter_backpack", EquipmentRarity.BLUE, "mini-utopia-starter-blue"),
    ("starter_sword", EquipmentRarity.PURPLE, "mini-utopia-starter-purple"),
    ("starter_shield", EquipmentRarity.BLUE, "mini-utopia-starter-shield"),
    ("starter_wings", EquipmentRarity.GREEN, "mini-utopia-starter-wings"),
    ("starter_accessory", EquipmentRarity.BLUE, "mini-utopia-starter-charm"),
    ("starter_cap", EquipmentRarity.GREEN, "mini-utopia-starter-cap"),
    ("starter_crown", EquipmentRarity.GOLD, "mini-utopia-starter-crown"),
)


class EquipmentService:
    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def ensure_default_definitions(self) -> dict[str, EquipmentDefinition]:
        existing_assets = {
            asset.slug: asset
            for asset in self.repository.list_assets(AssetType.EQUIPMENT)
        }
        result: dict[str, EquipmentDefinition] = {}

        for definition in STARTER_DEFINITIONS:
            slug = definition.definition_id
            asset = existing_assets.get(slug)
            if asset is None:
                asset = Asset.create(
                    AssetType.EQUIPMENT,
                    display_name=definition.display_name,
                    slug=slug,
                    description=definition.description,
                    status=ReviewStatus.APPROVED,
                    metadata={
                        "equipment_definition": definition.model_dump(mode="json"),
                        "system_default": True,
                    },
                )
                self.repository.save_asset(asset)

            if asset.metadata.get("system_default"):
                # Code is canonical for system defaults. This is also how the
                # v1 starter Outfit safely migrates to the v2 Top slot while
                # preserving the stable Asset ID used by owned instances.
                resolved = definition.model_copy(
                    update={"definition_id": asset.asset_id}
                )
                asset.display_name = resolved.display_name
                asset.description = resolved.description
                asset.metadata["equipment_definition"] = resolved.model_dump(mode="json")
                asset.metadata["equipment_schema_version"] = 2
                self.repository.save_asset(asset)
            else:
                resolved = EquipmentDefinition.model_validate(
                    asset.metadata.get(
                        "equipment_definition",
                        definition.model_dump(mode="json"),
                    )
                )
                if resolved.definition_id != asset.asset_id:
                    resolved = resolved.model_copy(
                        update={"definition_id": asset.asset_id}
                    )
                    asset.metadata["equipment_definition"] = resolved.model_dump(mode="json")
                    self.repository.save_asset(asset)

            result[resolved.definition_id] = resolved

        return result

    def list_definitions(self) -> dict[str, EquipmentDefinition]:
        self.ensure_default_definitions()
        result: dict[str, EquipmentDefinition] = {}
        for asset in self.repository.list_assets(AssetType.EQUIPMENT):
            raw = asset.metadata.get("equipment_definition")
            if not raw:
                continue
            definition = EquipmentDefinition.model_validate(raw)
            if definition.slot == EquipmentSlot.OUTFIT:
                # Normalize any v1 whole-body Outfit definition, not only the
                # built-in starter, so user-owned legacy items remain visible
                # and equipable after the v2 split.
                definition = definition.model_copy(update={"slot": EquipmentSlot.TOP})
                asset.metadata["equipment_definition"] = definition.model_dump(mode="json")
                asset.metadata["equipment_schema_version"] = 2
                self.repository.save_asset(asset)
            result[definition.definition_id] = definition
        return result

    def get_definition(self, definition_id: str) -> EquipmentDefinition:
        definitions = self.list_definitions()
        definition = definitions.get(definition_id)
        if definition is None:
            raise ValueError(f"Equipment definition not found: {definition_id}")
        return definition

    def get_collection(self) -> CreatorCollection:
        collection = self.repository.get_collection(DEFAULT_COLLECTION_ID)
        if collection is None:
            collection = CreatorCollection(collection_id=DEFAULT_COLLECTION_ID)
            self.repository.save_collection(collection)
        return collection

    def ensure_starter_collection(self) -> CreatorCollection:
        definitions = self.ensure_default_definitions()
        by_slug = {
            asset.slug: EquipmentDefinition.model_validate(
                asset.metadata["equipment_definition"]
            )
            for asset in self.repository.list_assets(AssetType.EQUIPMENT)
            if asset.metadata.get("equipment_definition")
        }

        collection = self.get_collection()

        # Backward-compatible loadout migration: keep the owned item instance
        # and move only the pointer from legacy Outfit -> Top.
        for character_id, loadout in list(collection.loadouts.items()):
            migrated = loadout.migrate_v2()
            if migrated != loadout:
                collection.loadouts[character_id] = migrated

        existing_seeds = {item.generation_seed for item in collection.items}

        for slug, rarity, seed in STARTER_ITEM_RECIPES:
            if seed in existing_seeds:
                continue
            definition = by_slug[slug]
            collection.items.append(
                create_equipment_instance(
                    definition=definition,
                    rarity=rarity,
                    item_level=1,
                    generation_seed=seed,
                )
            )

        collection.updated_at = now_utc()
        self.repository.save_collection(collection)
        return collection

    def base_stats(self, character_asset_id: str) -> StatBlock:
        asset = self.repository.get_asset(character_asset_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            raise ValueError(f"Character not found: {character_asset_id}")

        raw = asset.metadata.get("base_stats")
        if raw:
            return StatBlock.model_validate(raw)
        return StatBlock(hp=100, atk=10, defense=8)

    def loadout_for(self, character_asset_id: str) -> CharacterLoadout:
        collection = self.ensure_starter_collection()
        return collection.loadout_for(character_asset_id)

    def final_stats(self, character_asset_id: str) -> StatBlock:
        collection = self.ensure_starter_collection()
        loadout = collection.loadout_for(character_asset_id)
        total = self.base_stats(character_asset_id)

        for slot in PLAYABLE_EQUIPMENT_SLOTS:
            item_id = loadout.item_id_for_slot(slot)
            if not item_id:
                continue
            item = collection.item_by_id(item_id)
            if item is not None:
                total = total.plus(item.rolled_stats)

        return total

    def equip(
        self,
        *,
        character_asset_id: str,
        item_instance_id: str,
    ) -> CreatorCollection:
        asset = self.repository.get_asset(character_asset_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            raise ValueError(f"Character not found: {character_asset_id}")

        profile = CharacterProfile.model_validate(
            asset.metadata.get("character_profile", {})
        )
        collection = self.ensure_starter_collection()
        item = collection.item_by_id(item_instance_id)
        if item is None:
            raise ValueError(f"Equipment item not owned: {item_instance_id}")

        definition = self.get_definition(item.definition_id)
        character_tags = set(profile.avatar.compatible_tags or ["humanoid"])
        required_tags = set(definition.compatible_tags)
        if required_tags and character_tags.isdisjoint(required_tags):
            raise ValueError(
                f"Equipment is incompatible with this Character: {definition.display_name}"
            )

        loadout = collection.loadout_for(character_asset_id)
        collection.loadouts[character_asset_id] = loadout.with_item(
            definition.slot,
            item.item_instance_id,
        )
        collection.updated_at = now_utc()
        self.repository.save_collection(collection)
        return collection

    def unequip(
        self,
        *,
        character_asset_id: str,
        slot: EquipmentSlot,
    ) -> CreatorCollection:
        collection = self.ensure_starter_collection()
        loadout = collection.loadout_for(character_asset_id)
        collection.loadouts[character_asset_id] = loadout.with_item(slot, None)
        collection.updated_at = now_utc()
        self.repository.save_collection(collection)
        return collection


    def runtime_spec(self, character_asset_id: str) -> EquipmentRuntimeSpec:
        asset = self.repository.get_asset(character_asset_id)
        if asset is None or asset.asset_type != AssetType.CHARACTER:
            raise ValueError(f"Character not found: {character_asset_id}")

        profile = CharacterProfile.model_validate(
            asset.metadata.get("character_profile", {})
        )
        collection = self.ensure_starter_collection()
        definitions = self.list_definitions()
        loadout = collection.loadout_for(character_asset_id)

        equipped: dict[str, EquipmentRuntimeItemSpec] = {}
        for slot in PLAYABLE_EQUIPMENT_SLOTS:
            item_id = loadout.item_id_for_slot(slot)
            if not item_id:
                continue
            item = collection.item_by_id(item_id)
            if item is None:
                continue
            definition = definitions.get(item.definition_id)
            if definition is None:
                continue
            equipped[slot.value] = EquipmentRuntimeItemSpec(
                item_instance_id=item.item_instance_id,
                definition_id=definition.definition_id,
                display_name=definition.display_name,
                slot=definition.slot,
                rarity=item.rarity,
                mesh_asset_id=definition.mesh_asset_id,
                animation_class=definition.animation_class,
                rolled_stats=item.rolled_stats,
            )

        return EquipmentRuntimeSpec(
            character_asset_id=character_asset_id,
            body_type=profile.avatar.body_type,
            final_stats=self.final_stats(character_asset_id),
            equipped=equipped,
        )

    def export_runtime_spec(
        self,
        *,
        character_asset_id: str,
        target_path,
    ):
        return self.runtime_spec(character_asset_id).save_json(target_path)

    def add_instance(self, item: EquipmentInstance) -> CreatorCollection:
        collection = self.get_collection()
        if collection.item_by_id(item.item_instance_id) is not None:
            raise ValueError(f"Equipment item already exists: {item.item_instance_id}")
        collection.items.append(item)
        collection.updated_at = now_utc()
        self.repository.save_collection(collection)
        return collection

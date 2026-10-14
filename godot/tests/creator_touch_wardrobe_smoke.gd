extends SceneTree

## Child-facing wardrobe: nine-slot list, large touch targets, canonical
## server updates, and immediate 3D Hero clothing/prop preview.

func _initialize() -> void:
    var packed := load("res://scenes/character_creator.tscn") as PackedScene
    if packed == null:
        _fail("Character Creator scene missing")
        return
    var creator := packed.instantiate()
    root.add_child(creator)
    await process_frame

    var character := {
        "schema_version": "1.0",
        "character_id": "CHAR_WARDROBE_LILY",
        "display_name": "Lily",
        "revision": "1",
        "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
            "species_head_id": "species_head_sheep_v1"
        }}
    }
    creator._on_bridge_success("character:get", character)
    var equipment := {
        "character_id": "CHAR_WARDROBE_LILY",
        "slots": ["top", "headwear", "weapon_main"],
        "items": [
            {
                "slot": "headwear",
                "display_name": "Tiny Crown",
                "item_instance_id": "ITEM_WARDROBE_CROWN",
                "equipped": false
            },
            {
                "slot": "weapon_main",
                "display_name": "Star Sword",
                "item_instance_id": "ITEM_WARDROBE_SWORD",
                "equipped": false
            },
            {
                "slot": "top",
                "display_name": "Explorer Top",
                "item_instance_id": "ITEM_WARDROBE_TOP",
                "equipped": false
            }
        ],
        "runtime": {
            "character_asset_id": "CHAR_WARDROBE_LILY",
            "equipped": {},
            "final_stats": {"hp": 100, "atk": 10, "defense": 8}
        }
    }
    creator._on_bridge_success("equipment:get", equipment)
    creator._select_creator_tab("outfit")
    await process_frame

    var outfit := creator.get_node_or_null(
        "RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/OutfitChoices"
    ) as VBoxContainer
    if outfit == null or not outfit.visible:
        _fail("wardrobe did not open in the child-facing Creator")
        return

    var crown := outfit.get_node_or_null("Wear_headwear_ITEM_WARDROBE_CROWN") as Button
    var sword := outfit.get_node_or_null("Wear_weapon_main_ITEM_WARDROBE_SWORD") as Button
    if crown == null or sword == null:
        _fail("owned crown/sword were not rendered as touch choices")
        return
    if crown.custom_minimum_size.y < 44 or sword.custom_minimum_size.y < 44:
        _fail("wardrobe touch targets are too small")
        return
    if crown.pressed.get_connections().is_empty():
        _fail("wardrobe button does not call equipment API")
        return

    var equipped := equipment.duplicate(true)
    equipped["items"][0]["equipped"] = true
    equipped["runtime"]["equipped"] = {
        "headwear": {
            "item_instance_id": "ITEM_WARDROBE_CROWN",
            "display_name": "Tiny Crown",
            "rarity": "gold"
        }
    }
    creator._on_bridge_success("equipment:put:headwear", equipped)
    await process_frame
    if outfit.get_node_or_null("Remove_headwear") == null:
        _fail("equipped crown has no Take off button")
        return
    var stage := creator.get_node_or_null(
        "RootMargin/MainColumn/CreatorBody/PreviewPanel/AvatarStage"
    ) as MiniUtopiaCreatorAvatarStage
    if stage == null or stage.avatar_root().find_child("Equipment_headwear", true, false) == null:
        _fail("equipped crown did not appear on the same 3D Hero")
        return

    creator._select_creator_tab("look")
    if outfit.visible:
        _fail("Look tab did not close the wardrobe")
        return
    if not creator.get_node(
        "RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/BodyRow"
    ).visible:
        _fail("Look controls were not restored")
        return

    print("creator_touch_wardrobe_smoke: PASS · choices, equip, remove, 3D look")
    quit(0)


func _fail(message: String) -> void:
    push_error("creator_touch_wardrobe_smoke: FAIL · " + message)
    quit(1)

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


    # The official imported Knight carries unearned demo sword/shields.
    # Their imported draw layers must be zero so only server-owned gear renders.
    var knight_rig := stage.avatar_root().get_node("KayKitBody/Rig/Skeleton3D") as Skeleton3D
    for hand_name in ["handslot_l", "handslot_r"]:
        var native := knight_rig.get_node(hand_name) as Node3D
        for raw_mesh in native.get_children():
            if raw_mesh is MeshInstance3D and (raw_mesh as MeshInstance3D).layers != 0:
                _fail("native Knight weapon still visible without owned equipment")
                return
    var actual_hand := MiniUtopiaKaykitAvatarV1.mounted_weapon_socket(
        stage.avatar_root(), MiniUtopiaAvatarContract.SOCKET_WEAPON_R
    )
    if actual_hand == null or actual_hand.get_parent() != knight_rig.get_node("handslot_r"):
        _fail("owned hand models do not inherit the imported KayKit grip transform")
        return

    # Synthetic owner-scoped server response: only an actually owned standard
    # sword may be reskinned, and only AFTER equipment PUT confirms its ID.
    var equipped_sword := equipment.duplicate(true)
    equipped_sword["items"][1]["equipped"] = true
    equipped_sword["runtime"]["equipped"]["weapon_main"] = {
        "item_instance_id": "ITEM_WARDROBE_SWORD",
        "display_name": "Star Sword",
        "rarity": "blue",
    }
    creator._on_bridge_success("equipment:put:weapon_main", equipped_sword)
    var before_tags: Array = creator._draft_appearance.get("compatible_tags", ["humanoid"])
    creator._pending_hand_style = "staff"
    creator._pending_hand_slot = "weapon_main"
    creator._pending_hand_item_id = "ITEM_NOT_OWNED"
    creator._on_bridge_success("equipment:put:weapon_main", equipped_sword)
    if creator._draft_appearance.get("compatible_tags", ["humanoid"]) != before_tags:
        _fail("a mismatched equipment PUT changed avatar appearance")
        return

    creator._pending_hand_style = "staff"
    creator._pending_hand_slot = "weapon_main"
    creator._pending_hand_item_id = "ITEM_WARDROBE_SWORD"
    creator._on_bridge_success("equipment:put:weapon_main", equipped_sword)
    if not MiniUtopiaKaykitAvatarV1.visible_hand_style(
        stage.avatar_root(), "weapon_main", "staff"
    ):
        _fail("confirmed owned staff reskin was not visible on the official Knight")
        return
    if not creator._appearance_dirty:
        _fail("confirmed hand style was not marked for canonical Character save")
        return
    var updated: Dictionary = creator._character_update_payload("Lily")
    var avatar: Dictionary = updated.get("profile", {}).get("avatar", {})
    if MiniUtopiaKaykitAvatarV1.hand_skin(avatar) != "staff":
        _fail("hand style missing from canonical Character update payload")
        return

    # The same confirmed Character avatar + owned equipment must render in
    # the village, not just in the Creator's isolated SubViewport.
    var saved: Dictionary = creator.loaded_character.duplicate(true)
    saved["profile"]["avatar"] = avatar
    var play_payload := MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(saved)
    play_payload["equipment"] = equipped_sword["runtime"].duplicate(true)
    var world := Node3D.new()
    world.name = "MiniUtopiaWorld"
    root.add_child(world)
    var player := CharacterBody3D.new()
    world.add_child(player)
    var runtime := MiniUtopiaCreatorPlayRuntime.new()
    world.add_child(runtime)
    runtime.apply_payload_to_player(player, play_payload)
    if not MiniUtopiaKaykitAvatarV1.visible_hand_style(player, "weapon_main", "staff"):
        _fail("the same saved owned hand model disappeared after village reload")
        return
    world.queue_free()

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

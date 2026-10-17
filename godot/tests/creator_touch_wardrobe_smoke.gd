extends SceneTree

# Capture the actual child button and Save callbacks without external
# HTTP, credentials or real children. Server responses are simulated.
class CaptureBridge extends MiniUtopiaBridgeClient:
    var gear_calls: Array[Dictionary] = []
    var save_calls: Array[Dictionary] = []
    var reads: Array[String] = []
    var deny := false

    func has_family_session() -> bool:
        return true

    func is_busy() -> bool:
        return false

    func get_equipment(character_id: String) -> int:
        reads.append(character_id)
        return OK

    func put_equipment_slot(character_id: String, slot: String, item: Variant) -> int:
        gear_calls.append({"hero": character_id, "slot": slot, "item": item})
        return ERR_CANT_CONNECT if deny else OK

    func put_character(character_id: String, payload: Dictionary) -> int:
        save_calls.append({"hero": character_id, "payload": payload.duplicate(true)})
        return OK

## Child-facing wardrobe: nine-slot list, large touch targets, canonical
## server updates, and immediate 3D Hero clothing/prop preview.

func _initialize() -> void:
    var packed := load("res://scenes/character_creator.tscn") as PackedScene
    if packed == null:
        _fail("Character Creator scene missing")
        return
    var creator := packed.instantiate()
    creator.get_node("BridgeClient").set_script(CaptureBridge)
    root.add_child(creator)
    await process_frame

    var bridge := creator.get_node("BridgeClient") as CaptureBridge
    if bridge == null:
        _fail("Creator mock Bridge script did not attach")
        return
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
                "display_name": "Crafted Star",
                "item_instance_id": "ITEM_WARDROBE_CRAFTED",
                "visual_recipe": {"shape": "star"},
                "equipped": false
            },
            {
                "slot": "weapon_main",
                "display_name": "Spare Sword",
                "item_instance_id": "ITEM_WARDROBE_SPARE",
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
    equipped_sword["items"][3]["equipped"] = true
    equipped_sword["runtime"]["equipped"]["weapon_main"] = {
        "item_instance_id": "ITEM_WARDROBE_SWORD",
        "display_name": "Star Sword",
        "rarity": "blue",
    }
    creator._on_bridge_success("equipment:put:weapon_main", equipped_sword)
    var staff := creator.hand_style_grid.get_node("StaffStyleButton") as Button
    if not staff.visible or staff.pressed.get_connections().is_empty():
        _fail("child-facing staff control is not connected")
        return
    var before_tags: Array = creator._draft_appearance.get("compatible_tags", ["humanoid"])
    bridge.deny = true
    staff.pressed.emit()
    if bridge.gear_calls.size() != 1:
        _fail("staff click never sent a wardrobe PUT")
        return
    var call: Dictionary = bridge.gear_calls[0]
    if (
        call.get("hero") != "CHAR_WARDROBE_LILY"
        or call.get("slot") != "weapon_main"
        or call.get("item") != "ITEM_WARDROBE_SWORD"
    ):
        _fail("hand click chose crafted/spare instead of worn owned sword")
        return
    if creator._draft_appearance.get("compatible_tags", ["humanoid"]) != before_tags:
        _fail("failed equipment write changed Hero appearance")
        return
    if not creator._pending_hand_style.is_empty():
        _fail("failed equipment write left pending hand choice")
        return

    bridge.deny = false
    staff.pressed.emit()
    if bridge.gear_calls.size() != 2 or creator._pending_hand_style != "staff":
        _fail("successful hand click did not wait for server response")
        return
    if MiniUtopiaKaykitAvatarV1.visible_hand_style(
        stage.avatar_root(), "weapon_main", "staff"
    ):
        _fail("staff appeared before server confirmation")
        return
    var mismatch := equipped_sword.duplicate(true)
    mismatch["runtime"]["equipped"]["weapon_main"]["item_instance_id"] = "ITEM_FOREIGN"
    bridge.request_succeeded.emit("equipment:put:weapon_main", mismatch)
    if MiniUtopiaKaykitAvatarV1.hand_skin(creator._draft_appearance) == "staff":
        _fail("a mismatched server item changed appearance")
        return

    staff.pressed.emit()
    if bridge.gear_calls.size() != 3:
        _fail("retry after mismatched server item was blocked")
        return
    bridge.request_succeeded.emit("equipment:put:weapon_main", equipped_sword)
    if not MiniUtopiaKaykitAvatarV1.visible_hand_style(
        stage.avatar_root(), "weapon_main", "staff"
    ):
        _fail("server-confirmed staff not visible on Knight")
        return
    if not creator._appearance_dirty or not creator.play_button.disabled:
        _fail("unsaved hand change incorrectly allowed Village")
        return
    creator.save_button.pressed.emit()
    if bridge.save_calls.size() != 1:
        _fail("Save control did not send canonical Character PUT")
        return
    var write: Dictionary = bridge.save_calls[0]
    if write.get("hero") != "CHAR_WARDROBE_LILY":
        _fail("save targeted wrong Hero")
        return
    var avatar: Dictionary = write["payload"].get("profile", {}).get("avatar", {})
    if MiniUtopiaKaykitAvatarV1.hand_skin(avatar) != "staff":
        _fail("Character PUT missing visible staff")
        return
    var saved: Dictionary = character.duplicate(true)
    saved["profile"]["avatar"] = avatar.duplicate(true)
    saved["revision"] = "2"
    bridge.request_succeeded.emit("character:put", saved)

    # Fresh Creator reopens using server-saved Character and equipment GET,
    # not an unsaved draft composed directly into a village session.
    var reopened := packed.instantiate()
    reopened.get_node("BridgeClient").set_script(CaptureBridge)
    root.add_child(reopened)
    await process_frame
    var fresh_bridge := reopened.get_node("BridgeClient") as CaptureBridge
    fresh_bridge.request_succeeded.emit("character:get", saved)
    if fresh_bridge.reads != ["CHAR_WARDROBE_LILY"]:
        _fail("reopen did not GET the saved Hero wardrobe")
        return
    fresh_bridge.request_succeeded.emit("equipment:get", equipped_sword)
    if not MiniUtopiaKaykitAvatarV1.visible_hand_style(
        reopened.avatar_stage.avatar_root(), "weapon_main", "staff"
    ):
        _fail("saved staff disappeared on fresh Creator reopen")
        return
    if reopened.play_button.disabled:
        _fail("saved Hero with owned gear cannot enter Village")
        return
    var play_payload := MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(
        reopened.loaded_character
    )
    play_payload["equipment"] = reopened.equipment_state["runtime"].duplicate(true)
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

    var reopened_stage := reopened.avatar_stage as MiniUtopiaCreatorAvatarStage

    # The original fixed 90-degree weapon rotation brought the staff gem into
    # the helmet at animation extremes. Sample the same official right-hand
    # mount while Godot advances the imported Idle/Walk/Run animation clips.
    for pose in ["Idle", "Walk", "Run"]:
        reopened_stage.play_preview_animation(pose)
        await process_frame
        await process_frame
        var hand := reopened_stage.avatar_root().find_child(
            "Equipment_weapon_main", true, false
        ) as Node3D
        if hand == null or hand.get_node_or_null("OfficialHandProp") == null:
            _fail("owned long prop no longer follows the animated official hand")
            return
        var rig := reopened_stage.avatar_root().get_node(
            "KayKitBody/Rig/Skeleton3D"
        ) as Skeleton3D
        var head_bone := rig.find_bone("head")
        var center := rig.to_global(rig.get_bone_global_pose(head_bone).origin)
        var tip := hand.to_global(Vector3(0.0, 1.25, 0.0))
        var delta := tip - center
        var axes := reopened_stage.avatar_root().global_transform.basis.orthonormalized()
        # A 3-D radius alone cannot distinguish a jewel that overlaps the
        # *side-view projection*. Test BOTH actor-space planar projections:
        # front/back see X, left/right side see Z.
        var front_gap := absf(delta.dot(axes.x))
        var side_gap := absf(delta.dot(axes.z))
        if front_gap < 0.38 or side_gap < 0.46:
            _fail(
                "staff tip projected onto helmet in " + pose
                + " front=" + str(front_gap) + " side=" + str(side_gap)
            )
            return
        # Separately sample the long prop's centerline against the head in
        # 3-D. This is a coarse rig-proximity assertion, NOT mesh intersection.
        var start := hand.global_position
        var shaft := tip - start
        var fraction := clampf((center - start).dot(shaft) / shaft.length_squared(), 0.0, 1.0)
        if center.distance_to(start + shaft * fraction) < 0.35:
            _fail("staff centerline is too near the 3D helmet in " + pose)
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

extends SceneTree

func _initialize() -> void:
    var avatar := Node3D.new()
    avatar.name = "AvatarRoot"
    root.add_child(avatar)

    var socket := Node3D.new()
    socket.name = MiniUtopiaAvatarContract.SOCKET_WEAPON_R
    avatar.add_child(socket)

    var payload := {
        "equipped": {
            "weapon_main": {
                "item_instance_id": "ITEM_NULL_MESH_SMOKE",
                "definition_id": "EQ_NULL_MESH_SMOKE",
                "display_name": "Procedural Smoke Sword",
                "slot": "weapon_main",
                "rarity": "purple",
                "mesh_asset_id": null,
                "animation_class": "one_handed",
                "rolled_stats": {"hp": 0, "atk": 1, "defense": 0},
            }
        }
    }

    var attached := MiniUtopiaEquipmentRuntime.attach_loadout(
        avatar,
        payload
    )
    var weapon = attached.get("weapon_main")
    if weapon == null:
        push_error(
            "equipment_runtime_null_smoke: procedural weapon did not attach"
        )
        quit(1)
        return

    if StringName(weapon.name) != &"Equipment_weapon_main":
        push_error(
            "equipment_runtime_null_smoke: unexpected node name "
            + str(weapon.name)
        )
        quit(1)
        return

    print(
        "equipment_runtime_null_smoke: PASS · null mesh_asset_id "
        + "uses procedural fallback"
    )
    quit(0)

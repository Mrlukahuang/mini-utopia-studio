extends SceneTree

func _initialize() -> void:
    var avatar := Node3D.new()
    avatar.name = "AvatarRoot"
    root.add_child(avatar)

    var socket := Node3D.new()
    socket.name = MiniUtopiaAvatarContract.SOCKET_WEAPON_R
    avatar.add_child(socket)

    var offhand_socket := Node3D.new()
    offhand_socket.name = MiniUtopiaAvatarContract.SOCKET_WEAPON_L
    avatar.add_child(offhand_socket)

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
            },
            "weapon_offhand": {
                "item_instance_id": "ITEM_SHIELD_SMOKE",
                "definition_id": "EQ_SHIELD_SMOKE",
                "display_name": "Procedural Smoke Shield",
                "slot": "weapon_offhand",
                "rarity": "blue",
                "mesh_asset_id": null,
                "animation_class": "shield",
                "rolled_stats": {"hp": 0, "atk": 0, "defense": 1},
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

    if absf(weapon.rotation_degrees.x - 68.0) > 0.01:
        push_error(
            "equipment_runtime_null_smoke: sword is not pitched forward"
        )
        quit(1)
        return

    var shield = attached.get("weapon_offhand")
    if shield == null:
        push_error(
            "equipment_runtime_null_smoke: procedural shield did not attach"
        )
        quit(1)
        return

    if shield.position.x >= 0.0:
        push_error(
            "equipment_runtime_null_smoke: shield is not outside left hand"
        )
        quit(1)
        return

    if shield.rotation_degrees.y > -75.0:
        push_error(
            "equipment_runtime_null_smoke: shield is not yawed outward"
        )
        quit(1)
        return

    print(
        "equipment_runtime_null_smoke: PASS · null mesh fallback + "
        + "forward sword + outward shield"
    )
    quit(0)

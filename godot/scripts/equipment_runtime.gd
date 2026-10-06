class_name MiniUtopiaEquipmentRuntime
extends RefCounted

const SLOT_OUTFIT := "outfit" # legacy v1 compatibility
const SLOT_TOP := "top"
const SLOT_BOTTOM := "bottom"
const SLOT_SHOES := "shoes"
const SLOT_HEADWEAR := "headwear"
const SLOT_WEAPON_MAIN := "weapon_main"
const SLOT_WEAPON_OFFHAND := "weapon_offhand"
const SLOT_BACKPACK := "backpack"
const SLOT_WINGS := "wings"
const SLOT_ACCESSORY := "accessory"

const SOCKET_BY_SLOT := {
    SLOT_WEAPON_MAIN: MiniUtopiaAvatarContract.SOCKET_WEAPON_R,
    SLOT_WEAPON_OFFHAND: MiniUtopiaAvatarContract.SOCKET_WEAPON_L,
    SLOT_HEADWEAR: MiniUtopiaAvatarContract.SOCKET_HEADWEAR,
    SLOT_BACKPACK: MiniUtopiaAvatarContract.SOCKET_BACKPACK,
    SLOT_WINGS: MiniUtopiaAvatarContract.SOCKET_WINGS,
    SLOT_ACCESSORY: MiniUtopiaAvatarContract.SOCKET_ACCESSORY,
}


static func attach_loadout(
    avatar_root: Node3D,
    payload: Dictionary
) -> Dictionary:
    var result := {}
    var sockets := avatar_root.get_node_or_null("Sockets") as Node3D
    if sockets == null:
        push_warning("EQ-02: Avatar has no Sockets node.")
        return result

    var equipped: Dictionary = payload.get("equipped", {})
    for raw_slot in equipped.keys():
        var slot := String(raw_slot)
        var item: Dictionary = equipped.get(raw_slot, {})
        if slot in [SLOT_OUTFIT, SLOT_TOP, SLOT_BOTTOM, SLOT_SHOES]:
            _apply_clothing(avatar_root, slot, item)
            result[slot] = avatar_root.get_node_or_null("Visual/Body")
            continue

        var socket_name := String(SOCKET_BY_SLOT.get(slot, ""))
        if socket_name.is_empty():
            continue
        var socket := sockets.get_node_or_null(NodePath(socket_name)) as Node3D
        if socket == null:
            push_warning("EQ-02: Missing socket " + socket_name)
            continue

        _clear_equipment_children(socket)
        var attached := _attach_item(socket, slot, item)
        if attached != null:
            result[slot] = attached

    return result


static func _attach_item(
    socket: Node3D,
    slot: String,
    item: Dictionary
) -> Node3D:
    var mesh_asset_id := String(item.get("mesh_asset_id", ""))
    if not mesh_asset_id.is_empty() and AssetVaultRuntime.is_installed():
        var entry := AssetVaultRuntime.entry_by_id(mesh_asset_id)
        if not entry.is_empty():
            var asset_node := AssetVaultRuntime.instantiate_by_id(
                socket,
                mesh_asset_id,
                Vector3.ZERO,
                0.0,
                1.0,
                0.0
            )
            if asset_node != null:
                asset_node.name = "Equipment_" + slot
                return asset_node

    return _procedural_fallback(socket, slot, item)


static func _procedural_fallback(
    socket: Node3D,
    slot: String,
    item: Dictionary
) -> Node3D:
    var root := Node3D.new()
    root.name = "Equipment_" + slot
    socket.add_child(root)

    var color := _rarity_color(String(item.get("rarity", "green")))

    match slot:
        SLOT_WEAPON_MAIN:
            _build_sword(root, color)
        SLOT_WEAPON_OFFHAND:
            _build_shield(root, color)
        SLOT_HEADWEAR:
            _build_headwear(root, color, String(item.get("display_name", "")))
        SLOT_BACKPACK:
            _build_backpack(root, color)
        SLOT_WINGS:
            _build_wings(root, color)
        SLOT_ACCESSORY:
            _build_accessory(root, color)
        _:
            pass

    return root


static func _apply_clothing(
    avatar_root: Node3D,
    slot: String,
    item: Dictionary
) -> void:
    var color := _rarity_color(String(item.get("rarity", "green")))
    if slot in [SLOT_OUTFIT, SLOT_TOP]:
        var body := avatar_root.get_node_or_null("Visual/Body") as MeshInstance3D
        if body != null:
            body.material_override = _material(color)
        return

    var pattern := "Leg*" if slot == SLOT_BOTTOM else "Foot*"
    for node in avatar_root.find_children(pattern, "MeshInstance3D", true, false):
        var mesh_node := node as MeshInstance3D
        if mesh_node != null:
            mesh_node.material_override = _material(color)


static func _clear_equipment_children(socket: Node3D) -> void:
    for child in socket.get_children():
        if String(child.name).begins_with("Equipment_"):
            child.queue_free()


static func _build_sword(root: Node3D, color: Color) -> void:
    var grip := MeshInstance3D.new()
    grip.name = "Grip"
    var grip_mesh := CylinderMesh.new()
    grip_mesh.top_radius = 0.055
    grip_mesh.bottom_radius = 0.055
    grip_mesh.height = 0.32
    grip.mesh = grip_mesh
    grip.position = Vector3(0.0, 0.08, 0.0)
    grip.material_override = _material(Color("#7A5238"))
    root.add_child(grip)

    var guard := MeshInstance3D.new()
    guard.name = "Guard"
    var guard_mesh := BoxMesh.new()
    guard_mesh.size = Vector3(0.34, 0.06, 0.08)
    guard.mesh = guard_mesh
    guard.position = Vector3(0.0, 0.26, 0.0)
    guard.material_override = _material(Color("#F2C75C"))
    root.add_child(guard)

    var blade := MeshInstance3D.new()
    blade.name = "Blade"
    var blade_mesh := BoxMesh.new()
    blade_mesh.size = Vector3(0.12, 0.86, 0.055)
    blade.mesh = blade_mesh
    blade.position = Vector3(0.0, 0.72, 0.0)
    blade.material_override = _material(color)
    root.add_child(blade)

    root.rotation_degrees = Vector3(0.0, 0.0, -45.0)


static func _build_shield(root: Node3D, color: Color) -> void:
    var shield := MeshInstance3D.new()
    shield.name = "Shield"
    var mesh := CylinderMesh.new()
    mesh.top_radius = 0.30
    mesh.bottom_radius = 0.30
    mesh.height = 0.10
    shield.mesh = mesh
    shield.rotation_degrees = Vector3(90.0, 0.0, 0.0)
    shield.material_override = _material(color)
    root.add_child(shield)


static func _build_headwear(
    root: Node3D,
    color: Color,
    display_name: String
) -> void:
    if display_name.to_lower().contains("crown"):
        var ring := MeshInstance3D.new()
        ring.name = "CrownRing"
        var ring_mesh := CylinderMesh.new()
        ring_mesh.top_radius = 0.34
        ring_mesh.bottom_radius = 0.34
        ring_mesh.height = 0.10
        ring.mesh = ring_mesh
        ring.material_override = _material(Color("#F2C75C"))
        root.add_child(ring)
        for x in [-0.22, 0.0, 0.22]:
            var point := MeshInstance3D.new()
            point.name = "CrownPoint"
            var point_mesh := PrismMesh.new()
            point_mesh.size = Vector3(0.14, 0.28, 0.12)
            point.mesh = point_mesh
            point.position = Vector3(x, 0.18, 0.0)
            point.material_override = _material(Color("#F2C75C"))
            root.add_child(point)
    else:
        var cap := MeshInstance3D.new()
        cap.name = "Cap"
        var cap_mesh := SphereMesh.new()
        cap_mesh.radius = 0.42
        cap_mesh.height = 0.28
        cap.mesh = cap_mesh
        cap.material_override = _material(color)
        root.add_child(cap)


static func _build_backpack(root: Node3D, color: Color) -> void:
    var bag := MeshInstance3D.new()
    bag.name = "Bag"
    var bag_mesh := BoxMesh.new()
    bag_mesh.size = Vector3(0.58, 0.68, 0.24)
    bag.mesh = bag_mesh
    bag.position = Vector3(0.0, 0.0, -0.03)
    bag.material_override = _material(color)
    root.add_child(bag)

    var flap := MeshInstance3D.new()
    flap.name = "Flap"
    var flap_mesh := BoxMesh.new()
    flap_mesh.size = Vector3(0.48, 0.14, 0.28)
    flap.mesh = flap_mesh
    flap.position = Vector3(0.0, 0.20, 0.02)
    flap.material_override = _material(Color("#F6F1E8"))
    root.add_child(flap)


static func _build_wings(root: Node3D, color: Color) -> void:
    for side in [-1.0, 1.0]:
        var wing := MeshInstance3D.new()
        wing.name = "Wing"
        var mesh := BoxMesh.new()
        mesh.size = Vector3(0.18, 0.72, 0.44)
        wing.mesh = mesh
        wing.position = Vector3(0.34 * side, 0.06, -0.02)
        wing.rotation_degrees = Vector3(0.0, 0.0, 24.0 * side)
        wing.material_override = _material(color)
        root.add_child(wing)


static func _build_accessory(root: Node3D, color: Color) -> void:
    var charm := MeshInstance3D.new()
    charm.name = "Charm"
    var mesh := SphereMesh.new()
    mesh.radius = 0.10
    mesh.height = 0.20
    charm.mesh = mesh
    charm.position = Vector3(0.0, 0.0, 0.08)
    charm.material_override = _material(color)
    root.add_child(charm)


static func _rarity_color(rarity: String) -> Color:
    match rarity:
        "blue":
            return Color("#74B9FF")
        "purple":
            return Color("#B79CED")
        "gold":
            return Color("#F2C75C")
        "red":
            return Color("#F27D7D")
        "rainbow":
            return Color("#F7B7D2")
        _:
            return Color("#86D7A0")


static func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.78
    return material

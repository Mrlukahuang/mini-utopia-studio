class_name AssetVaultRuntime
extends RefCounted

const MANIFEST_PATH := "res://assets/external/library/asset_vault_manifest.json"

static var _manifest_cache: Dictionary = {}
static var _asset_by_id_cache: Dictionary = {}
static var _asset_by_filename_cache: Dictionary = {}


static func is_installed() -> bool:
    return FileAccess.file_exists(MANIFEST_PATH)


static func stats() -> Dictionary:
    var manifest := _manifest()
    return {
        "pack_count": int(manifest.get("pack_count", 0)),
        "asset_count": int(manifest.get("asset_count", 0)),
    }


static func entry_by_id(asset_id: String) -> Dictionary:
    _ensure_indexes()
    return _asset_by_id_cache.get(asset_id, {})


static func entries_by_filename(filename: String) -> Array:
    _ensure_indexes()
    return _asset_by_filename_cache.get(filename.to_lower(), [])


static func instantiate_by_id(
    parent: Node3D,
    asset_id: String,
    world_position: Vector3,
    yaw_degrees: float = 0.0,
    native_scale: float = 1.0,
    target_height: float = 0.0
) -> Node3D:
    var entry := entry_by_id(asset_id)
    if entry.is_empty():
        return null
    return _instantiate_entry(
        parent,
        entry,
        world_position,
        yaw_degrees,
        native_scale,
        target_height
    )


static func instantiate_first_filename(
    parent: Node3D,
    filename: String,
    world_position: Vector3,
    yaw_degrees: float = 0.0,
    native_scale: float = 1.0,
    target_height: float = 0.0
) -> Node3D:
    var entries := entries_by_filename(filename)
    if entries.is_empty():
        return null
    return _instantiate_entry(
        parent,
        entries[0],
        world_position,
        yaw_degrees,
        native_scale
    )


static func first_entry_matching(
    pack_terms: Array,
    filename_terms: Array
) -> Dictionary:
    for raw_entry in _manifest().get("assets", []):
        if typeof(raw_entry) != TYPE_DICTIONARY:
            continue

        var entry: Dictionary = raw_entry
        var pack_text := String(entry.get("pack", "")).to_lower()
        var source_member := String(entry.get("source_member", "")).to_lower()
        var filename := source_member.get_file()

        if not _contains_all(pack_text, pack_terms):
            continue
        if not _contains_all(filename, filename_terms):
            continue
        return entry

    return {}


static func instantiate_first_matching(
    parent: Node3D,
    pack_terms: Array,
    filename_terms: Array,
    world_position: Vector3,
    yaw_degrees: float = 0.0,
    native_scale: float = 1.0,
    target_height: float = 0.0
) -> Node3D:
    var entry := first_entry_matching(pack_terms, filename_terms)
    if entry.is_empty():
        return null
    return _instantiate_entry(
        parent,
        entry,
        world_position,
        yaw_degrees,
        native_scale,
        target_height
    )


static func _contains_all(haystack: String, terms: Array) -> bool:
    for raw_term in terms:
        var term := String(raw_term).to_lower()
        if not term.is_empty() and not haystack.contains(term):
            return false
    return true


static func _instantiate_entry(
    parent: Node3D,
    entry: Dictionary,
    world_position: Vector3,
    yaw_degrees: float,
    native_scale: float,
    target_height: float = 0.0
) -> Node3D:
    var res_path := String(entry.get("res_path", ""))
    if res_path.is_empty() or not ResourceLoader.exists(res_path):
        return null

    var resource := ResourceLoader.load(res_path)
    if not resource is PackedScene:
        return null

    var instance = (resource as PackedScene).instantiate()
    if not instance is Node3D:
        instance.queue_free()
        return null

    var wrapper := Node3D.new()
    wrapper.name = "Vault_" + String(entry.get("id", "asset"))
    wrapper.position = world_position
    wrapper.rotation_degrees.y = yaw_degrees
    parent.add_child(wrapper)
    wrapper.add_child(instance)

    var node := instance as Node3D
    if target_height > 0.0:
        var bounds := _bounds_in_root(node)
        if bounds.size.y > 0.0001:
            var scale_value := target_height / bounds.size.y
            node.scale = Vector3.ONE * scale_value
            var center_x := bounds.position.x + bounds.size.x * 0.5
            var center_z := bounds.position.z + bounds.size.z * 0.5
            node.position = Vector3(
                -center_x * scale_value,
                -bounds.position.y * scale_value,
                -center_z * scale_value
            )
    else:
        node.scale = Vector3.ONE * native_scale

    return wrapper


static func _manifest() -> Dictionary:
    if not _manifest_cache.is_empty():
        return _manifest_cache
    if not is_installed():
        return {}

    var file := FileAccess.open(MANIFEST_PATH, FileAccess.READ)
    if file == null:
        return {}

    var parsed = JSON.parse_string(file.get_as_text())
    if typeof(parsed) != TYPE_DICTIONARY:
        return {}

    _manifest_cache = parsed
    return _manifest_cache


static func _ensure_indexes() -> void:
    if not _asset_by_id_cache.is_empty():
        return

    for raw_entry in _manifest().get("assets", []):
        if typeof(raw_entry) != TYPE_DICTIONARY:
            continue

        var entry: Dictionary = raw_entry
        var asset_id := String(entry.get("id", ""))
        if not asset_id.is_empty():
            _asset_by_id_cache[asset_id] = entry

        var source_member := String(entry.get("source_member", ""))
        var filename := source_member.get_file().to_lower()
        if filename.is_empty():
            continue

        var bucket: Array = _asset_by_filename_cache.get(filename, [])
        bucket.append(entry)
        _asset_by_filename_cache[filename] = bucket


static func _bounds_in_root(root: Node3D) -> AABB:
    var meshes: Array = []
    _collect_meshes(root, meshes)
    var found := false
    var min_point := Vector3.ZERO
    var max_point := Vector3.ZERO
    var root_inverse := root.global_transform.affine_inverse()

    for value in meshes:
        var mesh_node := value as MeshInstance3D
        if mesh_node == null or mesh_node.mesh == null:
            continue

        var box := mesh_node.get_aabb()
        var to_root := root_inverse * mesh_node.global_transform
        for xi in range(2):
            for yi in range(2):
                for zi in range(2):
                    var corner := Vector3(
                        box.position.x + box.size.x * float(xi),
                        box.position.y + box.size.y * float(yi),
                        box.position.z + box.size.z * float(zi)
                    )
                    var point := to_root * corner
                    if not found:
                        min_point = point
                        max_point = point
                        found = true
                    else:
                        min_point = Vector3(
                            minf(min_point.x, point.x),
                            minf(min_point.y, point.y),
                            minf(min_point.z, point.z)
                        )
                        max_point = Vector3(
                            maxf(max_point.x, point.x),
                            maxf(max_point.y, point.y),
                            maxf(max_point.z, point.z)
                        )

    if not found:
        return AABB(Vector3.ZERO, Vector3.ONE)
    return AABB(min_point, max_point - min_point)


static func _collect_meshes(node: Node, output: Array) -> void:
    if node is MeshInstance3D:
        output.append(node)
    for child in node.get_children():
        _collect_meshes(child, output)

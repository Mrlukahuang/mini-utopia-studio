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
    native_scale: float = 1.0
) -> Node3D:
    var entry := entry_by_id(asset_id)
    if entry.is_empty():
        return null
    return _instantiate_entry(
        parent,
        entry,
        world_position,
        yaw_degrees,
        native_scale
    )


static func instantiate_first_filename(
    parent: Node3D,
    filename: String,
    world_position: Vector3,
    yaw_degrees: float = 0.0,
    native_scale: float = 1.0
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


static func _instantiate_entry(
    parent: Node3D,
    entry: Dictionary,
    world_position: Vector3,
    yaw_degrees: float,
    native_scale: float
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
    wrapper.scale = Vector3.ONE * native_scale
    parent.add_child(wrapper)
    wrapper.add_child(instance)
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

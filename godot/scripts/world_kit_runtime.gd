class_name WorldKitRuntime
extends RefCounted

const INSTALLED_MANIFEST_PATH := "res://assets/external/worldkit/installed_manifest.json"

static func has_installed() -> bool:
    return FileAccess.file_exists(INSTALLED_MANIFEST_PATH)

static func installed_entries() -> Array:
    if not has_installed():
        return []
    var file := FileAccess.open(INSTALLED_MANIFEST_PATH, FileAccess.READ)
    if file == null:
        return []
    var parsed = JSON.parse_string(file.get_as_text())
    if typeof(parsed) != TYPE_DICTIONARY:
        return []
    var assets = parsed.get("assets", [])
    return assets if typeof(assets) == TYPE_ARRAY else []

static func entry_by_id(asset_id: String) -> Dictionary:
    for entry in installed_entries():
        if String(entry.get("id", "")) == asset_id:
            return entry
    return {}

static func profile_available(profile_id: String) -> bool:
    if profile_id.is_empty():
        return true
    for entry in installed_entries():
        var paths = entry.get("profile_res_paths", {})
        if typeof(paths) == TYPE_DICTIONARY:
            if not String(paths.get(profile_id, "")).is_empty():
                return true
    return false

static func instantiate_asset(
    parent: Node3D,
    asset_id: String,
    position: Vector3,
    yaw_degrees: float = 0.0,
    native_scale: float = 1.0,
    target_height: float = 0.0,
    profile_id: String = "core_candidate_b"
) -> Node3D:
    var entry := entry_by_id(asset_id)
    if entry.is_empty():
        return null

    var res_path := String(entry.get("res_path", ""))
    if not profile_id.is_empty():
        var profile_paths = entry.get("profile_res_paths", {})
        if typeof(profile_paths) == TYPE_DICTIONARY:
            var candidate_path := String(profile_paths.get(profile_id, ""))
            if not candidate_path.is_empty():
                res_path = candidate_path

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
    wrapper.name = "WorldKit_" + asset_id
    wrapper.position = position
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

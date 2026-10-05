extends Node3D
class_name HeroRuntimeLoader

signal hero_loaded(hero_id: String, node: Node3D)
signal hero_failed(hero_id: String, reason: String)

@export var manifest_path := "res://assets/external/heroes/hero_manifest.json"
@export var show_placeholder_when_missing := true

var _pending_requests: Dictionary = {}

func _ready() -> void:
    call_deferred("_load_manifest")

func _load_manifest() -> void:
    if not FileAccess.file_exists(manifest_path):
        if show_placeholder_when_missing:
            _build_placeholder("NO HERO BUNDLE YET")
        return

    var text := FileAccess.get_file_as_string(manifest_path)
    var payload = JSON.parse_string(text)
    if typeof(payload) != TYPE_DICTIONARY:
        _build_placeholder("INVALID HERO MANIFEST")
        return

    var heroes = payload.get("heroes", [])
    if typeof(heroes) != TYPE_ARRAY or heroes.is_empty():
        _build_placeholder("EMPTY HERO MANIFEST")
        return

    for entry in heroes:
        if typeof(entry) == TYPE_DICTIONARY:
            _load_entry(entry)

func _load_entry(entry: Dictionary) -> void:
    var source := String(entry.get("source", ""))
    var hero_id := String(entry.get("hero_id", "hero"))
    if source.is_empty():
        hero_failed.emit(hero_id, "Hero source is empty.")
        return

    if source.begins_with("http://") or source.begins_with("https://"):
        var request := HTTPRequest.new()
        request.use_threads = true
        request.timeout = 120.0
        add_child(request)
        _pending_requests[request.get_instance_id()] = entry
        request.request_completed.connect(
            func(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
                var saved_entry: Dictionary = _pending_requests.get(request.get_instance_id(), entry)
                _pending_requests.erase(request.get_instance_id())
                if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
                    _fail_entry(saved_entry, "HTTP GLB download failed: %s / %s" % [result, response_code])
                    request.queue_free()
                    return
                _instantiate_glb(saved_entry, body, "")
                request.queue_free()
        )
        var error := request.request(source)
        if error != OK:
            _pending_requests.erase(request.get_instance_id())
            _fail_entry(entry, "Could not start HTTP request: %s" % error)
            request.queue_free()
        return

    if not FileAccess.file_exists(source):
        _fail_entry(entry, "GLB not found: %s" % source)
        return

    var bytes := FileAccess.get_file_as_bytes(source)
    _instantiate_glb(entry, bytes, source.get_base_dir())

func _instantiate_glb(entry: Dictionary, bytes: PackedByteArray, base_path: String) -> void:
    var hero_id := String(entry.get("hero_id", "hero"))
    if bytes.is_empty():
        _fail_entry(entry, "GLB payload is empty.")
        return

    var document := GLTFDocument.new()
    var state := GLTFState.new()
    state.base_path = base_path
    var error: Error = document.append_from_buffer(bytes, base_path, state)
    if error != OK:
        _fail_entry(entry, "Godot could not parse GLB: %s" % error)
        return

    var generated: Node = document.generate_scene(state)
    if generated == null or not (generated is Node3D):
        _fail_entry(entry, "GLB did not generate a 3D scene.")
        return

    var wrapper := Node3D.new()
    wrapper.name = "Hero_" + hero_id
    wrapper.position = _vec3(entry.get("position", [0.0, 4.5, -7.0]))
    add_child(wrapper)
    wrapper.add_child(generated)

    var target := _vec3(entry.get("target_size", [18.0, 8.0, 9.0]))
    _fit_to_envelope(generated as Node3D, target)

    var render_strategy := String(entry.get("render_strategy", ""))
    var should_collide := (
        bool(entry.get("collision_proxy", false))
        or render_strategy == "unified_glb"
    )
    if should_collide:
        _add_collision_proxy(wrapper, target)

    hero_loaded.emit(hero_id, wrapper)

func _fit_to_envelope(model: Node3D, target: Vector3) -> void:
    var bounds: AABB = _scene_aabb(model)
    if bounds.size.x <= 0.001 or bounds.size.y <= 0.001 or bounds.size.z <= 0.001:
        return

    var sx: float = target.x / bounds.size.x
    var sy: float = target.y / bounds.size.y
    var sz: float = target.z / bounds.size.z
    var uniform: float = minf(sx, minf(sy, sz)) * 0.94
    var center: Vector3 = bounds.position + bounds.size * 0.5

    model.scale = Vector3.ONE * uniform
    model.position = Vector3(
        -center.x * uniform,
        -bounds.position.y * uniform,
        -center.z * uniform
    )

func _scene_aabb(root: Node3D) -> AABB:
    var root_inverse: Transform3D = root.global_transform.affine_inverse()
    var found: bool = false
    var merged: AABB = AABB()
    var stack: Array[Node] = [root]

    while not stack.is_empty():
        var node: Node = stack.pop_back()
        if node is MeshInstance3D:
            var mesh_instance := node as MeshInstance3D
            if mesh_instance.mesh != null:
                var relative: Transform3D = root_inverse * mesh_instance.global_transform
                var transformed: AABB = _transform_aabb(mesh_instance.mesh.get_aabb(), relative)
                if not found:
                    merged = transformed
                    found = true
                else:
                    merged = merged.merge(transformed)
        for child in node.get_children():
            stack.append(child)

    return merged if found else AABB(Vector3.ZERO, Vector3.ONE)

func _transform_aabb(box: AABB, transform: Transform3D) -> AABB:
    var p: Vector3 = box.position
    var s: Vector3 = box.size
    var points: Array[Vector3] = [
        p,
        p + Vector3(s.x, 0, 0),
        p + Vector3(0, s.y, 0),
        p + Vector3(0, 0, s.z),
        p + Vector3(s.x, s.y, 0),
        p + Vector3(s.x, 0, s.z),
        p + Vector3(0, s.y, s.z),
        p + s,
    ]
    var first: Vector3 = transform * points[0]
    var minimum: Vector3 = first
    var maximum: Vector3 = first
    for point in points:
        var value: Vector3 = transform * point
        minimum = Vector3(
            minf(minimum.x, value.x),
            minf(minimum.y, value.y),
            minf(minimum.z, value.z)
        )
        maximum = Vector3(
            maxf(maximum.x, value.x),
            maxf(maximum.y, value.y),
            maxf(maximum.z, value.z)
        )
    return AABB(minimum, maximum - minimum)

func _add_collision_proxy(wrapper: Node3D, size: Vector3) -> void:
    var body := StaticBody3D.new()
    body.name = "HeroCollisionProxy"
    var shape_node := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = Vector3(size.x * 0.72, maxf(1.0, size.y * 0.55), size.z * 0.72)
    shape_node.shape = shape
    shape_node.position.y = shape.size.y * 0.5
    body.add_child(shape_node)
    wrapper.add_child(body)

func _fail_entry(entry: Dictionary, reason: String) -> void:
    var hero_id := String(entry.get("hero_id", "hero"))
    hero_failed.emit(hero_id, reason)
    push_warning("%s: %s" % [hero_id, reason])
    if show_placeholder_when_missing:
        _build_placeholder(String(entry.get("display_name", "Hero")) + "\n" + reason)

func _build_placeholder(message: String) -> void:
    if has_node("HeroPlaceholder"):
        return

    var root := Node3D.new()
    root.name = "HeroPlaceholder"
    root.position = Vector3(0, 5.2, -7.0)
    add_child(root)

    var body := MeshInstance3D.new()
    var body_mesh := SphereMesh.new()
    body_mesh.radius = 1.0
    body_mesh.height = 2.0
    body.mesh = body_mesh
    body.scale = Vector3(4.2, 1.65, 1.75)
    body.material_override = _material(Color("#5F7694"))
    root.add_child(body)

    for x in [-2.5, 2.5]:
        var fin := MeshInstance3D.new()
        var fin_mesh := BoxMesh.new()
        fin_mesh.size = Vector3(1.8, 0.25, 1.4)
        fin.mesh = fin_mesh
        fin.position = Vector3(x, -0.15, 0)
        fin.rotation_degrees.z = -18.0 if x < 0 else 18.0
        fin.material_override = _material(Color("#7287A2"))
        root.add_child(fin)

    var label := Label3D.new()
    label.text = message
    label.font_size = 28
    label.modulate = Color("#F4DFC1")
    label.outline_size = 7
    label.outline_modulate = Color("#293240")
    label.position = Vector3(0, 2.8, 0)
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    root.add_child(label)

func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.88
    return material

func _vec3(value) -> Vector3:
    if typeof(value) == TYPE_ARRAY and value.size() >= 3:
        return Vector3(float(value[0]), float(value[1]), float(value[2]))
    return Vector3.ZERO

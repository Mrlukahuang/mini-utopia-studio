class_name MiniUtopiaCreatorAvatarStage
extends SubViewportContainer

const DEFAULT_APPEARANCE := {
    "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
    "body_type": MiniUtopiaAvatarContract.BODY_STANDARD,
    "species_head_id": "species_head_human_v1",
    "surface_type": "skin",
    "surface_color_hex": "#F2C7A5",
    "eye_style_id": "eyes_round_soft_v1",
    "eye_color_hex": "#7A5238",
    "hair_style_id": "hair_short_v1",
    "hair_color_hex": "#5B4036",
}

var _viewport: SubViewport
var _world_root: Node3D
var _avatar_root: Node3D
var _visual: Node3D
var _sockets: Node3D
var _camera: Camera3D

var _body: MeshInstance3D
var _head: MeshInstance3D
var _hair: MeshInstance3D
var _eye_l: MeshInstance3D
var _eye_r: MeshInstance3D
var _ear_l: MeshInstance3D
var _ear_r: MeshInstance3D

var _appearance: Dictionary = DEFAULT_APPEARANCE.duplicate(true)
var _dragging := false
var _last_mouse_position := Vector2.ZERO
var _camera_distance := 6.2


func _ready() -> void:
    stretch = true
    mouse_filter = Control.MOUSE_FILTER_STOP
    gui_input.connect(_on_gui_input)
    _build_runtime_once()
    apply_appearance(_appearance)


func apply_appearance(appearance: Dictionary) -> void:
    if _avatar_root == null:
        _build_runtime_once()

    var merged := DEFAULT_APPEARANCE.duplicate(true)
    for key in appearance:
        merged[key] = appearance[key]
    _appearance = merged

    var body_type := String(
        merged.get(
            "body_type",
            MiniUtopiaAvatarContract.BODY_STANDARD
        )
    )
    if not MiniUtopiaAvatarContract.BODY_TYPES.has(body_type):
        body_type = MiniUtopiaAvatarContract.BODY_STANDARD

    var width_scale := MiniUtopiaAvatarContract.body_width_scale(body_type)
    _body.scale = Vector3(width_scale, 1.0, width_scale)

    for arm_name in ["ArmL", "ArmR"]:
        var arm := _visual.get_node_or_null(arm_name) as MeshInstance3D
        if arm != null:
            arm.position.x = (
                (-0.53 if arm_name == "ArmL" else 0.53)
                * width_scale
            )

    MiniUtopiaAvatarContract.apply_default_socket_positions(
        _sockets,
        body_type
    )

    var surface_color := _safe_color(
        String(merged.get("surface_color_hex", "#F2C7A5")),
        Color("#F2C7A5")
    )
    var hair_color := _safe_color(
        String(merged.get("hair_color_hex", "#5B4036")),
        Color("#5B4036")
    )
    var eye_color := _safe_color(
        String(merged.get("eye_color_hex", "#7A5238")),
        Color("#7A5238")
    )

    _apply_surface(
        String(merged.get("surface_type", "skin")),
        surface_color
    )
    _set_mesh_color(_hair, hair_color)
    _set_mesh_color(_eye_l, eye_color)
    _set_mesh_color(_eye_r, eye_color)

    _apply_species(String(merged.get("species_head_id", "")))
    _apply_hair(String(merged.get("hair_style_id", "")))


func current_appearance() -> Dictionary:
    return _appearance.duplicate(true)


func avatar_root_instance_id() -> int:
    return _avatar_root.get_instance_id() if _avatar_root != null else 0


func avatar_root() -> Node3D:
    return _avatar_root


func zoom_in() -> void:
    _camera_distance = max(4.3, _camera_distance - 0.45)
    _update_camera_distance()


func zoom_out() -> void:
    _camera_distance = min(8.4, _camera_distance + 0.45)
    _update_camera_distance()


func camera_distance() -> float:
    return _camera_distance


func reset_camera() -> void:
    if _avatar_root != null:
        _avatar_root.rotation = Vector3.ZERO
    _camera_distance = 6.2
    _update_camera_distance()


func _build_runtime_once() -> void:
    if _avatar_root != null:
        return

    _viewport = SubViewport.new()
    _viewport.name = "AvatarViewport"
    _viewport.transparent_bg = false
    _viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    _viewport.msaa_3d = Viewport.MSAA_4X
    add_child(_viewport)

    _world_root = Node3D.new()
    _world_root.name = "CreatorWorld"
    _viewport.add_child(_world_root)

    _build_environment()
    _build_avatar()


func _build_environment() -> void:
    var world_environment := WorldEnvironment.new()
    world_environment.name = "WorldEnvironment"
    var environment := Environment.new()
    environment.background_mode = Environment.BG_COLOR
    environment.background_color = Color("#E8E2FA")
    environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.ambient_light_color = Color("#FFF5E8")
    environment.ambient_light_energy = 0.82
    world_environment.environment = environment
    _world_root.add_child(world_environment)

    var key_light := DirectionalLight3D.new()
    key_light.name = "KeyLight"
    key_light.rotation_degrees = Vector3(-48.0, -28.0, 0.0)
    key_light.light_color = Color("#FFF3DA")
    key_light.light_energy = 1.2
    key_light.shadow_enabled = true
    _world_root.add_child(key_light)

    var fill := OmniLight3D.new()
    fill.name = "FillLight"
    fill.position = Vector3(-2.5, 3.0, 3.8)
    fill.light_color = Color("#D6E9FF")
    fill.light_energy = 1.7
    fill.omni_range = 8.0
    _world_root.add_child(fill)

    _camera = Camera3D.new()
    _camera.name = "CreatorCamera"
    _camera.position = Vector3(0.0, 1.35, _camera_distance)
    _camera.fov = 42.0
    _camera.current = true
    _world_root.add_child(_camera)

    var floor := MeshInstance3D.new()
    floor.name = "StageFloor"
    floor.position = Vector3(0.0, -0.08, 0.0)
    var floor_mesh := CylinderMesh.new()
    floor_mesh.top_radius = 2.1
    floor_mesh.bottom_radius = 2.1
    floor_mesh.height = 0.14
    floor.mesh = floor_mesh
    floor.material_override = _material(Color("#FFF8EE"))
    _world_root.add_child(floor)


func _build_avatar() -> void:
    _avatar_root = Node3D.new()
    _avatar_root.name = "AvatarRoot"
    _avatar_root.position = Vector3(0.0, 0.0, 0.0)
    _world_root.add_child(_avatar_root)

    _visual = Node3D.new()
    _visual.name = "Visual"
    _avatar_root.add_child(_visual)

    _body = _box(
        "Body",
        Vector3(0.0, 1.08, 0.0),
        Vector3(0.84, 1.08, 0.50),
        Color("#D7C2F3")
    )
    _visual.add_child(_body)

    _head = _sphere(
        "SpeciesHead",
        Vector3(0.0, 2.02, 0.0),
        Vector3(0.82, 0.78, 0.76),
        Color("#F2C7A5")
    )
    _visual.add_child(_head)

    _hair = _sphere(
        "Hair",
        Vector3(0.0, 2.27, -0.03),
        Vector3(0.86, 0.34, 0.79),
        Color("#5B4036")
    )
    _visual.add_child(_hair)

    _eye_l = _sphere(
        "EyeL",
        Vector3(-0.18, 2.05, 0.36),
        Vector3(0.11, 0.14, 0.08),
        Color("#7A5238")
    )
    _visual.add_child(_eye_l)

    _eye_r = _sphere(
        "EyeR",
        Vector3(0.18, 2.05, 0.36),
        Vector3(0.11, 0.14, 0.08),
        Color("#7A5238")
    )
    _visual.add_child(_eye_r)

    var arm_l := _box(
        "ArmL",
        Vector3(-0.53, 1.12, 0.0),
        Vector3(0.23, 0.82, 0.24),
        Color("#F2C7A5")
    )
    _visual.add_child(arm_l)

    var arm_r := _box(
        "ArmR",
        Vector3(0.53, 1.12, 0.0),
        Vector3(0.23, 0.82, 0.24),
        Color("#F2C7A5")
    )
    _visual.add_child(arm_r)

    for side in [-1.0, 1.0]:
        var leg := _box(
            "LegL" if side < 0.0 else "LegR",
            Vector3(0.23 * side, 0.38, 0.0),
            Vector3(0.31, 0.76, 0.34),
            Color("#BDE3F5")
        )
        _visual.add_child(leg)

    _ear_l = _sphere(
        "EarL",
        Vector3(-0.48, 2.47, 0.0),
        Vector3(0.22, 0.34, 0.18),
        Color("#F2C7A5")
    )
    _visual.add_child(_ear_l)

    _ear_r = _sphere(
        "EarR",
        Vector3(0.48, 2.47, 0.0),
        Vector3(0.22, 0.34, 0.18),
        Color("#F2C7A5")
    )
    _visual.add_child(_ear_r)

    _sockets = Node3D.new()
    _sockets.name = "Sockets"
    _avatar_root.add_child(_sockets)
    MiniUtopiaAvatarContract.ensure_socket_nodes(_sockets)
    MiniUtopiaAvatarContract.apply_default_socket_positions(
        _sockets,
        MiniUtopiaAvatarContract.BODY_STANDARD
    )


func _apply_surface(surface_type: String, color: Color) -> void:
    _set_mesh_color(_head, color)
    _set_mesh_color(_ear_l, color)
    _set_mesh_color(_ear_r, color)

    for arm_name in ["ArmL", "ArmR"]:
        var arm := _visual.get_node_or_null(arm_name) as MeshInstance3D
        if arm != null:
            _set_mesh_color(arm, color)

    var material := _head.material_override as StandardMaterial3D
    if material == null:
        return

    material.metallic = 0.0
    material.roughness = 0.84
    match surface_type:
        "metal":
            material.metallic = 0.72
            material.roughness = 0.32
        "cloud":
            material.roughness = 1.0
        "wool":
            material.roughness = 0.96
        "fur":
            material.roughness = 0.92


func _apply_species(species_head_id: String) -> void:
    var is_cat := species_head_id == "species_head_cat_v1"
    var is_sheep := species_head_id == "species_head_sheep_v1"
    _ear_l.visible = is_cat or is_sheep
    _ear_r.visible = is_cat or is_sheep

    if is_cat:
        _ear_l.scale = Vector3(0.72, 1.18, 0.72)
        _ear_r.scale = Vector3(0.72, 1.18, 0.72)
    elif is_sheep:
        _ear_l.scale = Vector3(1.10, 0.72, 1.0)
        _ear_r.scale = Vector3(1.10, 0.72, 1.0)

    if species_head_id == "species_head_robot_v1":
        _head.scale = Vector3(0.82, 0.72, 0.72)
    elif species_head_id == "species_head_cloud_v1":
        _head.scale = Vector3(0.92, 0.82, 0.82)
    else:
        _head.scale = Vector3(0.82, 0.78, 0.76)


func _apply_hair(hair_style_id: String) -> void:
    _hair.visible = hair_style_id != "hair_none"
    if not _hair.visible:
        return

    if hair_style_id == "hair_long_wavy_v1":
        _hair.scale = Vector3(0.92, 0.66, 0.84)
        _hair.position.y = 2.16
    elif hair_style_id == "hair_ponytail_v1":
        _hair.scale = Vector3(0.84, 0.42, 0.80)
        _hair.position.y = 2.25
    elif hair_style_id == "hair_fluffy_v1":
        _hair.scale = Vector3(0.98, 0.47, 0.92)
        _hair.position.y = 2.30
    elif hair_style_id == "hair_bob_v1":
        _hair.scale = Vector3(0.90, 0.50, 0.84)
        _hair.position.y = 2.20
    else:
        _hair.scale = Vector3(0.86, 0.34, 0.79)
        _hair.position.y = 2.27


func _on_gui_input(event: InputEvent) -> void:
    if event is InputEventMouseButton:
        var mouse_button := event as InputEventMouseButton
        if mouse_button.button_index == MOUSE_BUTTON_LEFT:
            _dragging = mouse_button.pressed
            _last_mouse_position = mouse_button.position
            accept_event()
        elif (
            mouse_button.pressed
            and mouse_button.button_index == MOUSE_BUTTON_WHEEL_UP
        ):
            zoom_in()
            accept_event()
        elif (
            mouse_button.pressed
            and mouse_button.button_index == MOUSE_BUTTON_WHEEL_DOWN
        ):
            zoom_out()
            accept_event()

    elif event is InputEventMouseMotion and _dragging:
        var motion := event as InputEventMouseMotion
        var delta := motion.position - _last_mouse_position
        _last_mouse_position = motion.position
        _avatar_root.rotate_y(-delta.x * 0.012)
        accept_event()


func _update_camera_distance() -> void:
    if _camera != null:
        _camera.position = Vector3(0.0, 1.35, _camera_distance)


func _box(
    node_name: String,
    node_position: Vector3,
    size: Vector3,
    color: Color
) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = node_position
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.material_override = _material(color)
    return node


func _sphere(
    node_name: String,
    node_position: Vector3,
    scale_value: Vector3,
    color: Color
) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = node_position
    node.scale = scale_value
    var mesh := SphereMesh.new()
    mesh.radius = 0.5
    mesh.height = 1.0
    node.mesh = mesh
    node.material_override = _material(color)
    return node


func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.84
    return material


func _set_mesh_color(node: MeshInstance3D, color: Color) -> void:
    if node == null:
        return
    var material := node.material_override as StandardMaterial3D
    if material == null:
        material = _material(color)
        node.material_override = material
    else:
        material.albedo_color = color


func _safe_color(value: String, fallback: Color) -> Color:
    if value.is_empty() or not value.begins_with("#"):
        return fallback
    return Color(value)

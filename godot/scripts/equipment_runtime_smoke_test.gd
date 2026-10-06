extends Node3D

const LOADOUT_PATH := "res://config/runtime/equipment_smoke_v0_1.json"
const BODY_TYPES := [
    MiniUtopiaAvatarContract.BODY_SLIM,
    MiniUtopiaAvatarContract.BODY_STANDARD,
    MiniUtopiaAvatarContract.BODY_CHUBBY,
]


func _ready() -> void:
    var payload := _load_payload()
    _build_environment()
    _build_stage(payload)
    _build_hud(payload)


func _load_payload() -> Dictionary:
    if not FileAccess.file_exists(LOADOUT_PATH):
        push_error("EQ-02 smoke payload missing: " + LOADOUT_PATH)
        return {}
    var file := FileAccess.open(LOADOUT_PATH, FileAccess.READ)
    if file == null:
        return {}
    var parsed = JSON.parse_string(file.get_as_text())
    return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


func _build_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color("#DCEFF7")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#FFF4E6")
    env.ambient_light_energy = 0.62
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-48.0, -28.0, 0.0)
    sun.light_energy = 1.0
    sun.shadow_enabled = true
    add_child(sun)

    var camera := Camera3D.new()
    camera.position = Vector3(0.0, 3.1, 9.2)
    camera.rotation_degrees = Vector3(-8.0, 0.0, 0.0)
    camera.current = true
    add_child(camera)

    var floor := MeshInstance3D.new()
    var floor_mesh := BoxMesh.new()
    floor_mesh.size = Vector3(12.0, 0.18, 5.4)
    floor.mesh = floor_mesh
    floor.position = Vector3(0.0, -0.10, 0.0)
    floor.material_override = _material(Color("#FFF9EE"))
    add_child(floor)


func _build_stage(payload: Dictionary) -> void:
    var x_positions := [-2.5, 0.0, 2.5]
    var yaws := [-18.0, 0.0, 18.0]

    for index in range(BODY_TYPES.size()):
        var body_type: String = BODY_TYPES[index]
        var avatar := _build_avatar(body_type)
        avatar.position = Vector3(x_positions[index], 0.0, 0.0)
        avatar.rotation_degrees.y = yaws[index]
        add_child(avatar)

        var attached := MiniUtopiaEquipmentRuntime.attach_loadout(
            avatar,
            payload
        )
        print(
            "EQ-02 smoke: ",
            MiniUtopiaAvatarContract.body_label(body_type),
            " attached slots = ",
            ", ".join(attached.keys())
        )


func _build_avatar(body_type: String) -> Node3D:
    var root := Node3D.new()
    root.name = "Avatar_" + MiniUtopiaAvatarContract.body_label(body_type)

    var visual := Node3D.new()
    visual.name = "Visual"
    root.add_child(visual)

    var width_scale := MiniUtopiaAvatarContract.body_width_scale(body_type)
    _add_box(
        visual,
        "Body",
        Vector3(0.0, 0.92, 0.0),
        Vector3(0.78 * width_scale, 0.92, 0.44 * width_scale),
        Color("#D7C2F3")
    )
    _add_sphere(
        visual,
        "SpeciesHead",
        Vector3(0.0, 1.72, 0.0),
        Vector3(0.72 * width_scale, 0.67, 0.66),
        Color("#F2C7A5")
    )

    for side in [-1.0, 1.0]:
        _add_box(
            visual,
            "Arm",
            Vector3(0.52 * width_scale * side, 1.05, 0.0),
            Vector3(0.22, 0.72, 0.22),
            Color("#F2C7A5")
        )
        _add_box(
            visual,
            "Leg",
            Vector3(0.22 * side, 0.34, 0.0),
            Vector3(0.27, 0.68, 0.30),
            Color("#BFDFF5")
        )

    var sockets := Node3D.new()
    sockets.name = "Sockets"
    root.add_child(sockets)
    MiniUtopiaAvatarContract.ensure_socket_nodes(sockets)
    MiniUtopiaAvatarContract.apply_default_socket_positions(
        sockets,
        body_type
    )

    var label := Label3D.new()
    label.text = MiniUtopiaAvatarContract.body_label(body_type)
    label.position = Vector3(0.0, 2.50, 0.0)
    label.font_size = 40
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    root.add_child(label)

    return root


func _build_hud(payload: Dictionary) -> void:
    var layer := CanvasLayer.new()
    add_child(layer)

    var panel := ColorRect.new()
    panel.position = Vector2(18.0, 18.0)
    panel.size = Vector2(820.0, 138.0)
    panel.color = Color(0.03, 0.06, 0.08, 0.80)
    layer.add_child(panel)

    var stats: Dictionary = payload.get("final_stats", {})
    var equipped: Dictionary = payload.get("equipped", {})

    var label := Label.new()
    label.position = Vector2(16.0, 10.0)
    label.text = (
        "EQ-02 · 3D Equipment Runtime\n"
        + "Same loadout attached to Slim / Standard / Chubby\n"
        + "HP %s · ATK %s · DEF %s · Slots %s"
        % [
            stats.get("hp", 0),
            stats.get("atk", 0),
            stats.get("defense", 0),
            ", ".join(equipped.keys()),
        ]
    )
    label.add_theme_font_size_override("font_size", 17)
    panel.add_child(label)


func _add_box(
    parent: Node3D,
    node_name: String,
    position: Vector3,
    size: Vector3,
    color: Color
) -> void:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = position
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)


func _add_sphere(
    parent: Node3D,
    node_name: String,
    position: Vector3,
    scale_value: Vector3,
    color: Color
) -> void:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = position
    node.scale = scale_value
    var mesh := SphereMesh.new()
    mesh.radius = 0.5
    mesh.height = 1.0
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)


func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.86
    return material

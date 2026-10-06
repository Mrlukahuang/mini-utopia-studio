extends Node3D

const PROFILE_ID := "core_candidate_b"
const PAIRS := [
    {"id": "forest_tree_round", "height": 4.4},
    {"id": "forest_rock", "height": 1.25},
    {"id": "medieval_home", "height": 4.1},
    {"id": "medieval_tower", "height": 4.4},
]

func _ready() -> void:
    _setup_environment()
    _setup_camera()
    _build_floor()
    _build_row(-3.4, "SOURCE", "")
    _build_row(3.4, "CANDIDATE B", PROFILE_ID)
    _build_hud()

func _setup_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color("#8E8B86")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#F6F0E7")
    env.ambient_light_energy = 0.24
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.tonemap_exposure = 1.0
    world_env.environment = env
    add_child(world_env)

    var key_light := DirectionalLight3D.new()
    key_light.rotation_degrees = Vector3(-48.0, -32.0, 0.0)
    key_light.light_color = Color("#FFF3E0")
    key_light.light_energy = 0.62
    key_light.shadow_enabled = true
    add_child(key_light)

    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-25.0, 142.0, 0.0)
    fill.light_color = Color("#AFCFE5")
    fill.light_energy = 0.08
    fill.shadow_enabled = false
    add_child(fill)

func _setup_camera() -> void:
    var camera := Camera3D.new()
    camera.position = Vector3(0.0, 14.5, 29.0)
    camera.fov = 48.0
    camera.current = true
    add_child(camera)
    camera.look_at(Vector3(0.0, 2.0, 0.0), Vector3.UP)

func _build_floor() -> void:
    var floor_node := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = Vector3(31.0, 0.35, 13.5)
    floor_node.mesh = mesh
    floor_node.position = Vector3(0.0, -0.25, 0.0)
    var material := StandardMaterial3D.new()
    material.albedo_color = Color("#817D78")
    material.roughness = 0.94
    floor_node.material_override = material
    add_child(floor_node)

func _build_row(z: float, title: String, profile_id: String) -> void:
    var spacing := 5.2
    var start_x := -float(PAIRS.size() - 1) * spacing * 0.5
    for i in PAIRS.size():
        var item: Dictionary = PAIRS[i]
        var x := start_x + float(i) * spacing
        GoldenAnchorRuntime.instantiate_anchor(
            self,
            String(item["id"]),
            Vector3(x, 0.0, z),
            float(item["height"]),
            INF,
            profile_id
        )
        _add_label(String(item["id"]), Vector3(x, 5.0, z))

    var row_label := Label3D.new()
    row_label.text = title
    row_label.font_size = 58
    row_label.modulate = Color("#343447")
    row_label.outline_size = 10
    row_label.outline_modulate = Color("#F6F0E7")
    row_label.position = Vector3(-12.4, 2.7, z)
    row_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(row_label)

func _add_label(value: String, position: Vector3) -> void:
    var label := Label3D.new()
    label.text = value
    label.font_size = 30
    label.modulate = Color("#343447")
    label.outline_size = 8
    label.outline_modulate = Color("#F6F0E7")
    label.position = position
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(label)

func _build_hud() -> void:
    var hud := CanvasLayer.new()
    add_child(hud)

    var panel := ColorRect.new()
    panel.offset_left = 18.0
    panel.offset_top = 18.0
    panel.offset_right = 760.0
    panel.offset_bottom = 96.0
    panel.color = Color(0.08, 0.07, 0.1, 0.82)
    hud.add_child(panel)

    var title := Label.new()
    title.offset_left = 16.0
    title.offset_top = 10.0
    title.offset_right = 730.0
    title.offset_bottom = 38.0
    title.text = "Mini Utopia · Golden Palette Compare"
    panel.add_child(title)

    var info := Label.new()
    info.offset_left = 16.0
    info.offset_top = 42.0
    info.offset_right = 730.0
    info.offset_bottom = 70.0
    info.text = "SOURCE vs core_candidate_b · fixed lighting / camera / exposure"
    panel.add_child(info)

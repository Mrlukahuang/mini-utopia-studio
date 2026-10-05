extends Node3D

const ANCHOR_ORDER := [
    "forest_tree_round",
    "forest_tree_branching",
    "forest_bush",
    "forest_rock",
    "medieval_home",
    "medieval_tower",
    "medieval_bridge",
    "platformer_platform",
    "platformer_slope",
    "dungeon_chest",
    "adventurer_knight",
    "skeleton_minion",
    "kenney_castle_tower",
]

func _ready() -> void:
    _setup_environment()
    _setup_camera()
    _build_floor()
    _build_hud()

    if not GoldenAnchorRuntime.has_installed():
        _show_missing_message()
        return

    _build_lineup()

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
    camera.position = Vector3(0.0, 13.5, 30.0)
    camera.fov = 50.0
    camera.current = true
    add_child(camera)
    camera.look_at(Vector3(0.0, 2.0, 0.0), Vector3.UP)

func _build_floor() -> void:
    var floor_node := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = Vector3(34.0, 0.35, 14.0)
    floor_node.mesh = mesh
    floor_node.position = Vector3(0.0, -0.25, 0.0)
    var material := StandardMaterial3D.new()
    material.albedo_color = Color("#817D78")
    material.roughness = 0.94
    floor_node.material_override = material
    add_child(floor_node)

func _build_lineup() -> void:
    var front_count := 7
    var spacing := 4.25

    for i in ANCHOR_ORDER.size():
        var row := 0 if i < front_count else 1
        var index_in_row := i if row == 0 else i - front_count
        var row_count := front_count if row == 0 else ANCHOR_ORDER.size() - front_count
        var start_x := -float(row_count - 1) * spacing * 0.5
        var x := start_x + float(index_in_row) * spacing
        var z := 2.8 if row == 0 else -3.0
        var anchor_id: String = ANCHOR_ORDER[i]

        var entry := GoldenAnchorRuntime.entry_by_id(anchor_id)
        var target_height := float(entry.get("target_height", 2.5))
        # Keep the audit lineup readable; very large structures are normalized.
        target_height = minf(target_height, 4.0)

        var instance := GoldenAnchorRuntime.instantiate_anchor(
            self,
            anchor_id,
            Vector3(x, 0.0, z),
            target_height
        )
        if instance != null:
            _add_label(anchor_id, Vector3(x, 4.65, z))

func _add_label(value: String, position: Vector3) -> void:
    var label := Label3D.new()
    label.text = value
    label.font_size = 32
    label.modulate = Color("#343447")
    label.outline_size = 8
    label.outline_modulate = Color("#F6F0E7")
    label.position = position
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(label)

func _show_missing_message() -> void:
    var label := Label3D.new()
    label.text = "Golden anchors are not installed.\nRun: python3 tools/install_golden_anchors.py"
    label.font_size = 48
    label.modulate = Color("#343447")
    label.outline_size = 10
    label.outline_modulate = Color("#F6F0E7")
    label.position = Vector3(0.0, 3.0, 0.0)
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(label)

func _build_hud() -> void:
    var hud := CanvasLayer.new()
    add_child(hud)

    var panel := ColorRect.new()
    panel.offset_left = 18.0
    panel.offset_top = 18.0
    panel.offset_right = 710.0
    panel.offset_bottom = 90.0
    panel.color = Color(0.08, 0.07, 0.1, 0.82)
    hud.add_child(panel)

    var title := Label.new()
    title.offset_left = 16.0
    title.offset_top = 10.0
    title.offset_right = 680.0
    title.offset_bottom = 36.0
    title.text = "Mini Utopia · Golden Style Anchors v1"
    panel.add_child(title)

    var info := Label.new()
    info.offset_left = 16.0
    info.offset_top = 39.0
    info.offset_right = 680.0
    info.offset_bottom = 65.0
    info.text = "Source geometry lineup · KayKit primary anchor + Kenney compatibility check"
    panel.add_child(info)

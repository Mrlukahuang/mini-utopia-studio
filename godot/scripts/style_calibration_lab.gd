extends Node3D

const PALETTE_PATH := "res://config/style/core_palette_candidates_v0_9.json"
const GoldenAnchorRuntime = preload("res://scripts/golden_anchor_runtime.gd")

var palette: Dictionary = {}
var color_materials: Array[StandardMaterial3D] = []

func _ready() -> void:
    palette = _load_palette()
    _setup_environment()
    _setup_camera()
    _build_floor()
    _build_palette_strip()
    _build_station(Vector3(-12.0, 0.0, 0.0), "COLOR", "color")
    _build_station(Vector3(0.0, 0.0, 0.0), "GRAYSCALE", "grayscale")
    _build_station(Vector3(12.0, 0.0, 0.0), "SILHOUETTE", "silhouette")
    _build_hud()

func _load_palette() -> Dictionary:
    var file := FileAccess.open(PALETTE_PATH, FileAccess.READ)
    if file == null:
        push_error("Style Calibration Lab could not open palette: " + PALETTE_PATH)
        return {}
    var parsed = JSON.parse_string(file.get_as_text())
    if typeof(parsed) != TYPE_DICTIONARY:
        push_error("Style Calibration Lab palette JSON is invalid")
        return {}
    return parsed.get("colors", {})

func _color(key: String, fallback: String = "#FF00FF") -> Color:
    return Color(String(palette.get(key, fallback)))

func _material(color: Color, roughness: float = 0.88) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = roughness
    return material

func _raw_material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 1.0
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    return material

func _mode_color(source: Color, mode: String) -> Color:
    if mode == "grayscale":
        var luma := source.get_luminance()
        return Color(luma, luma, luma, 1.0)
    if mode == "silhouette":
        return _color("deep_ink", "#343447")
    return source

func _box(parent: Node3D, pos: Vector3, size: Vector3, color: Color, mode: String) -> MeshInstance3D:
    var mesh := BoxMesh.new()
    mesh.size = size
    var node := MeshInstance3D.new()
    node.mesh = mesh
    node.position = pos
    node.material_override = _material(_mode_color(color, mode))
    parent.add_child(node)
    return node

func _sphere(parent: Node3D, pos: Vector3, radius: float, color: Color, mode: String, scale_value: Vector3 = Vector3.ONE) -> MeshInstance3D:
    var mesh := SphereMesh.new()
    mesh.radius = radius
    mesh.height = radius * 2.0
    mesh.radial_segments = 20
    mesh.rings = 10
    var node := MeshInstance3D.new()
    node.mesh = mesh
    node.position = pos
    node.scale = scale_value
    node.material_override = _material(_mode_color(color, mode))
    parent.add_child(node)
    return node

func _cylinder(parent: Node3D, pos: Vector3, radius: float, height: float, color: Color, mode: String) -> MeshInstance3D:
    var mesh := CylinderMesh.new()
    mesh.top_radius = radius
    mesh.bottom_radius = radius * 1.04
    mesh.height = height
    mesh.radial_segments = 16
    var node := MeshInstance3D.new()
    node.mesh = mesh
    node.position = pos
    node.material_override = _material(_mode_color(color, mode))
    parent.add_child(node)
    return node

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
    camera.position = Vector3(0.0, 13.5, 31.0)
    camera.fov = 42.0
    camera.current = true
    add_child(camera)
    camera.look_at(Vector3(0.0, 2.1, 0.0), Vector3.UP)

func _build_floor() -> void:
    var floor := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = Vector3(42.0, 0.35, 18.0)
    floor.mesh = mesh
    floor.position = Vector3(0.0, -0.25, 0.0)
    floor.material_override = _material(Color("#817D78"), 0.94)
    add_child(floor)

func _build_station(origin: Vector3, title: String, mode: String) -> void:
    var root := Node3D.new()
    root.name = title
    root.position = origin
    add_child(root)

    if mode == "color" and GoldenAnchorRuntime.has_installed():
        _build_real_golden_station(root)
    else:
        _build_architecture(root, Vector3(-3.6, 0.0, 0.0), mode)
        _build_nature(root, Vector3(0.0, 0.0, 0.0), mode)
        _build_character(root, Vector3(3.0, 0.0, 0.0), mode)
        _build_hero_mass(root, Vector3(0.3, 0.4, -3.4), mode)

    var label := Label3D.new()
    label.text = title
    label.font_size = 78
    label.modulate = Color("#343447")
    label.outline_size = 10
    label.outline_modulate = Color("#F6F0E7")
    label.position = Vector3(0.0, 5.85, 0.0)
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    root.add_child(label)

func _build_real_golden_station(parent: Node3D) -> void:
    # Five representative real assets replace the procedural COLOR lane once
    # the local Golden lineup has been installed. Grayscale/Silhouette lanes
    # remain deterministic procedural controls until palette remapping exists.
    GoldenAnchorRuntime.instantiate_anchor(
        parent, "medieval_home", Vector3(-3.6, 0.0, 0.0), 4.25
    )
    GoldenAnchorRuntime.instantiate_anchor(
        parent, "forest_tree_round", Vector3(0.0, 0.0, -0.15), 4.75
    )
    GoldenAnchorRuntime.instantiate_anchor(
        parent, "adventurer_knight", Vector3(3.1, 0.0, 0.3), 3.25
    )
    GoldenAnchorRuntime.instantiate_anchor(
        parent, "dungeon_chest", Vector3(-1.85, 0.0, 1.85), 1.1
    )
    GoldenAnchorRuntime.instantiate_anchor(
        parent, "forest_rock", Vector3(1.6, 0.0, 1.65), 1.05
    )


func _build_architecture(parent: Node3D, origin: Vector3, mode: String) -> void:
    _box(parent, origin + Vector3(0.0, 1.5, 0.0), Vector3(3.7, 3.0, 3.0), _color("cream_base"), mode)
    _box(parent, origin + Vector3(0.0, 3.45, 0.0), Vector3(4.3, 0.8, 3.55), _color("peach"), mode)
    _box(parent, origin + Vector3(0.0, 1.0, 1.55), Vector3(1.0, 1.9, 0.18), _color("cocoa"), mode)
    _box(parent, origin + Vector3(-1.1, 1.8, 1.56), Vector3(0.75, 0.75, 0.16), _color("powder_blue"), mode)
    _box(parent, origin + Vector3(1.1, 1.8, 1.56), Vector3(0.75, 0.75, 0.16), _color("powder_blue"), mode)
    _cylinder(parent, origin + Vector3(1.25, 4.25, -0.6), 0.32, 1.7, _color("apricot"), mode)

func _build_nature(parent: Node3D, origin: Vector3, mode: String) -> void:
    _cylinder(parent, origin + Vector3(0.0, 1.35, 0.0), 0.45, 2.7, _color("cocoa"), mode)
    _sphere(parent, origin + Vector3(0.0, 3.65, 0.0), 1.65, _color("sage"), mode, Vector3(1.05, 1.0, 1.0))
    _sphere(parent, origin + Vector3(1.0, 3.35, 0.2), 1.15, _color("mint"), mode)
    _sphere(parent, origin + Vector3(-0.9, 3.45, -0.25), 1.2, _color("moss"), mode)

    _sphere(parent, origin + Vector3(1.75, 0.6, 1.0), 0.75, _color("warm_taupe"), mode, Vector3(1.2, 0.75, 1.0))
    _sphere(parent, origin + Vector3(2.45, 0.38, 1.15), 0.48, _color("cream_warm"), mode, Vector3(1.0, 0.65, 1.0))

func _build_character(parent: Node3D, origin: Vector3, mode: String) -> void:
    _box(parent, origin + Vector3(0.0, 1.25, 0.0), Vector3(1.15, 1.45, 0.75), _color("lavender"), mode)
    _sphere(parent, origin + Vector3(0.0, 2.65, 0.0), 0.9, _color("cream_warm"), mode, Vector3(1.0, 0.92, 0.95))
    _box(parent, origin + Vector3(-0.72, 1.32, 0.0), Vector3(0.32, 1.15, 0.38), _color("strawberry"), mode)
    _box(parent, origin + Vector3(0.72, 1.32, 0.0), Vector3(0.32, 1.15, 0.38), _color("strawberry"), mode)
    _box(parent, origin + Vector3(-0.32, 0.35, 0.0), Vector3(0.38, 0.85, 0.5), _color("deep_ink"), mode)
    _box(parent, origin + Vector3(0.32, 0.35, 0.0), Vector3(0.38, 0.85, 0.5), _color("deep_ink"), mode)

func _build_hero_mass(parent: Node3D, origin: Vector3, mode: String) -> void:
    _sphere(parent, origin + Vector3(0.0, 1.3, 0.0), 2.2, _color("powder_blue"), mode, Vector3(1.65, 0.8, 0.9))
    _sphere(parent, origin + Vector3(-2.7, 1.3, 0.0), 1.05, _color("powder_blue"), mode, Vector3(1.15, 0.45, 0.55))
    _box(parent, origin + Vector3(0.25, 2.7, 0.0), Vector3(3.0, 0.45, 1.8), _color("cream_base"), mode)
    _cylinder(parent, origin + Vector3(0.2, 3.45, 0.0), 0.75, 1.35, _color("peach"), mode)
    _sphere(parent, origin + Vector3(1.25, 3.35, 0.2), 0.55, _color("glow_gold"), mode)

func _build_palette_strip() -> void:
    var keys := [
        "cream_base", "cream_warm", "peach", "strawberry", "apricot",
        "butter_yellow", "mint", "sage", "moss", "powder_blue",
        "aqua", "lavender", "lilac", "warm_taupe", "cocoa", "deep_ink", "glow_gold"
    ]
    var start_x := -12.8
    for i in keys.size():
        var key: String = keys[i]

        var raw := MeshInstance3D.new()
        var raw_mesh := BoxMesh.new()
        raw_mesh.size = Vector3(1.38, 0.28, 1.05)
        raw.mesh = raw_mesh
        raw.position = Vector3(start_x + float(i) * 1.6, 0.18, 7.15)
        raw.material_override = _raw_material(_color(key))
        add_child(raw)

        var lit := MeshInstance3D.new()
        var lit_mesh := BoxMesh.new()
        lit_mesh.size = Vector3(1.38, 0.28, 1.05)
        lit.mesh = lit_mesh
        lit.position = Vector3(start_x + float(i) * 1.6, 0.18, 5.75)
        lit.material_override = _material(_color(key), 0.9)
        add_child(lit)

    _add_palette_row_label("RAW", Vector3(-14.35, 0.75, 7.15))
    _add_palette_row_label("LIT", Vector3(-14.35, 0.75, 5.75))

func _add_palette_row_label(text_value: String, pos: Vector3) -> void:
    var label := Label3D.new()
    label.text = text_value
    label.font_size = 54
    label.modulate = Color("#343447")
    label.outline_size = 8
    label.outline_modulate = Color("#F6F0E7")
    label.position = pos
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(label)

func _build_hud() -> void:
    var hud := CanvasLayer.new()
    add_child(hud)

    var panel := ColorRect.new()
    panel.offset_left = 18.0
    panel.offset_top = 18.0
    panel.offset_right = 650.0
    panel.offset_bottom = 105.0
    panel.color = Color(0.08, 0.07, 0.1, 0.82)
    hud.add_child(panel)

    var title := Label.new()
    title.offset_left = 16.0
    title.offset_top = 10.0
    title.offset_right = 610.0
    title.offset_bottom = 38.0
    title.text = "Mini Utopia · Style Calibration Lab v0.1"
    panel.add_child(title)

    var info := Label.new()
    info.offset_left = 16.0
    info.offset_top = 40.0
    info.offset_right = 610.0
    info.offset_bottom = 76.0
    var real_state := "REAL GOLDEN ASSETS INSTALLED" if GoldenAnchorRuntime.has_installed() else "PROCEDURAL FALLBACK · run tools/install_golden_anchors.py"
    info.text = "Palette v0.9 · COLOR / GRAYSCALE / SILHOUETTE\n" + real_state
    panel.add_child(info)

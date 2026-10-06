extends Node3D

const LAYOUT_PATH := "res://config/worlds/forest_village_50x50_v0_1.json"
const PALETTE_PATH := "res://config/style/core_palette_candidates_v0_9.json"

var layout: Dictionary = {}
var palette: Dictionary = {}

func _ready() -> void:
    layout = _load_json(LAYOUT_PATH)
    palette = _load_json(PALETTE_PATH).get("colors", {})
    _setup_environment()
    _build_ground()
    _build_creek()
    _build_paths()
    _build_golden_world()
    _build_boundary()
    _build_hud()
    _build_world_labels()

func _load_json(path: String) -> Dictionary:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        push_error("Forest Village could not open " + path)
        return {}
    var parsed = JSON.parse_string(file.get_as_text())
    return parsed if typeof(parsed) == TYPE_DICTIONARY else {}

func _color(key: String, fallback: String = "#FF00FF") -> Color:
    return Color(String(palette.get(key, fallback)))

func _material(color: Color, roughness: float = 0.9) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = roughness
    return material

func _setup_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = _color("powder_blue", "#86C7E8").lightened(0.16)
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = _color("cream_warm", "#E7CE9E").lightened(0.1)
    env.ambient_light_energy = 0.32
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.tonemap_exposure = 1.0
    env.fog_enabled = true
    env.fog_light_color = _color("powder_blue", "#86C7E8").lightened(0.2)
    env.fog_light_energy = 0.18
    env.fog_density = 0.003
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-52.0, -35.0, 0.0)
    sun.light_color = _color("cream_warm", "#E7CE9E").lightened(0.2)
    sun.light_energy = 0.72
    sun.shadow_enabled = true
    sun.shadow_opacity = 0.78
    add_child(sun)

func _build_ground() -> void:
    _box_with_collision(
        "Ground",
        Vector3(0.0, -0.45, 0.0),
        Vector3(50.0, 0.8, 50.0),
        _color("sage", "#6EAD70").darkened(0.04)
    )

    # Village clearing subtly separates the architecture from the forest edge.
    _flat_disc(
        "VillageClearing",
        Vector3(0.0, 0.015, -5.5),
        13.5,
        _color("mint", "#8FD8A2").darkened(0.1),
        Vector3(1.0, 0.05, 0.82)
    )

func _build_creek() -> void:
    var water := MeshInstance3D.new()
    water.name = "Creek"
    var mesh := BoxMesh.new()
    mesh.size = Vector3(26.0, 0.08, 3.4)
    water.mesh = mesh
    water.position = Vector3(0.0, 0.03, 7.0)
    var water_material := _material(_color("aqua", "#69CDD0"), 0.38)
    water_material.metallic = 0.05
    water.material_override = water_material
    add_child(water)

    # Shallow banks make the creek readable without blocking traversal at its ends.
    _flat_disc("BankL", Vector3(-10.5, 0.06, 7.0), 3.4, _color("cream_warm"), Vector3(1.7, 0.05, 0.55))
    _flat_disc("BankR", Vector3(10.5, 0.06, 7.0), 3.4, _color("cream_warm"), Vector3(1.7, 0.05, 0.55))

func _build_paths() -> void:
    # Spawn -> bridge -> village center -> tower. Repeated toy slabs keep the path readable.
    var route: Array[Vector3] = []
    for z in range(19, 7, -2):
        route.append(Vector3(sin(float(z) * 0.32) * 0.8, 0.08, float(z)))
    for z in range(5, -15, -2):
        route.append(Vector3(sin(float(z) * 0.26) * 1.15, 0.08, float(z)))
    for point in route:
        _flat_disc(
            "PathStone",
            point,
            1.15,
            _color("cream_warm", "#E7CE9E"),
            Vector3(1.35, 0.05, 0.78)
        )

    var branch_points := [
        Vector3(-2.0, 0.08, -4.0), Vector3(-4.0, 0.08, -4.0),
        Vector3(-6.0, 0.08, -4.0), Vector3(2.0, 0.08, -7.0),
        Vector3(4.0, 0.08, -9.0), Vector3(5.0, 0.08, -12.0)
    ]
    for point in branch_points:
        _flat_disc(
            "VillagePath",
            point,
            1.0,
            _color("peach", "#F0A66A").lightened(0.1),
            Vector3(1.3, 0.05, 0.75)
        )

func _build_golden_world() -> void:
    if not GoldenAnchorRuntime.has_installed():
        _show_missing_assets()
        return

    var profile_id := String(layout.get("profile_id", "core_candidate_b"))
    for raw_entry in layout.get("anchors", []):
        if typeof(raw_entry) != TYPE_DICTIONARY:
            continue
        var entry: Dictionary = raw_entry
        var anchor_id := String(entry.get("id", ""))
        var pos := _vec3(entry.get("position", [0.0, 0.0, 0.0]))
        var target_height := float(entry.get("height", 2.0))
        var yaw := float(entry.get("yaw", 0.0))
        var instance := GoldenAnchorRuntime.instantiate_anchor(
            self,
            anchor_id,
            pos,
            target_height,
            yaw,
            profile_id
        )
        if instance != null and entry.has("collision"):
            _add_proxy_collider(
                "Collision_" + anchor_id,
                pos,
                yaw,
                entry["collision"]
            )

func _build_boundary() -> void:
    var edge := 25.25
    _invisible_box_collider("BoundaryNorth", Vector3(0.0, 1.5, -edge), Vector3(51.0, 3.0, 0.5))
    _invisible_box_collider("BoundarySouth", Vector3(0.0, 1.5, edge), Vector3(51.0, 3.0, 0.5))
    _invisible_box_collider("BoundaryWest", Vector3(-edge, 1.5, 0.0), Vector3(0.5, 3.0, 51.0))
    _invisible_box_collider("BoundaryEast", Vector3(edge, 1.5, 0.0), Vector3(0.5, 3.0, 51.0))

func _add_proxy_collider(name_value: String, origin: Vector3, yaw: float, spec: Dictionary) -> void:
    var kind := String(spec.get("type", "box"))
    var offset := _vec3(spec.get("offset", [0.0, 0.0, 0.0]))
    var body := StaticBody3D.new()
    body.name = name_value
    body.position = origin + offset
    body.rotation_degrees.y = yaw

    var shape_node := CollisionShape3D.new()
    if kind == "cylinder":
        var shape := CylinderShape3D.new()
        shape.radius = float(spec.get("radius", 0.75))
        shape.height = float(spec.get("height", 2.0))
        shape_node.shape = shape
    else:
        var shape := BoxShape3D.new()
        shape.size = _vec3(spec.get("size", [1.0, 1.0, 1.0]))
        shape_node.shape = shape

    body.add_child(shape_node)
    add_child(body)

func _box_with_collision(name_value: String, pos: Vector3, size: Vector3, color: Color) -> void:
    var node := MeshInstance3D.new()
    node.name = name_value
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.position = pos
    node.material_override = _material(color)
    add_child(node)
    _invisible_box_collider(name_value + "Collision", pos, size)

func _invisible_box_collider(name_value: String, pos: Vector3, size: Vector3) -> void:
    var body := StaticBody3D.new()
    body.name = name_value
    body.position = pos
    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = size
    collision.shape = shape
    body.add_child(collision)
    add_child(body)

func _flat_disc(name_value: String, pos: Vector3, radius: float, color: Color, scale_value: Vector3) -> void:
    var node := MeshInstance3D.new()
    node.name = name_value
    var mesh := CylinderMesh.new()
    mesh.top_radius = radius
    mesh.bottom_radius = radius * 1.02
    mesh.height = 0.09
    mesh.radial_segments = 20
    node.mesh = mesh
    node.position = pos
    node.scale = scale_value
    node.material_override = _material(color)
    add_child(node)

func _build_hud() -> void:
    var hud := CanvasLayer.new()
    add_child(hud)

    var panel := ColorRect.new()
    panel.offset_left = 18.0
    panel.offset_top = 18.0
    panel.offset_right = 520.0
    panel.offset_bottom = 112.0
    panel.color = Color(0.08, 0.07, 0.1, 0.78)
    hud.add_child(panel)

    var title := Label.new()
    title.offset_left = 16.0
    title.offset_top = 10.0
    title.offset_right = 480.0
    title.offset_bottom = 36.0
    title.text = "Mini Utopia · Forest Village 50×50 v0.1"
    panel.add_child(title)

    var help := Label.new()
    help.offset_left = 16.0
    help.offset_top = 42.0
    help.offset_right = 480.0
    help.offset_bottom = 82.0
    help.text = "Golden Forest + Medieval · Candidate B\nWASD / Arrows · Move   Shift · Run   Space · Jump"
    panel.add_child(help)

func _build_world_labels() -> void:
    _label3d("FOREST VILLAGE", Vector3(0.0, 6.8, -7.5), 54)
    _label3d("BRIDGE WALK", Vector3(0.0, 3.2, 7.0), 30)

func _label3d(value: String, position: Vector3, font_size: int) -> void:
    var label := Label3D.new()
    label.text = value
    label.font_size = font_size
    label.modulate = _color("cream_base", "#EEDFC7")
    label.outline_size = 8
    label.outline_modulate = _color("deep_ink", "#403A57")
    label.position = position
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(label)

func _show_missing_assets() -> void:
    _label3d(
        "Golden assets missing\nRun install_golden_anchors.py + bake_golden_palette.py",
        Vector3(0.0, 4.0, 0.0),
        42
    )

func _vec3(value) -> Vector3:
    if typeof(value) == TYPE_ARRAY and value.size() >= 3:
        return Vector3(float(value[0]), float(value[1]), float(value[2]))
    return Vector3.ZERO

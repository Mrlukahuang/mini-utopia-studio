extends Node3D

const LAYOUT_PATH := "res://config/worlds/forest_village_50x50_rich_v0_2.json"
const PALETTE_PATH := "res://config/style/core_palette_candidates_v0_9.json"

var layout: Dictionary = {}
var palette: Dictionary = {}
var ground_profile: Dictionary = {}
var rng := RandomNumberGenerator.new()
var material_cache: Dictionary = {}

func _ready() -> void:
    layout = _load_json(LAYOUT_PATH)
    palette = _load_json(PALETTE_PATH).get("colors", {})
    ground_profile = _load_json(String(layout.get("ground_profile", "")))
    rng.seed = int(ground_profile.get("seed", 50206))

    _setup_environment()
    _build_ground_layers()
    _build_creek()
    _build_paths()
    _build_golden_world()
    _build_ground_dressing()
    _build_boundary()
    _build_hud()
    _build_world_labels()

func _load_json(path: String) -> Dictionary:
    if path.is_empty():
        return {}
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        push_error("Forest Village Rich could not open " + path)
        return {}
    var parsed = JSON.parse_string(file.get_as_text())
    return parsed if typeof(parsed) == TYPE_DICTIONARY else {}

func _color(key: String, fallback: String = "#FF00FF") -> Color:
    return Color(String(palette.get(key, fallback)))

func _material(color: Color, roughness: float = 0.9) -> StandardMaterial3D:
    var cache_key := color.to_html(false) + "_" + str(snappedf(roughness, 0.01))
    if material_cache.has(cache_key):
        return material_cache[cache_key]

    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = roughness
    material_cache[cache_key] = material
    return material

func _setup_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = _color("powder_blue", "#86C7E8").lightened(0.12)
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = _color("cream_warm", "#E7CE9E").lightened(0.08)
    env.ambient_light_energy = 0.27
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.tonemap_exposure = 0.95
    env.fog_enabled = true
    env.fog_light_color = _color("powder_blue", "#86C7E8").lightened(0.18)
    env.fog_light_energy = 0.16
    env.fog_density = 0.004
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-48.0, -34.0, 0.0)
    sun.light_color = _color("cream_warm", "#E7CE9E").lightened(0.18)
    sun.light_energy = 0.68
    sun.shadow_enabled = true
    sun.shadow_opacity = 0.76
    add_child(sun)

    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-22.0, 145.0, 0.0)
    fill.light_color = _color("powder_blue", "#86C7E8")
    fill.light_energy = 0.06
    fill.shadow_enabled = false
    add_child(fill)

func _build_ground_layers() -> void:
    var ground_cfg: Dictionary = ground_profile.get("ground", {})
    var base_color := _color(String(ground_cfg.get("base_color", "sage")), "#6EAD70")
    base_color = base_color.darkened(float(ground_cfg.get("base_darkening", 0.18)))

    _box_with_collision(
        "GroundBase",
        Vector3(0.0, -0.44, 0.0),
        Vector3(50.0, 0.8, 50.0),
        base_color
    )

    var clearing_color := _color(
        String(ground_cfg.get("village_clearing_color", "mint")),
        "#8FD8A2"
    )
    clearing_color = clearing_color.darkened(
        float(ground_cfg.get("village_clearing_darkening", 0.12))
    )
    _flat_patch(
        "VillageClearing",
        Vector3(0.0, 0.015, -6.0),
        14.6,
        clearing_color,
        Vector3(1.0, 0.04, 0.80),
        14
    )

    for raw_patch in ground_cfg.get("patches", []):
        if typeof(raw_patch) != TYPE_DICTIONARY:
            continue
        var patch: Dictionary = raw_patch
        var center2 := _vec2(patch.get("center", [0.0, 0.0]))
        var patch_color := _color(String(patch.get("color", "sage")))
        patch_color = patch_color.lightened(float(patch.get("lighten", 0.0)))
        patch_color = patch_color.darkened(float(patch.get("darken", 0.0)))
        var scale2 := _vec2(patch.get("scale", [1.0, 1.0]))
        _flat_patch(
            "GroundPatch",
            Vector3(center2.x, 0.01, center2.y),
            float(patch.get("radius", 5.0)),
            patch_color,
            Vector3(scale2.x, 0.035, scale2.y),
            12
        )

func _build_creek() -> void:
    var cfg: Dictionary = ground_profile.get("creek", {})
    var water_color := _color(String(cfg.get("color", "aqua")), "#69CDD0")
    var bank_color := _color(String(cfg.get("bank_color", "cream_warm")), "#E7CE9E")
    var bank_stone_color := _color(String(cfg.get("bank_stone_color", "warm_taupe")), "#A7785F")
    var half_length := float(cfg.get("half_length", 13.5))
    var spacing := float(cfg.get("segment_spacing", 1.75))

    var x := -half_length
    var index := 0
    while x <= half_length:
        var z := 7.0 + sin(x * 0.17) * 0.55
        var rot := sin(x * 0.11) * 5.0

        _flat_patch(
            "CreekBank",
            Vector3(x, 0.035, z),
            1.45,
            bank_color,
            Vector3(1.22, 0.035, 0.86),
            12,
            rot
        )

        var water := _flat_patch(
            "CreekWater",
            Vector3(x, 0.07, z),
            1.18,
            water_color,
            Vector3(1.14, 0.028, 0.66),
            14,
            rot
        )
        if water != null:
            var water_material := _material(water_color, 0.30)
            water_material.metallic = 0.04
            water.material_override = water_material

        if index % 2 == 0:
            _small_rock(
                Vector3(x - 0.5, 0.11, z - 1.05),
                rng.randf_range(0.18, 0.34),
                bank_stone_color
            )
            _small_rock(
                Vector3(x + 0.4, 0.11, z + 1.00),
                rng.randf_range(0.16, 0.30),
                bank_stone_color.lightened(0.08)
            )
        x += spacing
        index += 1

func _build_paths() -> void:
    var path_cfg: Dictionary = ground_profile.get("paths", {})
    _build_path_polyline(layout.get("main_path", []), path_cfg, true)

    for raw_branch in layout.get("branch_paths", []):
        if typeof(raw_branch) == TYPE_ARRAY:
            _build_path_polyline(raw_branch, path_cfg, false)

func _build_path_polyline(raw_points: Array, cfg: Dictionary, is_main: bool) -> void:
    if raw_points.size() < 2:
        return

    var points: Array = []
    for raw_point in raw_points:
        var p2 := _vec2(raw_point)
        points.append(Vector3(p2.x, 0.0, p2.y))

    var spacing := float(cfg.get("paver_spacing", 1.15))
    var width := float(cfg.get("stone_width", 2.9))
    if not is_main:
        width *= 0.78

    var stone_keys: Array = cfg.get(
        "stone_colors",
        ["cream_warm", "cream_base", "peach", "warm_taupe"]
    )

    for segment_index in range(points.size() - 1):
        var a: Vector3 = points[segment_index]
        var b: Vector3 = points[segment_index + 1]
        var direction := (b - a)
        var length := direction.length()
        if length < 0.001:
            continue

        var normalized := direction / length
        var perpendicular := Vector3(-normalized.z, 0.0, normalized.x)
        var yaw := rad_to_deg(atan2(normalized.x, normalized.z))
        var steps := maxi(1, int(ceil(length / spacing)))

        for step_index in range(steps):
            var t := float(step_index) / float(steps)
            var center := a.lerp(b, t)

            _flat_patch(
                "PathDirt",
                center + Vector3(0.0, 0.045, 0.0),
                width * 0.60,
                _color(String(cfg.get("dirt_color", "warm_taupe"))).lightened(
                    float(cfg.get("dirt_lighten", 0.20))
                ),
                Vector3(1.15, 0.025, 0.82),
                10,
                yaw + rng.randf_range(-4.0, 4.0)
            )

            var row_offset := width * 0.23
            for side in [-1.0, 1.0]:
                var jitter := perpendicular * (row_offset * side)
                jitter += perpendicular * rng.randf_range(-0.14, 0.14)
                var paver_color := _color(
                    String(stone_keys[rng.randi_range(0, stone_keys.size() - 1)])
                )
                if String(stone_keys[0]) == "cream_warm":
                    paver_color = paver_color.lightened(rng.randf_range(0.0, 0.08))
                _paver(
                    center + jitter + Vector3(0.0, 0.095, 0.0),
                    yaw + rng.randf_range(-9.0, 9.0),
                    paver_color,
                    rng.randf_range(0.72, 0.90),
                    rng.randf_range(0.95, 1.18)
                )

            if is_main and step_index % 3 == 1:
                var center_color := _color(
                    String(stone_keys[rng.randi_range(0, stone_keys.size() - 1)])
                )
                _paver(
                    center + Vector3(
                        rng.randf_range(-0.16, 0.16),
                        0.095,
                        rng.randf_range(-0.12, 0.12)
                    ),
                    yaw + rng.randf_range(-12.0, 12.0),
                    center_color,
                    rng.randf_range(0.62, 0.76),
                    rng.randf_range(0.82, 1.02)
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

func _build_ground_dressing() -> void:
    var dressing_root := Node3D.new()
    dressing_root.name = "GroundDressing"
    add_child(dressing_root)

    var dressing_cfg: Dictionary = ground_profile.get("dressing", {})
    var zones: Dictionary = ground_profile.get("zones", {})

    _scatter_grass(
        dressing_root,
        zones.get("grass", []),
        int(dressing_cfg.get("grass_tufts", 78))
    )
    _scatter_flower_clusters(
        dressing_root,
        zones.get("flowers", []),
        int(dressing_cfg.get("flower_clusters", 22))
    )
    _scatter_pebbles(
        dressing_root,
        zones.get("pebbles", []),
        int(dressing_cfg.get("pebbles", 42))
    )
    _scatter_mushrooms(
        dressing_root,
        zones.get("mushrooms", []),
        int(dressing_cfg.get("mushrooms", 12))
    )

    for raw_garden in ground_profile.get("gardens", []):
        if typeof(raw_garden) == TYPE_DICTIONARY:
            _build_garden(dressing_root, raw_garden)

    _dress_creek_banks(dressing_root)

func _scatter_grass(parent: Node3D, zones: Array, count: int) -> void:
    if zones.is_empty():
        return

    for _i in range(count):
        var zone: Dictionary = zones[rng.randi_range(0, zones.size() - 1)]
        var pos2 := _random_point_in_zone(zone)
        _grass_tuft(
            parent,
            Vector3(pos2.x, 0.14, pos2.y),
            rng.randf_range(0.72, 1.18)
        )

func _scatter_flower_clusters(parent: Node3D, zones: Array, count: int) -> void:
    if zones.is_empty():
        return

    var flower_keys := ["strawberry", "lavender", "butter_yellow", "powder_blue"]
    for _i in range(count):
        var zone: Dictionary = zones[rng.randi_range(0, zones.size() - 1)]
        var center2 := _random_point_in_zone(zone)
        var cluster_count := rng.randi_range(3, 6)
        var flower_key: String = flower_keys[rng.randi_range(0, flower_keys.size() - 1)]
        for _j in range(cluster_count):
            var angle := rng.randf_range(0.0, TAU)
            var radius := rng.randf_range(0.05, 0.72)
            _flower(
                parent,
                Vector3(
                    center2.x + cos(angle) * radius,
                    0.10,
                    center2.y + sin(angle) * radius
                ),
                _color(flower_key),
                rng.randf_range(0.75, 1.12)
            )

func _scatter_pebbles(parent: Node3D, zones: Array, count: int) -> void:
    if zones.is_empty():
        return

    for _i in range(count):
        var zone: Dictionary = zones[rng.randi_range(0, zones.size() - 1)]
        var pos2 := _random_point_in_zone(zone)
        var base := _color("warm_taupe")
        if rng.randf() > 0.5:
            base = _color("cream_warm").darkened(0.10)
        _small_rock(
            Vector3(pos2.x, 0.12, pos2.y),
            rng.randf_range(0.10, 0.28),
            base,
            parent
        )

func _scatter_mushrooms(parent: Node3D, zones: Array, count: int) -> void:
    if zones.is_empty():
        return

    for _i in range(count):
        var zone: Dictionary = zones[rng.randi_range(0, zones.size() - 1)]
        var pos2 := _random_point_in_zone(zone)
        var cap_key := "strawberry" if rng.randf() > 0.35 else "peach"
        _mushroom(
            parent,
            Vector3(pos2.x, 0.08, pos2.y),
            _color(cap_key),
            rng.randf_range(0.75, 1.15)
        )

func _build_garden(parent: Node3D, garden: Dictionary) -> void:
    var center2 := _vec2(garden.get("center", [0.0, 0.0]))
    var radius := float(garden.get("radius", 2.0))
    var flower_color := _color(String(garden.get("flower_color", "strawberry")))

    _flat_patch(
        "GardenSoil",
        Vector3(center2.x, 0.07, center2.y),
        radius,
        _color("warm_taupe").darkened(0.12),
        Vector3(1.0, 0.025, 0.62),
        12,
        rng.randf_range(-25.0, 25.0),
        parent
    )

    var flowers := rng.randi_range(8, 12)
    for _i in range(flowers):
        var angle := rng.randf_range(0.0, TAU)
        var rr := sqrt(rng.randf()) * radius * 0.76
        _flower(
            parent,
            Vector3(
                center2.x + cos(angle) * rr,
                0.10,
                center2.y + sin(angle) * rr * 0.62
            ),
            flower_color,
            rng.randf_range(0.8, 1.1)
        )

    var border_count := 10
    for i in range(border_count):
        var angle := TAU * float(i) / float(border_count)
        _small_rock(
            Vector3(
                center2.x + cos(angle) * radius * 0.92,
                0.10,
                center2.y + sin(angle) * radius * 0.56
            ),
            rng.randf_range(0.12, 0.20),
            _color("cream_warm").darkened(0.05),
            parent
        )

func _dress_creek_banks(parent: Node3D) -> void:
    for x in range(-12, 13, 2):
        var xf := float(x)
        var z := 7.0 + sin(xf * 0.17) * 0.55
        var side := -1.0 if x % 4 == 0 else 1.0
        _grass_tuft(
            parent,
            Vector3(xf + rng.randf_range(-0.3, 0.3), 0.14, z + side * 1.25),
            rng.randf_range(0.72, 1.0)
        )
        if x % 3 == 0:
            _flower(
                parent,
                Vector3(xf + 0.35, 0.10, z - side * 1.18),
                _color("butter_yellow"),
                rng.randf_range(0.75, 1.0)
            )

func _grass_tuft(parent: Node3D, pos: Vector3, scale_value: float) -> void:
    var colors := [_color("mint"), _color("sage"), _color("moss").lightened(0.10)]
    for blade_index in range(3):
        var blade := MeshInstance3D.new()
        blade.name = "GrassBlade"

        var mesh := BoxMesh.new()
        mesh.size = Vector3(0.08, 0.38, 0.10)
        blade.mesh = mesh
        blade.position = pos + Vector3(
            (float(blade_index) - 1.0) * 0.08,
            0.16 * scale_value,
            rng.randf_range(-0.05, 0.05)
        )
        blade.scale = Vector3(
            scale_value,
            scale_value * rng.randf_range(0.82, 1.12),
            scale_value
        )
        blade.rotation_degrees = Vector3(
            rng.randf_range(-8.0, 8.0),
            rng.randf_range(0.0, 180.0),
            rng.randf_range(-18.0, 18.0)
        )
        blade.material_override = _material(
            colors[blade_index % colors.size()],
            0.95
        )
        parent.add_child(blade)

func _flower(parent: Node3D, pos: Vector3, head_color: Color, scale_value: float) -> void:
    var stem := MeshInstance3D.new()
    var stem_mesh := CylinderMesh.new()
    stem_mesh.top_radius = 0.028
    stem_mesh.bottom_radius = 0.035
    stem_mesh.height = 0.34
    stem_mesh.radial_segments = 6
    stem.mesh = stem_mesh
    stem.position = pos + Vector3(0.0, 0.17 * scale_value, 0.0)
    stem.scale = Vector3.ONE * scale_value
    stem.material_override = _material(_color("sage").darkened(0.08), 0.95)
    parent.add_child(stem)

    var head := MeshInstance3D.new()
    var head_mesh := SphereMesh.new()
    head_mesh.radius = 0.105
    head_mesh.height = 0.21
    head_mesh.radial_segments = 8
    head_mesh.rings = 4
    head.mesh = head_mesh
    head.position = pos + Vector3(0.0, 0.37 * scale_value, 0.0)
    head.scale = Vector3(1.0, 0.55, 1.0) * scale_value
    head.material_override = _material(head_color, 0.82)
    parent.add_child(head)

func _mushroom(parent: Node3D, pos: Vector3, cap_color: Color, scale_value: float) -> void:
    var stem := MeshInstance3D.new()
    var stem_mesh := CylinderMesh.new()
    stem_mesh.top_radius = 0.07
    stem_mesh.bottom_radius = 0.10
    stem_mesh.height = 0.34
    stem_mesh.radial_segments = 8
    stem.mesh = stem_mesh
    stem.position = pos + Vector3(0.0, 0.17 * scale_value, 0.0)
    stem.scale = Vector3.ONE * scale_value
    stem.material_override = _material(_color("cream_base"), 0.9)
    parent.add_child(stem)

    var cap := MeshInstance3D.new()
    var cap_mesh := SphereMesh.new()
    cap_mesh.radius = 0.23
    cap_mesh.height = 0.46
    cap_mesh.radial_segments = 10
    cap_mesh.rings = 5
    cap.mesh = cap_mesh
    cap.position = pos + Vector3(0.0, 0.38 * scale_value, 0.0)
    cap.scale = Vector3(1.0, 0.42, 1.0) * scale_value
    cap.material_override = _material(cap_color, 0.84)
    parent.add_child(cap)

func _small_rock(
    pos: Vector3,
    radius: float,
    color: Color,
    parent: Node3D = null
) -> void:
    var rock := MeshInstance3D.new()
    rock.name = "SmallRock"
    var mesh := SphereMesh.new()
    mesh.radius = radius
    mesh.height = radius * 2.0
    mesh.radial_segments = 7
    mesh.rings = 4
    rock.mesh = mesh
    rock.position = pos
    rock.scale = Vector3(
        rng.randf_range(0.85, 1.25),
        rng.randf_range(0.45, 0.72),
        rng.randf_range(0.78, 1.18)
    )
    rock.rotation_degrees.y = rng.randf_range(0.0, 180.0)
    rock.material_override = _material(color, 0.96)
    var target_parent: Node3D = parent if parent != null else self
    target_parent.add_child(rock)

func _paver(
    pos: Vector3,
    yaw: float,
    color: Color,
    width_scale: float,
    length_scale: float
) -> void:
    var node := MeshInstance3D.new()
    node.name = "StonePaver"
    var mesh := CylinderMesh.new()
    mesh.top_radius = 0.56
    mesh.bottom_radius = 0.59
    mesh.height = 0.12
    mesh.radial_segments = 8
    node.mesh = mesh
    node.position = pos
    node.scale = Vector3(width_scale, 0.34, length_scale)
    node.rotation_degrees.y = yaw
    node.material_override = _material(color, 0.93)
    add_child(node)

func _flat_patch(
    name_value: String,
    pos: Vector3,
    radius: float,
    color: Color,
    scale_value: Vector3,
    segments: int,
    yaw: float = 0.0,
    parent: Node3D = null
) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = name_value
    var mesh := CylinderMesh.new()
    mesh.top_radius = radius
    mesh.bottom_radius = radius * 1.01
    mesh.height = 0.07
    mesh.radial_segments = maxi(6, segments)
    node.mesh = mesh
    node.position = pos
    node.scale = scale_value
    node.rotation_degrees.y = yaw
    node.material_override = _material(color, 0.96)
    var target_parent: Node3D = parent if parent != null else self
    target_parent.add_child(node)
    return node

func _random_point_in_zone(zone: Dictionary) -> Vector2:
    var center := _vec2(zone.get("center", [0.0, 0.0]))
    var radius := float(zone.get("radius", 3.0))
    var angle := rng.randf_range(0.0, TAU)
    var rr := sqrt(rng.randf()) * radius
    return center + Vector2(cos(angle), sin(angle)) * rr

func _build_boundary() -> void:
    var edge := 25.25
    _invisible_box_collider(
        "BoundaryNorth",
        Vector3(0.0, 1.5, -edge),
        Vector3(51.0, 3.0, 0.5)
    )
    _invisible_box_collider(
        "BoundarySouth",
        Vector3(0.0, 1.5, edge),
        Vector3(51.0, 3.0, 0.5)
    )
    _invisible_box_collider(
        "BoundaryWest",
        Vector3(-edge, 1.5, 0.0),
        Vector3(0.5, 3.0, 51.0)
    )
    _invisible_box_collider(
        "BoundaryEast",
        Vector3(edge, 1.5, 0.0),
        Vector3(0.5, 3.0, 51.0)
    )

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

func _build_hud() -> void:
    var hud := CanvasLayer.new()
    add_child(hud)

    var panel := ColorRect.new()
    panel.offset_left = 18.0
    panel.offset_top = 18.0
    panel.offset_right = 570.0
    panel.offset_bottom = 120.0
    panel.color = Color(0.08, 0.07, 0.1, 0.78)
    hud.add_child(panel)

    var title := Label.new()
    title.offset_left = 16.0
    title.offset_top = 10.0
    title.offset_right = 535.0
    title.offset_bottom = 38.0
    title.text = "Mini Utopia · Forest Village 50×50 Rich v0.2"
    panel.add_child(title)

    var help := Label.new()
    help.offset_left = 16.0
    help.offset_top = 43.0
    help.offset_right = 535.0
    help.offset_bottom = 90.0
    help.text = "Storybook Meadow + Stone Road + Ground Dressing\nGolden Forest + Medieval · Candidate B\nWASD / Arrows · Move   Shift · Run   Space · Jump"
    panel.add_child(help)

func _build_world_labels() -> void:
    _label3d("FOREST VILLAGE", Vector3(0.0, 6.8, -7.5), 54)
    _label3d("CREEK WALK", Vector3(0.0, 3.2, 7.0), 30)

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

func _vec2(value) -> Vector2:
    if typeof(value) == TYPE_ARRAY and value.size() >= 2:
        return Vector2(float(value[0]), float(value[1]))
    return Vector2.ZERO

func _vec3(value) -> Vector3:
    if typeof(value) == TYPE_ARRAY and value.size() >= 3:
        return Vector3(float(value[0]), float(value[1]), float(value[2]))
    return Vector3.ZERO

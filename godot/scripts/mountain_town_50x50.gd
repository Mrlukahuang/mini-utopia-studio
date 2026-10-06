extends Node3D

const CONFIG_PATH := "res://config/worlds/mountain_town_50x50_v0_3.json"
const PALETTE_PATH := "res://config/style/core_palette_candidates_v0_9.json"
const SQRT3 := 1.7320508075688772

var config: Dictionary = {}
var palette: Dictionary = {}
var road_lookup: Dictionary = {}
var building_cells: Dictionary = {}
var rng := RandomNumberGenerator.new()

var columns: int = 10
var rows: int = 12
var tile_scale: float = 2.3
var hex_x: float = 4.6
var hex_z: float = 3.983716857408418
var origin_x: float = 21.85
var origin_z: float = 21.9104427157463


func _ready() -> void:
    config = _load_json(CONFIG_PATH)
    palette = _load_json(PALETTE_PATH).get("colors", {})

    var grid: Dictionary = config.get("grid", {})
    columns = int(grid.get("columns", 10))
    rows = int(grid.get("rows", 12))
    tile_scale = float(grid.get("tile_scale", 2.3))
    hex_x = 2.0 * tile_scale
    hex_z = SQRT3 * tile_scale
    origin_x = ((float(columns - 1) + 0.5) * hex_x) * 0.5
    origin_z = (float(rows - 1) * hex_z) * 0.5

    rng.seed = 50310
    _build_lookup_tables()
    _setup_environment()
    _build_hex_world()
    _build_bridge()
    _build_mountain_ring()
    _build_buildings()
    _build_resource_yards()
    _build_forest_dressing()
    _build_fences()
    _build_boundary()
    _place_player()
    _build_hud()


func _load_json(path: String) -> Dictionary:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        push_error("Mountain Town could not open " + path)
        return {}
    var parsed = JSON.parse_string(file.get_as_text())
    return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


func _color(key: String, fallback: String = "#FFFFFF") -> Color:
    return Color(String(palette.get(key, fallback)))


func _build_lookup_tables() -> void:
    road_lookup.clear()
    building_cells.clear()

    for raw_entry in config.get("road_cells", []):
        if typeof(raw_entry) != TYPE_DICTIONARY:
            continue
        var entry: Dictionary = raw_entry
        road_lookup[_cell_key(int(entry.get("c", 0)), int(entry.get("r", 0)))] = entry

    for raw_building in config.get("buildings", []):
        if typeof(raw_building) != TYPE_DICTIONARY:
            continue
        var building: Dictionary = raw_building
        building_cells[_cell_key(int(building.get("c", 0)), int(building.get("r", 0)))] = true


func _setup_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = _color("powder_blue", "#86C7E8").darkened(0.10)
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = _color("cream_warm", "#E7CE9E").lightened(0.04)
    env.ambient_light_energy = 0.26
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.tonemap_exposure = 0.92
    env.fog_enabled = true
    env.fog_light_color = _color("powder_blue", "#86C7E8").lightened(0.08)
    env.fog_light_energy = 0.16
    env.fog_density = 0.006
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-48.0, -35.0, 0.0)
    sun.light_color = _color("cream_warm", "#E7CE9E").lightened(0.16)
    sun.light_energy = 0.68
    sun.shadow_enabled = true
    sun.shadow_opacity = 0.76
    add_child(sun)

    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-20.0, 145.0, 0.0)
    fill.light_color = _color("powder_blue", "#86C7E8")
    fill.light_energy = 0.05
    fill.shadow_enabled = false
    add_child(fill)


func _build_hex_world() -> void:
    if not WorldKitRuntime.has_installed():
        _show_missing_assets()
        return

    var river_cfg: Dictionary = config.get("river", {})
    var river_row: int = int(river_cfg.get("row", 9))
    var crossing_col: int = int(river_cfg.get("crossing_col", 4))
    var profile_id := String(config.get("profile_id", "core_candidate_b"))

    for r in range(rows):
        for c in range(columns):
            var key := _cell_key(c, r)
            var level := _terrain_level(c, r)
            var top_y := float(level) * tile_scale
            var position := _hex_position(c, r, top_y)
            var asset_id := "med_hex_grass"
            var yaw := 0.0
            var is_river := r == river_row
            var is_slope := false

            if is_river:
                if c == crossing_col:
                    asset_id = "med_hex_river_crossing_A"
                elif c % 3 == 1:
                    asset_id = "med_hex_river_A_curvy"
                else:
                    asset_id = "med_hex_river_A"
            elif road_lookup.has(key):
                var road: Dictionary = road_lookup[key]
                asset_id = String(road.get("id", "med_hex_road_A"))
                yaw = float(road.get("yaw", 0.0))
                is_slope = bool(road.get("slope", false))
                if road.has("level"):
                    level = int(road.get("level", level))
                    top_y = float(level) * tile_scale
                    position = _hex_position(c, r, top_y)

            WorldKitRuntime.instantiate_asset(
                self,
                asset_id,
                position,
                yaw,
                tile_scale,
                0.0,
                profile_id
            )

            if is_river:
                _add_riverbed_collider(position)
            elif is_slope:
                _add_hill_access_ramp(c, r)
            else:
                _add_tile_collider(position, level)


func _terrain_level(c: int, r: int) -> int:
    if r <= 1:
        return 1
    if r == 2 and (c <= 2 or c >= 6):
        return 1
    if c == 0 and r <= 7:
        return 1
    if c == 9 and r <= 7:
        return 1
    return 0


func _hex_position(c: int, r: int, y: float = 0.0) -> Vector3:
    var offset := 0.5 if (r % 2) == 1 else 0.0
    var x := (float(c) + offset) * hex_x - origin_x
    var z := float(r) * hex_z - origin_z
    return Vector3(x, y, z)


func _build_bridge() -> void:
    var river_cfg: Dictionary = config.get("river", {})
    var c := int(river_cfg.get("crossing_col", 4))
    var r := int(river_cfg.get("row", 9))
    var position := _hex_position(c, r, 0.0)

    WorldKitRuntime.instantiate_asset(
        self,
        "med_building_bridge_A",
        position,
        0.0,
        1.0,
        2.6,
        String(config.get("profile_id", "core_candidate_b"))
    )

    _add_box_collider(
        "BridgeCollision",
        position + Vector3(0.0, 0.15, 0.0),
        Vector3(3.4, 0.45, 5.0),
        Vector3.ZERO
    )


func _build_mountain_ring() -> void:
    var profile_id := String(config.get("profile_id", "core_candidate_b"))
    for raw_entry in config.get("mountains", []):
        if typeof(raw_entry) != TYPE_DICTIONARY:
            continue
        var entry: Dictionary = raw_entry
        var c := int(entry.get("c", 0))
        var r := int(entry.get("r", 0))
        var level := _terrain_level(c, r)
        var position := _hex_position(c, r, float(level) * tile_scale)

        WorldKitRuntime.instantiate_asset(
            self,
            String(entry.get("id", "")),
            position,
            float(entry.get("yaw", 0.0)),
            1.0,
            float(entry.get("height", 7.0)),
            profile_id
        )


func _build_buildings() -> void:
    var profile_id := String(config.get("profile_id", "core_candidate_b"))

    for raw_entry in config.get("buildings", []):
        if typeof(raw_entry) != TYPE_DICTIONARY:
            continue
        var entry: Dictionary = raw_entry
        var c := int(entry.get("c", 0))
        var r := int(entry.get("r", 0))
        var level := int(entry.get("level", _terrain_level(c, r)))
        var ground_y := float(level) * tile_scale
        var position := _hex_position(c, r, ground_y)
        var target_height := float(entry.get("height", 4.5))

        WorldKitRuntime.instantiate_asset(
            self,
            String(entry.get("id", "")),
            position,
            float(entry.get("yaw", 0.0)),
            1.0,
            target_height,
            profile_id
        )

        var radius := 1.25
        if target_height >= 5.8:
            radius = 1.55
        _add_cylinder_collider(
            "BuildingCollision",
            position + Vector3(0.0, minf(target_height * 0.34, 2.0), 0.0),
            radius,
            minf(target_height * 0.68, 4.0)
        )


func _build_resource_yards() -> void:
    for raw_entry in config.get("resources", []):
        if typeof(raw_entry) != TYPE_DICTIONARY:
            continue
        var entry: Dictionary = raw_entry
        var c := int(entry.get("c", 0))
        var r := int(entry.get("r", 0))
        var level := _terrain_level(c, r)
        var offset := _vec3(entry.get("offset", [0.0, 0.0, 0.0]))
        var position := _hex_position(c, r, float(level) * tile_scale) + offset

        WorldKitRuntime.instantiate_asset(
            self,
            String(entry.get("id", "")),
            position,
            rng.randf_range(-25.0, 25.0),
            float(entry.get("scale", 1.0)),
            0.0,
            ""
        )


func _build_forest_dressing() -> void:
    if not WorldKitRuntime.has_installed():
        return

    var grass_ids := [
        "forest_grass_1_a_color1",
        "forest_grass_1_b_color1",
        "forest_grass_1_c_color1",
        "forest_grass_1_d_color1",
        "forest_grass_2_a_color1",
        "forest_grass_2_b_color1",
        "forest_grass_2_c_color1",
        "forest_grass_2_d_color1"
    ]
    var bush_ids := [
        "forest_bush_1_b_color1",
        "forest_bush_2_d_color1",
        "forest_bush_3_a_color1"
    ]
    var rock_ids := [
        "forest_rock_1_c_color1",
        "forest_rock_2_f_color1",
        "forest_rock_3_k_color1"
    ]
    var tree_ids := [
        "forest_tree_1_b_color1",
        "forest_tree_3_a_color1",
        "forest_tree_4_b_color1"
    ]
    var profile_id := String(config.get("profile_id", "core_candidate_b"))
    var river_cfg: Dictionary = config.get("river", {})
    var river_row := int(river_cfg.get("row", 9))

    for r in range(rows):
        for c in range(columns):
            var key := _cell_key(c, r)
            if r == river_row or road_lookup.has(key) or building_cells.has(key):
                continue

            var level := _terrain_level(c, r)
            var center := _hex_position(c, r, float(level) * tile_scale)

            var grass_count := rng.randi_range(1, 3)
            for _i in range(grass_count):
                var grass_id: String = grass_ids[rng.randi_range(0, grass_ids.size() - 1)]
                WorldKitRuntime.instantiate_asset(
                    self,
                    grass_id,
                    center + _random_flat_offset(1.45) + Vector3(0.0, 0.03, 0.0),
                    rng.randf_range(0.0, 360.0),
                    rng.randf_range(0.48, 0.72),
                    0.0,
                    profile_id
                )

            var edge_factor := 0.0
            if c <= 1 or c >= columns - 2 or r <= 2:
                edge_factor = 1.0

            if rng.randf() < 0.26 + edge_factor * 0.16:
                var bush_id: String = bush_ids[rng.randi_range(0, bush_ids.size() - 1)]
                WorldKitRuntime.instantiate_asset(
                    self,
                    bush_id,
                    center + _random_flat_offset(1.2),
                    rng.randf_range(0.0, 360.0),
                    rng.randf_range(0.46, 0.66),
                    0.0,
                    profile_id
                )

            if rng.randf() < 0.22:
                var rock_id: String = rock_ids[rng.randi_range(0, rock_ids.size() - 1)]
                WorldKitRuntime.instantiate_asset(
                    self,
                    rock_id,
                    center + _random_flat_offset(1.2),
                    rng.randf_range(0.0, 360.0),
                    rng.randf_range(0.16, 0.24),
                    0.0,
                    profile_id
                )

            if edge_factor > 0.5 and rng.randf() < 0.42:
                var tree_id: String = tree_ids[rng.randi_range(0, tree_ids.size() - 1)]
                WorldKitRuntime.instantiate_asset(
                    self,
                    tree_id,
                    center + _random_flat_offset(0.9),
                    rng.randf_range(0.0, 360.0),
                    rng.randf_range(1.15, 1.55),
                    0.0,
                    profile_id
                )

            if rng.randf() < 0.12:
                _add_flower_cluster(
                    center + _random_flat_offset(1.1) + Vector3(0.0, 0.04, 0.0)
                )


func _build_fences() -> void:
    var profile_id := String(config.get("profile_id", "core_candidate_b"))
    var fence_cells: Array[Vector2i] = [
        Vector2i(1, 4), Vector2i(1, 5), Vector2i(7, 3),
        Vector2i(8, 4), Vector2i(2, 7), Vector2i(6, 8)
    ]

    for cell: Vector2i in fence_cells:
        var level := _terrain_level(cell.x, cell.y)
        var center := _hex_position(cell.x, cell.y, float(level) * tile_scale)
        WorldKitRuntime.instantiate_asset(
            self,
            "med_fence_wood_straight",
            center + Vector3(0.0, 0.0, 1.65),
            0.0,
            2.1,
            0.0,
            profile_id
        )


func _add_flower_cluster(center: Vector3) -> void:
    var flower_colors := [
        _color("strawberry"),
        _color("lavender"),
        _color("butter_yellow"),
        _color("powder_blue")
    ]
    var flower_color: Color = flower_colors[rng.randi_range(0, flower_colors.size() - 1)]

    for _i in range(rng.randi_range(3, 6)):
        var offset := _random_flat_offset(0.55)
        var stem := MeshInstance3D.new()
        var stem_mesh := CylinderMesh.new()
        stem_mesh.top_radius = 0.018
        stem_mesh.bottom_radius = 0.026
        stem_mesh.height = 0.24
        stem_mesh.radial_segments = 5
        stem.mesh = stem_mesh
        stem.position = center + offset + Vector3(0.0, 0.12, 0.0)
        stem.material_override = _simple_material(_color("sage").darkened(0.12))
        add_child(stem)

        var head := MeshInstance3D.new()
        var head_mesh := SphereMesh.new()
        head_mesh.radius = 0.075
        head_mesh.height = 0.15
        head_mesh.radial_segments = 7
        head_mesh.rings = 4
        head.mesh = head_mesh
        head.position = center + offset + Vector3(0.0, 0.27, 0.0)
        head.scale = Vector3(1.0, 0.55, 1.0)
        head.material_override = _simple_material(flower_color)
        add_child(head)


func _simple_material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.92
    return material


func _add_tile_collider(position: Vector3, level: int) -> void:
    if level <= 0:
        _add_box_collider(
            "TileCollision",
            position + Vector3(0.0, -0.35, 0.0),
            Vector3(hex_x * 0.96, 0.7, 2.18 * tile_scale),
            Vector3.ZERO
        )
    else:
        _add_box_collider(
            "RaisedTileCollision",
            Vector3(position.x, position.y * 0.5, position.z),
            Vector3(hex_x * 0.96, position.y, 2.18 * tile_scale),
            Vector3.ZERO
        )


func _add_riverbed_collider(position: Vector3) -> void:
    _add_box_collider(
        "Riverbed",
        position + Vector3(0.0, -0.82, 0.0),
        Vector3(hex_x * 0.96, 0.35, 2.18 * tile_scale),
        Vector3.ZERO
    )


func _add_hill_access_ramp(c: int, r: int) -> void:
    var low := _hex_position(c, r + 1, 0.0)
    var high := _hex_position(c, r, tile_scale)
    var delta := high - low
    var horizontal := Vector3(delta.x, 0.0, delta.z)
    var horizontal_length := horizontal.length()
    if horizontal_length < 0.001:
        return

    var length := sqrt(horizontal_length * horizontal_length + tile_scale * tile_scale)
    var midpoint := (low + high) * 0.5 + Vector3(0.0, 0.10, 0.0)
    var yaw := rad_to_deg(atan2(horizontal.x, horizontal.z))
    var pitch := -rad_to_deg(atan2(tile_scale, horizontal_length))

    _add_box_collider(
        "HillAccessRamp",
        midpoint,
        Vector3(2.8, 0.45, length),
        Vector3(pitch, yaw, 0.0)
    )


func _add_box_collider(
    name_value: String,
    position: Vector3,
    size: Vector3,
    rotation_degrees: Vector3
) -> void:
    var body := StaticBody3D.new()
    body.name = name_value
    body.position = position
    body.rotation_degrees = rotation_degrees

    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = size
    collision.shape = shape
    body.add_child(collision)
    add_child(body)


func _add_cylinder_collider(
    name_value: String,
    position: Vector3,
    radius: float,
    height: float
) -> void:
    var body := StaticBody3D.new()
    body.name = name_value
    body.position = position

    var collision := CollisionShape3D.new()
    var shape := CylinderShape3D.new()
    shape.radius = radius
    shape.height = height
    collision.shape = shape
    body.add_child(collision)
    add_child(body)


func _build_boundary() -> void:
    var half := 25.5
    _add_box_collider("NorthBoundary", Vector3(0.0, 2.0, -half), Vector3(52.0, 4.0, 0.5), Vector3.ZERO)
    _add_box_collider("SouthBoundary", Vector3(0.0, 2.0, half), Vector3(52.0, 4.0, 0.5), Vector3.ZERO)
    _add_box_collider("WestBoundary", Vector3(-half, 2.0, 0.0), Vector3(0.5, 4.0, 52.0), Vector3.ZERO)
    _add_box_collider("EastBoundary", Vector3(half, 2.0, 0.0), Vector3(0.5, 4.0, 52.0), Vector3.ZERO)


func _place_player() -> void:
    var player := get_node_or_null("Player") as Node3D
    if player == null:
        return

    var spawn: Dictionary = config.get("spawn", {})
    var c := int(spawn.get("col", 4))
    var r := int(spawn.get("row", 11))
    player.position = _hex_position(c, r, float(spawn.get("y", 0.8)))


func _build_hud() -> void:
    var hud := CanvasLayer.new()
    add_child(hud)

    var panel := ColorRect.new()
    panel.offset_left = 18.0
    panel.offset_top = 18.0
    panel.offset_right = 600.0
    panel.offset_bottom = 128.0
    panel.color = Color(0.08, 0.07, 0.1, 0.78)
    hud.add_child(panel)

    var title := Label.new()
    title.offset_left = 16.0
    title.offset_top = 10.0
    title.offset_right = 560.0
    title.offset_bottom = 38.0
    title.text = "Mini Utopia · Mountain Town 50×50 v0.3"
    panel.add_child(title)

    var info := Label.new()
    info.offset_left = 16.0
    info.offset_top = 42.0
    info.offset_right = 560.0
    info.offset_bottom = 100.0
    info.text = "REAL KayKit Hex Terrain + Roads + River + Mountain Ring\n30-building town · Forest Nature dressing · Resource Bits\nWASD / Arrows · Move   Shift · Run   Space · Jump"
    panel.add_child(info)


func _show_missing_assets() -> void:
    var label := Label3D.new()
    label.text = "Mountain Town assets missing\nRun: python3 tools/prepare_mountain_town_assets.py"
    label.font_size = 44
    label.modulate = _color("cream_base")
    label.outline_size = 10
    label.outline_modulate = _color("deep_ink")
    label.position = Vector3(0.0, 4.0, 0.0)
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(label)


func _random_flat_offset(radius: float) -> Vector3:
    var angle := rng.randf_range(0.0, TAU)
    var distance := sqrt(rng.randf()) * radius
    return Vector3(cos(angle) * distance, 0.0, sin(angle) * distance)


func _cell_key(c: int, r: int) -> String:
    return str(c) + ":" + str(r)


func _vec3(value) -> Vector3:
    if typeof(value) == TYPE_ARRAY and value.size() >= 3:
        return Vector3(float(value[0]), float(value[1]), float(value[2]))
    return Vector3.ZERO

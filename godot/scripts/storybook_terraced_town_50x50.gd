extends Node3D

const CONFIG_PATH := "res://config/worlds/storybook_terraced_town_50x50_v0_5.json"
const PALETTE_PATH := "res://config/style/core_palette_candidates_v0_9.json"
const SQRT3: float = 1.7320508075688772

var config: Dictionary = {}
var palette: Dictionary = {}

var columns: int = 10
var rows: int = 12
var tile_scale: float = 2.1
var terrace_step: float = 2.1
var hex_x: float = 4.2
var hex_z: float = 3.6373066958946425
var origin_x: float = 19.95
var origin_z: float = 20.005186827420532

var road_cells: Dictionary = {}
var road_connections: Dictionary = {}
var slope_cells: Dictionary = {}
var building_cells: Dictionary = {}
var road_world_positions: Array[Vector3] = []

var rng := RandomNumberGenerator.new()


func _ready() -> void:
    config = _load_json(CONFIG_PATH)
    palette = _load_json(PALETTE_PATH).get("colors", {})

    var grid: Dictionary = config.get("grid", {})
    columns = int(grid.get("columns", 10))
    rows = int(grid.get("rows", 12))
    tile_scale = float(grid.get("tile_scale", 2.1))

    var terrain_cfg: Dictionary = config.get("terrain", {})
    terrace_step = float(terrain_cfg.get("terrace_step", tile_scale))

    hex_x = 2.0 * tile_scale
    hex_z = SQRT3 * tile_scale
    origin_x = ((float(columns - 1) + 0.5) * hex_x) * 0.5
    origin_z = (float(rows - 1) * hex_z) * 0.5

    rng.seed = 50512
    _build_lookup_tables()
    _setup_environment()
    _build_hex_world()
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
        push_error("Green Mountain Town could not open " + path)
        return {}

    var parsed = JSON.parse_string(file.get_as_text())
    return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


func _color(key: String, fallback: String = "#FFFFFF") -> Color:
    return Color(String(palette.get(key, fallback)))


func _build_lookup_tables() -> void:
    road_cells.clear()
    road_connections.clear()
    slope_cells.clear()
    building_cells.clear()
    road_world_positions.clear()

    _register_road_path(config.get("main_road", []))

    for raw_path in config.get("side_roads", []):
        if typeof(raw_path) == TYPE_ARRAY:
            _register_road_path(raw_path)

    for raw_cell in config.get("slope_cells", []):
        if typeof(raw_cell) == TYPE_ARRAY and raw_cell.size() >= 2:
            var cell := Vector2i(int(raw_cell[0]), int(raw_cell[1]))
            slope_cells[_cell_key(cell.x, cell.y)] = true

    for raw_building in config.get("buildings", []):
        if typeof(raw_building) != TYPE_DICTIONARY:
            continue
        var building: Dictionary = raw_building
        building_cells[
            _cell_key(int(building.get("c", 0)), int(building.get("r", 0)))
        ] = true

    for key in road_cells.keys():
        var cell: Vector2i = road_cells[key]
        var level := _terrain_level(cell.x, cell.y)
        road_world_positions.append(
            _hex_position(cell.x, cell.y, float(level) * terrace_step)
        )


func _register_road_path(raw_path: Array) -> void:
    var cells: Array[Vector2i] = []

    for raw_cell in raw_path:
        if typeof(raw_cell) != TYPE_ARRAY or raw_cell.size() < 2:
            continue
        var cell := Vector2i(int(raw_cell[0]), int(raw_cell[1]))
        cells.append(cell)
        road_cells[_cell_key(cell.x, cell.y)] = cell

    for index in range(cells.size() - 1):
        _connect_road_cells(cells[index], cells[index + 1])


func _connect_road_cells(a: Vector2i, b: Vector2i) -> void:
    var dir_ab := _direction_between(a, b)
    var dir_ba := _direction_between(b, a)

    if dir_ab < 0 or dir_ba < 0:
        push_warning("Non-adjacent road cells: " + str(a) + " -> " + str(b))
        return

    _append_connection(a, dir_ab)
    _append_connection(b, dir_ba)


func _append_connection(cell: Vector2i, direction: int) -> void:
    var key := _cell_key(cell.x, cell.y)
    var values: Array = road_connections.get(key, [])
    if not values.has(direction):
        values.append(direction)
    road_connections[key] = values


func _direction_between(a: Vector2i, b: Vector2i) -> int:
    for direction in range(6):
        if _neighbor_for_direction(a, direction) == b:
            return direction
    return -1


func _neighbor_for_direction(cell: Vector2i, direction: int) -> Vector2i:
    var even_row := (cell.y % 2) == 0

    if even_row:
        var offsets_even: Array[Vector2i] = [
            Vector2i(1, 0),
            Vector2i(0, 1),
            Vector2i(-1, 1),
            Vector2i(-1, 0),
            Vector2i(-1, -1),
            Vector2i(0, -1),
        ]
        return cell + offsets_even[direction]

    var offsets_odd: Array[Vector2i] = [
        Vector2i(1, 0),
        Vector2i(1, 1),
        Vector2i(0, 1),
        Vector2i(-1, 0),
        Vector2i(0, -1),
        Vector2i(1, -1),
    ]
    return cell + offsets_odd[direction]


func _setup_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = _color("powder_blue", "#86C7E8").darkened(0.14)
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = _color("cream_warm", "#E7CE9E").lightened(0.03)
    env.ambient_light_energy = 0.25
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.tonemap_exposure = 0.90
    env.fog_enabled = true
    env.fog_light_color = _color("powder_blue", "#86C7E8").lightened(0.07)
    env.fog_light_energy = 0.14
    env.fog_density = 0.005
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-50.0, -34.0, 0.0)
    sun.light_color = _color("cream_warm", "#E7CE9E").lightened(0.15)
    sun.light_energy = 0.66
    sun.shadow_enabled = true
    sun.shadow_opacity = 0.74
    add_child(sun)

    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-22.0, 145.0, 0.0)
    fill.light_color = _color("powder_blue", "#86C7E8")
    fill.light_energy = 0.05
    fill.shadow_enabled = false
    add_child(fill)


func _build_hex_world() -> void:
    if not WorldKitRuntime.has_installed():
        _show_missing_assets()
        return

    var river_cfg: Dictionary = config.get("river", {})
    var river_row := int(river_cfg.get("row", 9))
    var crossing_cols: Array[int] = []
    for raw_col in river_cfg.get("crossing_cols", []):
        crossing_cols.append(int(raw_col))
    var terrain_profile := String(
        config.get("terrain_profile_id", "core_candidate_b_green_terrain")
    )

    for r in range(rows):
        for c in range(columns):
            var level := _terrain_level(c, r)
            _build_terrain_stack(c, r, level, terrain_profile)

            var position := _hex_position(
                c,
                r,
                float(level) * terrace_step
            )
            var key := _cell_key(c, r)

            if r == river_row:
                if crossing_cols.has(c) and road_cells.has(key):
                    var road_shape := _road_shape_for(c, r)
                    WorldKitRuntime.instantiate_asset(
                        self,
                        "med_hex_river_crossing_A",
                        position,
                        float(road_shape.get("yaw", 0.0)),
                        tile_scale,
                        0.0,
                        terrain_profile
                    )
                    _add_tile_collider(position, level)
                else:
                    var river_asset := "med_hex_river_A"
                    if c % 3 == 1:
                        river_asset = "med_hex_river_A_curvy"
                    elif c % 3 == 2:
                        river_asset = "med_hex_river_B"

                    WorldKitRuntime.instantiate_asset(
                        self,
                        river_asset,
                        position,
                        0.0,
                        tile_scale,
                        0.0,
                        terrain_profile
                    )
                    _add_riverbed_collider(position)
                continue

            if road_cells.has(key):
                var shape := _road_shape_for(c, r)
                WorldKitRuntime.instantiate_asset(
                    self,
                    String(shape.get("id", "med_hex_road_A")),
                    position,
                    float(shape.get("yaw", 0.0)),
                    tile_scale,
                    0.0,
                    terrain_profile
                )

                if slope_cells.has(key):
                    _add_slope_collider(c, r)
                else:
                    _add_tile_collider(position, level)
                continue

            WorldKitRuntime.instantiate_asset(
                self,
                "med_hex_grass",
                position,
                0.0,
                tile_scale,
                0.0,
                terrain_profile
            )
            _add_tile_collider(position, level)


func _build_terrain_stack(
    c: int,
    r: int,
    level: int,
    terrain_profile: String
) -> void:
    if level <= 0:
        return

    for stack_index in range(level):
        var support_position := _hex_position(
            c,
            r,
            float(stack_index) * terrace_step
        )
        WorldKitRuntime.instantiate_asset(
            self,
            "med_hex_grass_bottom",
            support_position,
            0.0,
            tile_scale,
            0.0,
            terrain_profile
        )


func _road_shape_for(c: int, r: int) -> Dictionary:
    var key := _cell_key(c, r)
    var raw_connections: Array = road_connections.get(key, [])
    var connections: Array[int] = []

    for value in raw_connections:
        connections.append(int(value))

    if connections.is_empty():
        return {"id": "med_hex_road_A", "yaw": 0.0}

    if slope_cells.has(key):
        return {
            "id": "med_hex_road_A_sloped_high",
            "yaw": _best_yaw_for_connections(connections),
        }

    if connections.size() == 1:
        var dead_rotation := _rotation_for_shape([3], connections)
        return {
            "id": "med_hex_road_M",
            "yaw": float(dead_rotation * 60),
        }

    if connections.size() == 2:
        var a := connections[0]
        var b := connections[1]
        var diff := absi(a - b)
        var cyclic_diff := mini(diff, 6 - diff)

        if cyclic_diff == 3:
            var straight_rotation := _rotation_for_shape([0, 3], connections)
            return {
                "id": "med_hex_road_A",
                "yaw": float(straight_rotation * 60),
            }

        if cyclic_diff == 2:
            var wide_curve_rotation := _rotation_for_shape([3, 1], connections)
            return {
                "id": "med_hex_road_B",
                "yaw": float(wide_curve_rotation * 60),
            }

        var tight_curve_rotation := _rotation_for_shape([3, 2], connections)
        return {
            "id": "med_hex_road_C",
            "yaw": float(tight_curve_rotation * 60),
        }

    # Junctions deliberately become fully paved hex plazas. This keeps every
    # branch readable and avoids broken connections at the town center.
    return {"id": "med_hex_road_L", "yaw": 0.0}


func _best_yaw_for_connections(connections: Array[int]) -> float:
    if connections.size() >= 2:
        var straight_rotation := _rotation_for_shape([0, 3], connections)
        if straight_rotation >= 0:
            return float(straight_rotation * 60)

        var wide_rotation := _rotation_for_shape([3, 1], connections)
        if wide_rotation >= 0:
            return float(wide_rotation * 60)

        var tight_rotation := _rotation_for_shape([3, 2], connections)
        if tight_rotation >= 0:
            return float(tight_rotation * 60)

    if connections.size() == 1:
        var dead_rotation := _rotation_for_shape([3], connections)
        if dead_rotation >= 0:
            return float(dead_rotation * 60)

    return 0.0


func _rotation_for_shape(base: Array, target: Array) -> int:
    var target_sorted: Array = target.duplicate()
    target_sorted.sort()

    for rotation in range(6):
        var rotated: Array = []
        for direction in base:
            rotated.append((direction + rotation) % 6)
        rotated.sort()

        if rotated == target_sorted:
            return rotation

    return 0


func _terrain_level(c: int, r: int) -> int:
    var river_cfg: Dictionary = config.get("river", {})
    if r == int(river_cfg.get("row", 9)):
        return 0

    # Broad readable valley / town floor.
    if c >= 2 and c <= 7 and r >= 2 and r <= 9:
        return 0

    # First green terrace wraps the town on all four sides.
    if (
        (c == 1 or c == 8) and r >= 1 and r <= 10
    ):
        return 1
    if r == 1 and c >= 2 and c <= 7:
        return 1
    if r == 10 and c >= 2 and c <= 7:
        return 1

    # Outermost ring is the high mountain shelf, matching the layered
    # KayKit modular-terrain reference rather than a flat hex field.
    return 2


func _hex_position(c: int, r: int, y: float = 0.0) -> Vector3:
    var row_offset := 0.5 if (r % 2) == 1 else 0.0
    var x := (float(c) + row_offset) * hex_x - origin_x
    var z := float(r) * hex_z - origin_z
    return Vector3(x, y, z)


func _build_mountain_ring() -> void:
    var terrain_profile := String(
        config.get("terrain_profile_id", "core_candidate_b_green_terrain")
    )

    for raw_entry in config.get("mountains", []):
        if typeof(raw_entry) != TYPE_DICTIONARY:
            continue

        var entry: Dictionary = raw_entry
        var c := int(entry.get("c", 0))
        var r := int(entry.get("r", 0))
        var level := _terrain_level(c, r)
        var position := _hex_position(
            c,
            r,
            float(level) * terrace_step
        )

        WorldKitRuntime.instantiate_asset(
            self,
            String(entry.get("id", "")),
            position,
            float(entry.get("yaw", 0.0)),
            1.0,
            float(entry.get("height", 6.0)),
            terrain_profile
        )


func _build_buildings() -> void:
    var building_profile := String(
        config.get("building_profile_id", "core_candidate_b")
    )
    var front_offset := float(
        config.get("building_front_offset_degrees", 180.0)
    )

    for raw_entry in config.get("buildings", []):
        if typeof(raw_entry) != TYPE_DICTIONARY:
            continue

        var entry: Dictionary = raw_entry
        var c := int(entry.get("c", 0))
        var r := int(entry.get("r", 0))
        var level := _terrain_level(c, r)
        var position := _hex_position(
            c,
            r,
            float(level) * terrace_step
        )
        var target_height := float(entry.get("height", 3.6))
        var yaw := float(entry.get("yaw", 0.0))

        if bool(entry.get("face_road", false)):
            yaw = _yaw_toward_nearest_road(position) + front_offset

        WorldKitRuntime.instantiate_asset(
            self,
            String(entry.get("id", "")),
            position,
            yaw,
            1.0,
            target_height,
            building_profile
        )

        var radius := 1.05
        if target_height >= 4.3:
            radius = 1.28
        if target_height >= 5.2:
            radius = 1.42

        _add_cylinder_collider(
            "BuildingCollision",
            position + Vector3(
                0.0,
                minf(target_height * 0.32, 1.7),
                0.0
            ),
            radius,
            minf(target_height * 0.64, 3.4)
        )


func _yaw_toward_nearest_road(position: Vector3) -> float:
    if road_world_positions.is_empty():
        return 0.0

    var best_position := road_world_positions[0]
    var best_distance := position.distance_squared_to(best_position)

    for road_position in road_world_positions:
        var distance := position.distance_squared_to(road_position)
        if distance < best_distance:
            best_distance = distance
            best_position = road_position

    var direction := best_position - position
    direction.y = 0.0

    if direction.length_squared() < 0.0001:
        return 0.0

    return rad_to_deg(atan2(direction.x, direction.z))


func _build_resource_yards() -> void:
    for raw_entry in config.get("resources", []):
        if typeof(raw_entry) != TYPE_DICTIONARY:
            continue

        var entry: Dictionary = raw_entry
        var c := int(entry.get("c", 0))
        var r := int(entry.get("r", 0))
        var level := _terrain_level(c, r)
        var offset := _vec3(entry.get("offset", [0.0, 0.0, 0.0]))
        var position := _hex_position(
            c,
            r,
            float(level) * terrace_step
        ) + offset

        WorldKitRuntime.instantiate_asset(
            self,
            String(entry.get("id", "")),
            position,
            rng.randf_range(-22.0, 22.0),
            float(entry.get("scale", 0.8)),
            0.0,
            ""
        )


func _build_forest_dressing() -> void:
    if not WorldKitRuntime.has_installed():
        return

    var forest_profile := String(config.get("forest_profile_id", ""))

    var grass_ids: Array[String] = [
        "forest_grass_1_a_color1",
        "forest_grass_1_b_color1",
        "forest_grass_1_c_color1",
        "forest_grass_1_d_color1",
        "forest_grass_2_a_color1",
        "forest_grass_2_b_color1",
        "forest_grass_2_c_color1",
        "forest_grass_2_d_color1",
        "forest_grass_1_a_singlesided_color1",
        "forest_grass_1_c_singlesided_color1",
        "forest_grass_2_a_singlesided_color1",
        "forest_grass_2_c_singlesided_color1",
    ]

    var bush_ids: Array[String] = [
        "forest_bush_1_b_color1",
        "forest_bush_1_d_color1",
        "forest_bush_2_b_color1",
        "forest_bush_2_d_color1",
        "forest_bush_3_a_color1",
        "forest_bush_3_c_color1",
        "forest_bush_4_a_color1",
        "forest_bush_4_c_color1",
    ]

    var rock_ids: Array[String] = [
        "forest_rock_1_c_color1",
        "forest_rock_1_g_color1",
        "forest_rock_1_m_color1",
        "forest_rock_2_b_color1",
        "forest_rock_2_f_color1",
        "forest_rock_2_h_color1",
        "forest_rock_3_d_color1",
        "forest_rock_3_k_color1",
        "forest_rock_3_n_color1",
    ]

    var tree_ids: Array[String] = [
        "forest_tree_1_a_color1",
        "forest_tree_1_b_color1",
        "forest_tree_2_a_color1",
        "forest_tree_2_c_color1",
        "forest_tree_2_e_color1",
        "forest_tree_3_a_color1",
        "forest_tree_3_b_color1",
        "forest_tree_4_a_color1",
        "forest_tree_4_b_color1",
        "forest_tree_4_c_color1",
    ]

    var river_cfg: Dictionary = config.get("river", {})
    var river_row := int(river_cfg.get("row", 9))

    for r in range(rows):
        for c in range(columns):
            var key := _cell_key(c, r)

            if r == river_row:
                _dress_river_edge(c, r, forest_profile, grass_ids, rock_ids)
                continue

            if road_cells.has(key) or building_cells.has(key):
                continue

            var level := _terrain_level(c, r)
            var center := _hex_position(
                c,
                r,
                float(level) * terrace_step
            )

            var grass_count := 2
            if level > 0:
                grass_count = 3

            for _grass_index in range(grass_count):
                var grass_id: String = grass_ids[
                    rng.randi_range(0, grass_ids.size() - 1)
                ]
                WorldKitRuntime.instantiate_asset(
                    self,
                    grass_id,
                    center
                    + _random_flat_offset(1.35)
                    + Vector3(0.0, 0.03, 0.0),
                    rng.randf_range(0.0, 360.0),
                    rng.randf_range(0.45, 0.70),
                    0.0,
                    forest_profile
                )

            var bush_probability := 0.26
            var rock_probability := 0.18
            var tree_probability := 0.12

            if level == 1:
                bush_probability = 0.38
                rock_probability = 0.25
                tree_probability = 0.28
            elif level >= 2:
                bush_probability = 0.48
                rock_probability = 0.36
                tree_probability = 0.52

            if rng.randf() < bush_probability:
                var bush_id: String = bush_ids[
                    rng.randi_range(0, bush_ids.size() - 1)
                ]
                WorldKitRuntime.instantiate_asset(
                    self,
                    bush_id,
                    center + _random_flat_offset(1.15),
                    rng.randf_range(0.0, 360.0),
                    rng.randf_range(0.42, 0.66),
                    0.0,
                    forest_profile
                )

            if rng.randf() < rock_probability:
                var rock_id: String = rock_ids[
                    rng.randi_range(0, rock_ids.size() - 1)
                ]
                WorldKitRuntime.instantiate_asset(
                    self,
                    rock_id,
                    center + _random_flat_offset(1.15),
                    rng.randf_range(0.0, 360.0),
                    rng.randf_range(0.15, 0.25),
                    0.0,
                    forest_profile
                )

            if rng.randf() < tree_probability:
                var tree_id: String = tree_ids[
                    rng.randi_range(0, tree_ids.size() - 1)
                ]
                WorldKitRuntime.instantiate_asset(
                    self,
                    tree_id,
                    center + _random_flat_offset(0.95),
                    rng.randf_range(0.0, 360.0),
                    rng.randf_range(0.95, 1.35),
                    0.0,
                    forest_profile
                )

            if level <= 1 and rng.randf() < 0.16:
                _add_flower_cluster(
                    center
                    + _random_flat_offset(1.0)
                    + Vector3(0.0, 0.04, 0.0)
                )


func _dress_river_edge(
    c: int,
    r: int,
    forest_profile: String,
    grass_ids: Array[String],
    rock_ids: Array[String]
) -> void:
    var center := _hex_position(c, r, 0.0)

    var river_cfg: Dictionary = config.get("river", {})
    var crossing_cols: Array[int] = []
    for raw_col in river_cfg.get("crossing_cols", []):
        crossing_cols.append(int(raw_col))
    if crossing_cols.has(c):
        return

    var grass_id: String = grass_ids[
        rng.randi_range(0, grass_ids.size() - 1)
    ]
    WorldKitRuntime.instantiate_asset(
        self,
        grass_id,
        center + Vector3(0.0, 0.03, 1.5),
        rng.randf_range(0.0, 360.0),
        0.58,
        0.0,
        forest_profile
    )

    var rock_id: String = rock_ids[
        rng.randi_range(0, rock_ids.size() - 1)
    ]
    WorldKitRuntime.instantiate_asset(
        self,
        rock_id,
        center + Vector3(0.8, 0.02, -1.35),
        rng.randf_range(0.0, 360.0),
        0.18,
        0.0,
        forest_profile
    )


func _build_fences() -> void:
    var building_profile := String(
        config.get("building_profile_id", "core_candidate_b")
    )

    var fence_cells: Array[Vector2i] = [
        Vector2i(1, 5),
        Vector2i(8, 5),
        Vector2i(1, 7),
        Vector2i(8, 7),
        Vector2i(2, 2),
        Vector2i(8, 2),
    ]

    for cell: Vector2i in fence_cells:
        var level := _terrain_level(cell.x, cell.y)
        var center := _hex_position(
            cell.x,
            cell.y,
            float(level) * terrace_step
        )
        var yaw := _yaw_toward_nearest_road(center)

        WorldKitRuntime.instantiate_asset(
            self,
            "med_fence_wood_straight",
            center + Vector3(0.0, 0.0, 1.55),
            yaw,
            1.65,
            0.0,
            building_profile
        )


func _add_flower_cluster(center: Vector3) -> void:
    var flower_colors: Array[Color] = [
        _color("strawberry"),
        _color("lavender"),
        _color("butter_yellow"),
        _color("powder_blue"),
    ]
    var flower_color: Color = flower_colors[
        rng.randi_range(0, flower_colors.size() - 1)
    ]

    for _index in range(rng.randi_range(3, 6)):
        var offset := _random_flat_offset(0.50)

        var stem := MeshInstance3D.new()
        var stem_mesh := CylinderMesh.new()
        stem_mesh.top_radius = 0.018
        stem_mesh.bottom_radius = 0.025
        stem_mesh.height = 0.23
        stem_mesh.radial_segments = 5
        stem.mesh = stem_mesh
        stem.position = center + offset + Vector3(0.0, 0.115, 0.0)
        stem.material_override = _simple_material(
            _color("sage").darkened(0.12)
        )
        add_child(stem)

        var head := MeshInstance3D.new()
        var head_mesh := SphereMesh.new()
        head_mesh.radius = 0.070
        head_mesh.height = 0.14
        head_mesh.radial_segments = 7
        head_mesh.rings = 4
        head.mesh = head_mesh
        head.position = center + offset + Vector3(0.0, 0.26, 0.0)
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
            position + Vector3(0.0, -0.34, 0.0),
            Vector3(hex_x * 0.96, 0.68, 2.18 * tile_scale),
            Vector3.ZERO
        )
        return

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


func _add_slope_collider(c: int, r: int) -> void:
    var cell := Vector2i(c, r)
    var level := _terrain_level(c, r)
    var raw_connections: Array = road_connections.get(_cell_key(c, r), [])
    var lower_neighbor := Vector2i(-999, -999)

    for raw_direction in raw_connections:
        var direction := int(raw_direction)
        var neighbor := _neighbor_for_direction(cell, direction)
        if (
            neighbor.x < 0
            or neighbor.x >= columns
            or neighbor.y < 0
            or neighbor.y >= rows
        ):
            continue

        if _terrain_level(neighbor.x, neighbor.y) < level:
            lower_neighbor = neighbor
            break

    if lower_neighbor.x == -999:
        _add_tile_collider(
            _hex_position(c, r, float(level) * terrace_step),
            level
        )
        return

    var low_level := _terrain_level(lower_neighbor.x, lower_neighbor.y)
    var low := _hex_position(
        lower_neighbor.x,
        lower_neighbor.y,
        float(low_level) * terrace_step
    )
    var high := _hex_position(c, r, float(level) * terrace_step)
    var delta := high - low
    var horizontal := Vector3(delta.x, 0.0, delta.z)
    var horizontal_length := horizontal.length()

    if horizontal_length < 0.001:
        return

    var length := sqrt(
        horizontal_length * horizontal_length
        + terrace_step * terrace_step
    )
    var midpoint := (low + high) * 0.5 + Vector3(0.0, 0.08, 0.0)
    var yaw := rad_to_deg(atan2(horizontal.x, horizontal.z))
    var pitch := -rad_to_deg(atan2(terrace_step, horizontal_length))

    _add_box_collider(
        "RoadSlopeCollision",
        midpoint,
        Vector3(2.55, 0.40, length),
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
    _add_box_collider(
        "NorthBoundary",
        Vector3(0.0, 3.0, -half),
        Vector3(52.0, 6.0, 0.5),
        Vector3.ZERO
    )
    _add_box_collider(
        "SouthBoundary",
        Vector3(0.0, 3.0, half),
        Vector3(52.0, 6.0, 0.5),
        Vector3.ZERO
    )
    _add_box_collider(
        "WestBoundary",
        Vector3(-half, 3.0, 0.0),
        Vector3(0.5, 6.0, 52.0),
        Vector3.ZERO
    )
    _add_box_collider(
        "EastBoundary",
        Vector3(half, 3.0, 0.0),
        Vector3(0.5, 6.0, 52.0),
        Vector3.ZERO
    )


func _place_player() -> void:
    var player := get_node_or_null("Player") as Node3D
    if player == null:
        return

    var spawn: Dictionary = config.get("spawn", {})
    var c := int(spawn.get("col", 4))
    var r := int(spawn.get("row", 11))
    var level := _terrain_level(c, r)

    player.position = _hex_position(
        c,
        r,
        float(level) * terrace_step + float(spawn.get("y", 0.85))
    )


func _build_hud() -> void:
    var hud := CanvasLayer.new()
    add_child(hud)

    var panel := ColorRect.new()
    panel.offset_left = 18.0
    panel.offset_top = 18.0
    panel.offset_right = 650.0
    panel.offset_bottom = 134.0
    panel.color = Color(0.08, 0.07, 0.1, 0.78)
    hud.add_child(panel)

    var title := Label.new()
    title.offset_left = 16.0
    title.offset_top = 10.0
    title.offset_right = 615.0
    title.offset_bottom = 38.0
    title.text = "Mini Utopia · Storybook Terraced Town 50×50 v0.5"
    panel.add_child(title)

    var info := Label.new()
    info.offset_left = 16.0
    info.offset_top = 42.0
    info.offset_right = 615.0
    info.offset_bottom = 104.0
    info.text = "Layered KayKit terrain · 1 horizontal avenue + 2 side streets\n30 street-facing buildings · 2 river crossings · mountain ring\nForest Nature grass / bushes / rocks / trees · WASD / Shift / Space"
    panel.add_child(info)


func _show_missing_assets() -> void:
    var label := Label3D.new()
    label.text = "Mountain Town assets missing\nRun: python3 tools/prepare_mountain_town_assets.py --clean"
    label.font_size = 42
    label.modulate = _color("cream_base")
    label.outline_size = 10
    label.outline_modulate = _color("deep_ink")
    label.position = Vector3(0.0, 4.0, 0.0)
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(label)


func _random_flat_offset(radius: float) -> Vector3:
    var angle := rng.randf_range(0.0, TAU)
    var distance := sqrt(rng.randf()) * radius
    return Vector3(
        cos(angle) * distance,
        0.0,
        sin(angle) * distance
    )


func _cell_key(c: int, r: int) -> String:
    return str(c) + ":" + str(r)


func _vec3(value) -> Vector3:
    if typeof(value) == TYPE_ARRAY and value.size() >= 3:
        return Vector3(
            float(value[0]),
            float(value[1]),
            float(value[2])
        )
    return Vector3.ZERO

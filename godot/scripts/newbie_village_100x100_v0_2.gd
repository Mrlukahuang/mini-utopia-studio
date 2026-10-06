extends Node3D

const WORLD_SIZE := 100.0
const BLOCK_UNIT := 2.0
const GROUND_BLOCK_SCALE := 4.0
const MAIN_ROAD_WIDTH_BLOCKS := 3
const BRANCH_ROAD_WIDTH_BLOCKS := 2
const HOUSE_TARGET_HEIGHT := 4.8
const SKELETON_COUNT := 2

const CLIFF_COLOR := Color("#808991")
const GRASS_FALLBACK_COLOR := Color("#35A96E")
const ROAD_FALLBACK_COLOR := Color("#FFD45F")
const STEP_COLOR := Color("#69C955")

var rng := RandomNumberGenerator.new()
var yellow_block_asset_id := ""
var green_block_asset_id := ""
var skeleton_asset_id := ""


func _ready() -> void:
    rng.seed = 100214
    _setup_environment()
    _resolve_vault_assets()
    _build_solid_foundation()
    _build_green_block_valley()
    _build_layered_forest_mountains()
    _build_yellow_block_roads()
    _build_central_plaza()
    _build_houses_on_pads()
    _build_resource_yard()
    _build_forest_nature_dressing()
    _build_skeletons()
    _build_world_boundary()
    _build_hud()


func _setup_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color("#86C8E7")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#FFE4B7")
    env.ambient_light_energy = 0.34
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.tonemap_exposure = 0.90
    env.fog_enabled = true
    env.fog_light_color = Color("#B9DEED")
    env.fog_light_energy = 0.14
    env.fog_density = 0.003
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-50.0, -34.0, 0.0)
    sun.light_color = Color("#FFE3A6")
    sun.light_energy = 0.80
    sun.shadow_enabled = true
    sun.shadow_opacity = 0.72
    add_child(sun)

    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-22.0, 145.0, 0.0)
    fill.light_color = Color("#A9D8ED")
    fill.light_energy = 0.07
    fill.shadow_enabled = false
    add_child(fill)


func _resolve_vault_assets() -> void:
    if not AssetVaultRuntime.is_installed():
        push_error("Newbie Village v0.2 requires the Full Asset Vault.")
        return

    var yellow_entry := AssetVaultRuntime.first_entry_matching(
        ["block"],
        ["block", "yellow"]
    )
    if yellow_entry.is_empty():
        yellow_entry = AssetVaultRuntime.first_entry_matching(
            ["block"],
            ["yellow"]
        )
    if not yellow_entry.is_empty():
        yellow_block_asset_id = String(yellow_entry.get("id", ""))
        print(
            "Newbie Village yellow Block Bits asset: ",
            yellow_entry.get("source_member", "")
        )
    else:
        push_warning(
            "No plain yellow Block Bits asset found; using solid yellow fallback."
        )

    var green_entry := AssetVaultRuntime.first_entry_matching(
        ["block"],
        ["block", "green"]
    )
    if green_entry.is_empty():
        green_entry = AssetVaultRuntime.first_entry_matching(
            ["block"],
            ["green"]
        )
    if not green_entry.is_empty():
        green_block_asset_id = String(green_entry.get("id", ""))
        print(
            "Newbie Village green Block Bits asset: ",
            green_entry.get("source_member", "")
        )
    else:
        push_warning(
            "No plain green Block Bits asset found; using solid green fallback."
        )

    var skeleton_entry := AssetVaultRuntime.first_entry_matching(
        ["skeleton"],
        ["skeleton"]
    )
    if skeleton_entry.is_empty():
        skeleton_entry = AssetVaultRuntime.first_entry_matching(
            ["skeleton"],
            []
        )
    if not skeleton_entry.is_empty():
        skeleton_asset_id = String(skeleton_entry.get("id", ""))
    else:
        push_warning(
            "No Skeleton Pack asset found; using visible fallback skeleton markers."
        )


func _build_solid_foundation() -> void:
    # One simple collider keeps the complete 100x100 ground physically solid.
    _add_solid_box(
        "WorldFoundation",
        Vector3(0.0, -2.0, 0.0),
        Vector3(WORLD_SIZE, 4.0, WORLD_SIZE),
        CLIFF_COLOR
    )


func _build_green_block_valley() -> void:
    # The visible settlement floor is made from the plain green Block Bits cube.
    # 4m presentation blocks keep the node count sensible while retaining the
    # block-built visual language.
    for x_value in range(-36, 37, 4):
        for z_value in range(-36, 37, 4):
            _place_green_surface_block(
                Vector3(float(x_value), -2.0, float(z_value)),
                GROUND_BLOCK_SCALE
            )


func _build_layered_forest_mountains() -> void:
    # Level 1: wide cliff shelves enclosing the valley, with deliberate gaps
    # around the south and north road approaches.
    var level_one := [
        ["WestLowA", Vector2(-43.0, -22.0), Vector2(14.0, 34.0), 4.0],
        ["WestLowB", Vector2(-43.0, 22.0), Vector2(14.0, 30.0), 4.0],
        ["EastLowA", Vector2(43.0, -22.0), Vector2(14.0, 34.0), 4.4],
        ["EastLowB", Vector2(43.0, 22.0), Vector2(14.0, 30.0), 4.4],
        ["NorthLowA", Vector2(-23.0, -43.0), Vector2(34.0, 14.0), 4.2],
        ["NorthLowB", Vector2(23.0, -43.0), Vector2(30.0, 14.0), 4.2],
        ["SouthLowA", Vector2(-23.0, 43.0), Vector2(34.0, 14.0), 3.8],
        ["SouthLowB", Vector2(23.0, 43.0), Vector2(30.0, 14.0), 3.8],
    ]
    for item in level_one:
        _add_block_cliff_terrace(
            String(item[0]),
            item[1],
            item[2],
            float(item[3])
        )

    # Level 2: the additional mountain shelf requested in the reference.
    var level_two := [
        ["NorthWestUpper", Vector2(-42.0, -41.0), Vector2(18.0, 18.0), 8.0],
        ["NorthEastUpper", Vector2(42.0, -41.0), Vector2(18.0, 18.0), 8.4],
        ["SouthWestUpper", Vector2(-42.0, 41.0), Vector2(18.0, 18.0), 7.6],
        ["SouthEastUpper", Vector2(42.0, 41.0), Vector2(18.0, 18.0), 8.2],
    ]
    for item in level_two:
        _add_block_cliff_terrace(
            String(item[0]),
            item[1],
            item[2],
            float(item[3])
        )

    # Level 3: two compact peaks give the world a stronger skyline and a
    # destination-like silhouette rather than a flat perimeter wall.
    _add_block_cliff_terrace(
        "NorthWestPeak",
        Vector2(-43.0, -43.0),
        Vector2(10.0, 10.0),
        12.0
    )
    _add_block_cliff_terrace(
        "SouthEastPeak",
        Vector2(43.0, 43.0),
        Vector2(10.0, 10.0),
        12.4
    )

    # Walkable stepped routes visually connect the valley to two lookout shelves.
    _build_terrace_steps(
        Vector3(-35.0, 0.0, -27.0),
        Vector3(-1.0, 0.0, 0.0),
        6,
        4.0
    )
    _build_terrace_steps(
        Vector3(35.0, 0.0, 27.0),
        Vector3(1.0, 0.0, 0.0),
        6,
        4.4
    )


func _add_block_cliff_terrace(
    terrace_name: String,
    center: Vector2,
    size: Vector2,
    height: float
) -> void:
    _add_solid_box(
        terrace_name + "_Cliff",
        Vector3(center.x, height * 0.5, center.y),
        Vector3(size.x, height, size.y),
        CLIFF_COLOR
    )

    # Green Block Bits along the top edges create the same green-cap / grey-rock
    # read as the Forest Nature reference while the procedural mass stays solid.
    var x_start := int(floor(center.x - size.x * 0.5 + 2.0))
    var x_end := int(ceil(center.x + size.x * 0.5 - 2.0))
    var z_start := int(floor(center.y - size.y * 0.5 + 2.0))
    var z_end := int(ceil(center.y + size.y * 0.5 - 2.0))

    for x_value in range(x_start, x_end + 1, 4):
        for z_value in range(z_start, z_end + 1, 4):
            _place_green_surface_block(
                Vector3(float(x_value), height - 2.0, float(z_value)),
                GROUND_BLOCK_SCALE
            )


func _build_terrace_steps(
    start: Vector3,
    direction: Vector3,
    count: int,
    target_height: float
) -> void:
    for index in range(count):
        var progress := float(index + 1) / float(count)
        var top_y := target_height * progress
        var position := start + direction * float(index) * 2.2
        _add_solid_box(
            "MountainStep_%s_%s" % [str(start.x), str(index)],
            Vector3(position.x, top_y * 0.5, position.z),
            Vector3(4.4, top_y, 5.0),
            STEP_COLOR
        )


func _build_yellow_block_roads() -> void:
    # One north-south main road, exactly three 2m Block Bits cubes wide.
    for z_value in range(-38, 39, 2):
        for lane in [-1, 0, 1]:
            _place_yellow_road_block(
                Vector3(
                    float(lane) * BLOCK_UNIT,
                    -1.0,
                    float(z_value)
                )
            )

    # Two east-west branch roads, exactly two cubes wide.
    for branch_z in [-16.0, 14.0]:
        for x_value in range(-34, 35, 2):
            for z_offset in [-1.0, 1.0]:
                _place_yellow_road_block(
                    Vector3(
                        float(x_value),
                        -1.0,
                        branch_z + z_offset
                    )
                )

    # Collision stripes make the roads explicitly solid even if a visual source
    # model has no collider.
    _add_collision_box_only(
        "MainRoadSolid",
        Vector3(0.0, 0.08, 0.0),
        Vector3(6.0, 0.16, 78.0)
    )
    _add_collision_box_only(
        "BranchRoadNorthSolid",
        Vector3(0.0, 0.08, -16.0),
        Vector3(70.0, 0.16, 4.0)
    )
    _add_collision_box_only(
        "BranchRoadSouthSolid",
        Vector3(0.0, 0.08, 14.0),
        Vector3(70.0, 0.16, 4.0)
    )


func _place_yellow_road_block(world_position: Vector3) -> void:
    if not yellow_block_asset_id.is_empty():
        var instance := AssetVaultRuntime.instantiate_by_id(
            self,
            yellow_block_asset_id,
            world_position,
            0.0,
            BLOCK_UNIT
        )
        if instance != null:
            return

    _add_visual_box(
        "YellowRoadFallback",
        world_position,
        Vector3(BLOCK_UNIT, BLOCK_UNIT, BLOCK_UNIT),
        ROAD_FALLBACK_COLOR
    )


func _place_green_surface_block(
    world_position: Vector3,
    scale_value: float
) -> void:
    if not green_block_asset_id.is_empty():
        var instance := AssetVaultRuntime.instantiate_by_id(
            self,
            green_block_asset_id,
            world_position,
            0.0,
            scale_value
        )
        if instance != null:
            return

    _add_visual_box(
        "GreenBlockFallback",
        world_position,
        Vector3(scale_value, scale_value, scale_value),
        GRASS_FALLBACK_COLOR
    )


func _build_central_plaza() -> void:
    # The road intersection itself is the plaza floor. A low central marker
    # gives the player a visual anchor without hiding the Block Bits surface.
    _add_solid_box(
        "PlazaMarker",
        Vector3(0.0, 0.45, 0.0),
        Vector3(2.6, 0.9, 2.6),
        Color("#D9BC78")
    )


func _build_houses_on_pads() -> void:
    var homes := [
        "building_home_A_red.gltf",
        "building_home_B_red.gltf",
        "building_home_A_blue.gltf",
        "building_home_B_blue.gltf",
        "building_home_A_yellow.gltf",
        "building_home_B_yellow.gltf",
    ]

    # Main-street homes.
    for z_value in [-30.0, -24.0, -8.0, 8.0, 24.0, 30.0]:
        _spawn_house_on_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(-10.0, 0.0, z_value),
            Vector3(0.0, 0.0, z_value),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35),
            0.65
        )
        _spawn_house_on_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(10.0, 0.0, z_value),
            Vector3(0.0, 0.0, z_value),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35),
            0.65
        )

    # First horizontal branch: houses become more elevated toward the edges.
    for x_value in [-30.0, -22.0, -14.0, 14.0, 22.0]:
        var pad_height := _branch_pad_height(x_value)
        _spawn_house_on_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, -23.0),
            Vector3(x_value, 0.0, -16.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35),
            pad_height
        )
        _spawn_house_on_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, -9.0),
            Vector3(x_value, 0.0, -16.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35),
            pad_height
        )

    # Second horizontal branch.
    for x_value in [-30.0, -22.0, -14.0, 14.0, 22.0, 30.0]:
        var pad_height := _branch_pad_height(x_value)
        _spawn_house_on_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, 7.0),
            Vector3(x_value, 0.0, 14.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35),
            pad_height
        )
        _spawn_house_on_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, 21.0),
            Vector3(x_value, 0.0, 14.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35),
            pad_height
        )

    # Larger village landmarks close to the centre.
    _spawn_house_on_pad(
        "building_tavern_red.gltf",
        Vector3(-16.0, 0.0, -4.0),
        Vector3(0.0, 0.0, -4.0),
        5.8,
        0.8
    )
    _spawn_house_on_pad(
        "building_market_red.gltf",
        Vector3(16.0, 0.0, -4.0),
        Vector3(0.0, 0.0, -4.0),
        5.5,
        0.8
    )
    _spawn_house_on_pad(
        "building_blacksmith_red.gltf",
        Vector3(-16.0, 0.0, 4.0),
        Vector3(0.0, 0.0, 4.0),
        5.8,
        0.8
    )
    _spawn_house_on_pad(
        "building_church_red.gltf",
        Vector3(16.0, 0.0, 4.0),
        Vector3(0.0, 0.0, 4.0),
        6.5,
        0.8
    )


func _branch_pad_height(x_value: float) -> float:
    if absf(x_value) >= 28.0:
        return 2.4
    if absf(x_value) >= 20.0:
        return 1.6
    return 0.75


func _spawn_house_on_pad(
    filename: String,
    base_position: Vector3,
    road_target: Vector3,
    target_height: float,
    pad_height: float
) -> void:
    _build_house_pad(base_position, road_target, pad_height)

    var house_position := Vector3(
        base_position.x,
        pad_height + 0.05,
        base_position.z
    )
    var yaw := _yaw_toward(base_position, road_target) + 180.0
    var node := AssetVaultRuntime.instantiate_first_filename(
        self,
        filename,
        house_position,
        yaw,
        1.0,
        target_height
    )

    if node == null:
        push_warning("Missing village building asset: " + filename)
        _add_visual_box(
            "BuildingFallback",
            house_position + Vector3(0.0, target_height * 0.5, 0.0),
            Vector3(4.2, target_height, 4.0),
            Color("#D89B63")
        )

    _add_collision_box_only(
        "BuildingCollision",
        house_position + Vector3(0.0, 1.95, 0.0),
        Vector3(4.5, 3.9, 4.2)
    )


func _build_house_pad(
    base_position: Vector3,
    road_target: Vector3,
    pad_height: float
) -> void:
    # Grey solid core + green Block Bits cap: houses visibly sit on terrain.
    _add_solid_box(
        "HousePadCore",
        Vector3(
            base_position.x,
            pad_height * 0.5,
            base_position.z
        ),
        Vector3(7.0, pad_height, 7.0),
        CLIFF_COLOR
    )

    for x_offset in [-2.0, 0.0, 2.0]:
        for z_offset in [-2.0, 0.0, 2.0]:
            _place_green_surface_block(
                Vector3(
                    base_position.x + x_offset,
                    pad_height - 1.0,
                    base_position.z + z_offset
                ),
                BLOCK_UNIT
            )

    if pad_height > 1.0:
        _build_pad_steps(base_position, road_target, pad_height)


func _build_pad_steps(
    pad_position: Vector3,
    road_target: Vector3,
    pad_height: float
) -> void:
    var direction := road_target - pad_position
    direction.y = 0.0
    if direction.length_squared() < 0.001:
        return
    direction = direction.normalized()

    var steps := 3
    for index in range(steps):
        var progress := float(index + 1) / float(steps)
        var top_y := pad_height * progress
        var distance := 4.5 + float(steps - index) * 1.1
        var step_position := pad_position + direction * distance
        _add_solid_box(
            "HousePadStep",
            Vector3(step_position.x, top_y * 0.5, step_position.z),
            Vector3(2.6, top_y, 2.4),
            STEP_COLOR
        )


func _build_resource_yard() -> void:
    var origin := Vector3(30.0, 0.0, -7.0)
    var pad_height := 2.0
    _build_house_pad(origin, Vector3(30.0, 0.0, -16.0), pad_height)

    var props := [
        ["Wood_Log_Stack.gltf", Vector3(-2.2, 0.0, -2.2), 1.15],
        ["Wood_Planks_Stack_Medium.gltf", Vector3(1.4, 0.0, -2.1), 1.10],
        ["Stone_Chunks_Large.gltf", Vector3(2.0, 0.0, 1.6), 1.05],
        ["Stone_Bricks_Stack_Medium.gltf", Vector3(-2.0, 0.0, 1.5), 1.10],
        ["Pallet_Wood.gltf", Vector3(0.4, 0.0, 2.8), 1.05],
    ]

    for item in props:
        var filename := String(item[0])
        var offset: Vector3 = item[1]
        var scale_value := float(item[2])
        AssetVaultRuntime.instantiate_first_filename(
            self,
            filename,
            Vector3(
                origin.x + offset.x,
                pad_height + offset.y + 0.05,
                origin.z + offset.z
            ),
            rng.randf_range(-20.0, 20.0),
            scale_value
        )

    _add_collision_box_only(
        "ResourceYardCollisionA",
        Vector3(origin.x - 1.8, pad_height + 0.8, origin.z - 1.6),
        Vector3(3.4, 1.6, 3.4)
    )
    _add_collision_box_only(
        "ResourceYardCollisionB",
        Vector3(origin.x + 2.0, pad_height + 0.8, origin.z + 1.2),
        Vector3(3.4, 1.6, 3.4)
    )


func _build_forest_nature_dressing() -> void:
    var tree_files := [
        "Tree_1_A_Color1.gltf",
        "Tree_1_B_Color1.gltf",
        "Tree_2_A_Color1.gltf",
        "Tree_2_C_Color1.gltf",
        "Tree_2_E_Color1.gltf",
        "Tree_3_A_Color1.gltf",
        "Tree_3_B_Color1.gltf",
        "Tree_4_A_Color1.gltf",
        "Tree_4_B_Color1.gltf",
        "Tree_4_C_Color1.gltf",
    ]
    var rock_files := [
        "Rock_1_C_Color1.gltf",
        "Rock_1_G_Color1.gltf",
        "Rock_1_M_Color1.gltf",
        "Rock_2_B_Color1.gltf",
        "Rock_2_F_Color1.gltf",
        "Rock_2_H_Color1.gltf",
        "Rock_3_D_Color1.gltf",
        "Rock_3_K_Color1.gltf",
        "Rock_3_N_Color1.gltf",
    ]
    var bush_files := [
        "Bush_1_B_Color1.gltf",
        "Bush_1_D_Color1.gltf",
        "Bush_2_B_Color1.gltf",
        "Bush_2_D_Color1.gltf",
        "Bush_3_A_Color1.gltf",
        "Bush_3_C_Color1.gltf",
        "Bush_4_A_Color1.gltf",
        "Bush_4_C_Color1.gltf",
    ]
    var grass_files := [
        "Grass_1_A_Color1.gltf",
        "Grass_1_B_Color1.gltf",
        "Grass_1_C_Color1.gltf",
        "Grass_2_A_Color1.gltf",
        "Grass_2_B_Color1.gltf",
        "Grass_2_C_Color1.gltf",
    ]

    # Explicit Forest Nature clusters at valley, first shelf, second shelf and
    # peak heights make the mountain ring read like the supplied reference.
    var clusters := [
        [Vector3(-32.0, 0.05, -31.0), 7.0, 5],
        [Vector3(31.0, 0.05, -31.0), 7.0, 5],
        [Vector3(-31.0, 0.05, 30.0), 7.0, 5],
        [Vector3(31.0, 0.05, 30.0), 7.0, 5],
        [Vector3(-43.0, 4.15, -20.0), 8.0, 8],
        [Vector3(43.0, 4.55, 20.0), 8.0, 8],
        [Vector3(-22.0, 4.35, -43.0), 8.0, 8],
        [Vector3(22.0, 3.95, 43.0), 8.0, 8],
        [Vector3(-42.0, 8.15, -41.0), 6.5, 8],
        [Vector3(42.0, 8.55, -41.0), 6.5, 8],
        [Vector3(-42.0, 7.75, 41.0), 6.5, 8],
        [Vector3(42.0, 8.35, 41.0), 6.5, 8],
        [Vector3(-43.0, 12.15, -43.0), 4.0, 5],
        [Vector3(43.0, 12.55, 43.0), 4.0, 5],
    ]

    for cluster in clusters:
        _scatter_forest_cluster(
            cluster[0],
            float(cluster[1]),
            int(cluster[2]),
            tree_files,
            rock_files,
            bush_files,
            grass_files
        )

    # Small village green pockets preserve breathing room between houses.
    for center in [
        Vector3(-20.0, 0.05, -30.0),
        Vector3(20.0, 0.05, -30.0),
        Vector3(-25.0, 0.05, 0.0),
        Vector3(25.0, 0.05, 0.0),
        Vector3(-20.0, 0.05, 29.0),
        Vector3(20.0, 0.05, 29.0),
    ]:
        var bush_file: String = bush_files[
            rng.randi_range(0, bush_files.size() - 1)
        ]
        AssetVaultRuntime.instantiate_first_filename(
            self,
            bush_file,
            center,
            rng.randf_range(0.0, 360.0),
            rng.randf_range(0.85, 1.20)
        )
        for _index in range(3):
            var grass_file: String = grass_files[
                rng.randi_range(0, grass_files.size() - 1)
            ]
            AssetVaultRuntime.instantiate_first_filename(
                self,
                grass_file,
                center + Vector3(
                    rng.randf_range(-2.3, 2.3),
                    0.0,
                    rng.randf_range(-2.3, 2.3)
                ),
                rng.randf_range(0.0, 360.0),
                rng.randf_range(0.65, 1.0)
            )


func _scatter_forest_cluster(
    center: Vector3,
    radius: float,
    count: int,
    tree_files: Array,
    rock_files: Array,
    bush_files: Array,
    grass_files: Array
) -> void:
    for index in range(count):
        var offset := Vector3(
            rng.randf_range(-radius, radius),
            0.0,
            rng.randf_range(-radius, radius)
        )
        var position := center + offset
        var tree_file: String = tree_files[
            rng.randi_range(0, tree_files.size() - 1)
        ]
        AssetVaultRuntime.instantiate_first_filename(
            self,
            tree_file,
            position,
            rng.randf_range(0.0, 360.0),
            rng.randf_range(1.05, 1.65)
        )

        if index % 2 == 0:
            var rock_file: String = rock_files[
                rng.randi_range(0, rock_files.size() - 1)
            ]
            AssetVaultRuntime.instantiate_first_filename(
                self,
                rock_file,
                position + Vector3(
                    rng.randf_range(-1.8, 1.8),
                    0.0,
                    rng.randf_range(-1.8, 1.8)
                ),
                rng.randf_range(0.0, 360.0),
                rng.randf_range(0.75, 1.35)
            )

        if index % 3 == 0:
            var bush_file: String = bush_files[
                rng.randi_range(0, bush_files.size() - 1)
            ]
            AssetVaultRuntime.instantiate_first_filename(
                self,
                bush_file,
                position + Vector3(
                    rng.randf_range(-1.6, 1.6),
                    0.0,
                    rng.randf_range(-1.6, 1.6)
                ),
                rng.randf_range(0.0, 360.0),
                rng.randf_range(0.75, 1.20)
            )

        if index % 2 == 1:
            var grass_file: String = grass_files[
                rng.randi_range(0, grass_files.size() - 1)
            ]
            AssetVaultRuntime.instantiate_first_filename(
                self,
                grass_file,
                position + Vector3(
                    rng.randf_range(-1.5, 1.5),
                    0.03,
                    rng.randf_range(-1.5, 1.5)
                ),
                rng.randf_range(0.0, 360.0),
                rng.randf_range(0.65, 0.95)
            )


func _build_skeletons() -> void:
    var positions := [
        Vector3(-41.0, 4.15, -18.0),
        Vector3(41.0, 4.55, 20.0),
    ]

    for index in range(SKELETON_COUNT):
        var position: Vector3 = positions[index]
        var skeleton: Node3D = null
        if not skeleton_asset_id.is_empty():
            skeleton = AssetVaultRuntime.instantiate_by_id(
                self,
                skeleton_asset_id,
                position,
                180.0 if index == 0 else 20.0,
                1.0,
                1.8
            )

        if skeleton == null:
            _build_skeleton_fallback(
                position,
                "SkeletonFallback_%s" % str(index + 1)
            )

        _add_collision_cylinder(
            "SkeletonCollision_%s" % str(index + 1),
            position + Vector3(0.0, 0.85, 0.0),
            0.45,
            1.7
        )


func _build_skeleton_fallback(position: Vector3, node_name: String) -> void:
    var root := Node3D.new()
    root.name = node_name
    root.position = position
    add_child(root)

    var bone_color := Color("#EFE8D6")
    _add_visual_sphere(root, Vector3(0.0, 1.55, 0.0), 0.24, bone_color)
    _add_visual_box_to(
        root,
        Vector3(0.0, 0.95, 0.0),
        Vector3(0.18, 0.72, 0.14),
        bone_color
    )
    _add_visual_box_to(
        root,
        Vector3(-0.20, 0.50, 0.0),
        Vector3(0.10, 0.65, 0.10),
        bone_color
    )
    _add_visual_box_to(
        root,
        Vector3(0.20, 0.50, 0.0),
        Vector3(0.10, 0.65, 0.10),
        bone_color
    )


func _build_world_boundary() -> void:
    _add_collision_box_only(
        "BoundaryWest",
        Vector3(-49.5, 6.0, 0.0),
        Vector3(1.0, 12.0, WORLD_SIZE)
    )
    _add_collision_box_only(
        "BoundaryEast",
        Vector3(49.5, 6.0, 0.0),
        Vector3(1.0, 12.0, WORLD_SIZE)
    )
    _add_collision_box_only(
        "BoundaryNorth",
        Vector3(0.0, 6.0, -49.5),
        Vector3(WORLD_SIZE, 12.0, 1.0)
    )
    _add_collision_box_only(
        "BoundarySouth",
        Vector3(0.0, 6.0, 49.5),
        Vector3(WORLD_SIZE, 12.0, 1.0)
    )


func _build_hud() -> void:
    var layer := CanvasLayer.new()
    add_child(layer)

    var panel := ColorRect.new()
    panel.position = Vector2(18.0, 18.0)
    panel.size = Vector2(650.0, 126.0)
    panel.color = Color(0.035, 0.07, 0.085, 0.78)
    layer.add_child(panel)

    var label := Label.new()
    label.position = Vector2(18.0, 10.0)
    label.size = Vector2(620.0, 106.0)
    label.text = (
        "新手村 · 100×100 v0.2\n"
        + "Yellow Block Bits roads · Green Block Bits village ground / house pads\n"
        + "Forest Nature layered mountains: valley + 2 extra elevation bands\n"
        + "1 main road (3 blocks) + 2 horizontal branches (2 blocks) · 2 skeletons\n"
        + "WASD / Shift / Space"
    )
    label.add_theme_font_size_override("font_size", 16)
    panel.add_child(label)


func _yaw_toward(source: Vector3, target: Vector3) -> float:
    var direction := target - source
    direction.y = 0.0
    if direction.length_squared() < 0.0001:
        return 0.0
    return rad_to_deg(atan2(direction.x, direction.z))


func _add_solid_box(
    node_name: String,
    center: Vector3,
    size: Vector3,
    color: Color
) -> StaticBody3D:
    var body := StaticBody3D.new()
    body.name = node_name
    body.position = center
    add_child(body)

    var mesh_instance := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = size
    mesh_instance.mesh = mesh
    mesh_instance.material_override = _material(color)
    body.add_child(mesh_instance)

    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = size
    collision.shape = shape
    body.add_child(collision)
    return body


func _add_visual_box(
    node_name: String,
    center: Vector3,
    size: Vector3,
    color: Color
) -> MeshInstance3D:
    var mesh_instance := MeshInstance3D.new()
    mesh_instance.name = node_name
    mesh_instance.position = center
    var mesh := BoxMesh.new()
    mesh.size = size
    mesh_instance.mesh = mesh
    mesh_instance.material_override = _material(color)
    add_child(mesh_instance)
    return mesh_instance


func _add_visual_box_to(
    parent: Node3D,
    center: Vector3,
    size: Vector3,
    color: Color
) -> void:
    var mesh_instance := MeshInstance3D.new()
    mesh_instance.position = center
    var mesh := BoxMesh.new()
    mesh.size = size
    mesh_instance.mesh = mesh
    mesh_instance.material_override = _material(color)
    parent.add_child(mesh_instance)


func _add_visual_sphere(
    parent: Node3D,
    center: Vector3,
    radius: float,
    color: Color
) -> void:
    var mesh_instance := MeshInstance3D.new()
    mesh_instance.position = center
    var mesh := SphereMesh.new()
    mesh.radius = radius
    mesh.height = radius * 2.0
    mesh_instance.mesh = mesh
    mesh_instance.material_override = _material(color)
    parent.add_child(mesh_instance)


func _add_collision_box_only(
    node_name: String,
    center: Vector3,
    size: Vector3
) -> void:
    var body := StaticBody3D.new()
    body.name = node_name
    body.position = center
    add_child(body)

    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = size
    collision.shape = shape
    body.add_child(collision)


func _add_collision_cylinder(
    node_name: String,
    center: Vector3,
    radius: float,
    height: float
) -> void:
    var body := StaticBody3D.new()
    body.name = node_name
    body.position = center
    add_child(body)

    var collision := CollisionShape3D.new()
    var shape := CylinderShape3D.new()
    shape.radius = radius
    shape.height = height
    collision.shape = shape
    body.add_child(collision)


func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.90
    return material

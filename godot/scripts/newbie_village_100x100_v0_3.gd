extends Node3D

const WORLD_SIZE := 100.0
const GROUND_TILE_SIZE := 4.0
const GROUND_CAP_THICKNESS := 0.60
const ROAD_TILE_SIZE := 2.0
const ROAD_HEIGHT := 0.36
const MAIN_ROAD_WIDTH_BLOCKS := 3
const BRANCH_ROAD_WIDTH_BLOCKS := 2
const HOUSE_TARGET_HEIGHT := 4.9
const HOUSE_PAD_CAP_THICKNESS := 0.60
const MOUNTAIN_CELL_SIZE := 8.0
const SKELETON_COUNT := 2

const CLIFF_COLOR := Color("#899198")
const GREEN_FALLBACK_COLOR := Color("#35A96E")
const YELLOW_FALLBACK_COLOR := Color("#FFD35A")
const STEP_COLOR := Color("#72CF59")

var rng := RandomNumberGenerator.new()
var yellow_block_asset_id := ""
var green_block_asset_id := ""
var skeleton_asset_id := ""


func _ready() -> void:
    rng.seed = 100315
    _setup_environment()
    _resolve_vault_assets()
    _build_aligned_valley_floor()
    _build_visible_yellow_roads()
    _build_irregular_layered_mountains()
    _build_houses_on_real_block_surfaces()
    _build_resource_yard()
    _build_forest_reference_dressing()
    _build_skeletons()
    _build_training_skeleton()
    _build_world_boundary()
    _build_hud()


func _setup_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color("#89CBE8")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#FFE5B8")
    env.ambient_light_energy = 0.34
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.tonemap_exposure = 0.90
    env.fog_enabled = true
    env.fog_light_color = Color("#C3E2EE")
    env.fog_light_energy = 0.14
    env.fog_density = 0.0028
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-49.0, -34.0, 0.0)
    sun.light_color = Color("#FFE3A9")
    sun.light_energy = 0.80
    sun.shadow_enabled = true
    sun.shadow_opacity = 0.72
    add_child(sun)

    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-23.0, 146.0, 0.0)
    fill.light_color = Color("#A7D6EA")
    fill.light_energy = 0.07
    fill.shadow_enabled = false
    add_child(fill)


func _resolve_vault_assets() -> void:
    if not AssetVaultRuntime.is_installed():
        push_error("Newbie Village v0.3 requires the Full Asset Vault.")
        return

    var plain_exclusions := [
        "ore",
        "grass",
        "snow",
        "brick",
        "rock",
        "lava",
        "water",
        "wood",
        "log",
        "mechan",
        "metal",
        "sand",
        "soil",
        "dirt",
    ]

    var yellow_entry := AssetVaultRuntime.best_entry_matching(
        ["block", "bits"],
        ["yellow"],
        plain_exclusions
    )
    if yellow_entry.is_empty():
        yellow_entry = AssetVaultRuntime.best_entry_matching(
            ["block"],
            ["yellow"],
            plain_exclusions
        )

    var green_entry := AssetVaultRuntime.best_entry_matching(
        ["block", "bits"],
        ["green"],
        plain_exclusions
    )
    if green_entry.is_empty():
        green_entry = AssetVaultRuntime.best_entry_matching(
            ["block"],
            ["green"],
            plain_exclusions
        )

    if not yellow_entry.is_empty():
        yellow_block_asset_id = String(yellow_entry.get("id", ""))
        print(
            "Newbie Village v0.3 yellow Block Bits: ",
            yellow_entry.get("source_member", "")
        )
    else:
        push_warning(
            "Plain yellow Block Bits cube was not found; using yellow solid fallback."
        )

    if not green_entry.is_empty():
        green_block_asset_id = String(green_entry.get("id", ""))
        print(
            "Newbie Village v0.3 green Block Bits: ",
            green_entry.get("source_member", "")
        )
    else:
        push_warning(
            "Plain green Block Bits cube was not found; using green solid fallback."
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


func _build_aligned_valley_floor() -> void:
    # Critical v0.3 rule:
    # the collider top and the visible Block Bits top are both exactly Y = 0.
    # This prevents the player from sinking into a visually raised but hollow tile.
    _add_solid_box(
        "ValleyFoundation",
        Vector3(0.0, -2.80, 0.0),
        Vector3(WORLD_SIZE, 4.40, WORLD_SIZE),
        CLIFF_COLOR
    )

    for x_value in range(-48, 49, 4):
        for z_value in range(-48, 49, 4):
            _place_green_box_fit(
                Vector3(
                    float(x_value),
                    -GROUND_CAP_THICKNESS,
                    float(z_value)
                ),
                Vector3(
                    GROUND_TILE_SIZE,
                    GROUND_CAP_THICKNESS,
                    GROUND_TILE_SIZE
                )
            )

    # One exact collision surface for the whole valley.
    _add_collision_box_only(
        "ValleyWalkSurface",
        Vector3(0.0, -0.30, 0.0),
        Vector3(WORLD_SIZE, 0.60, WORLD_SIZE)
    )


func _build_visible_yellow_roads() -> void:
    # Yellow blocks are deliberately 8cm higher than the green surface so the
    # top face cannot disappear through coplanar overlap.
    var road_bottom_y := 0.08 - ROAD_HEIGHT

    # N-S main road: exactly 3 tiles wide.
    for z_value in range(-40, 41, 2):
        for lane in [-1, 0, 1]:
            _place_yellow_box_fit(
                Vector3(
                    float(lane) * ROAD_TILE_SIZE,
                    road_bottom_y,
                    float(z_value)
                ),
                Vector3(ROAD_TILE_SIZE, ROAD_HEIGHT, ROAD_TILE_SIZE)
            )

    # Two E-W branches: exactly 2 tiles wide.
    for branch_z in [-16.0, 14.0]:
        for x_value in range(-36, 37, 2):
            for z_offset in [-1.0, 1.0]:
                _place_yellow_box_fit(
                    Vector3(
                        float(x_value),
                        road_bottom_y,
                        branch_z + z_offset
                    ),
                    Vector3(ROAD_TILE_SIZE, ROAD_HEIGHT, ROAD_TILE_SIZE)
                )

    _add_collision_box_only(
        "MainRoadSolid",
        Vector3(0.0, 0.04, 0.0),
        Vector3(6.0, 0.08, 82.0)
    )
    _add_collision_box_only(
        "BranchRoadNorthSolid",
        Vector3(0.0, 0.04, -16.0),
        Vector3(74.0, 0.08, 4.0)
    )
    _add_collision_box_only(
        "BranchRoadSouthSolid",
        Vector3(0.0, 0.04, 14.0),
        Vector3(74.0, 0.08, 4.0)
    )


func _build_irregular_layered_mountains() -> void:
    var wide_shape: Array[Vector2i] = [
        Vector2i(-1, -1),
        Vector2i(0, -1),
        Vector2i(1, -1),
        Vector2i(-1, 0),
        Vector2i(0, 0),
        Vector2i(1, 0),
        Vector2i(-1, 1),
        Vector2i(0, 1),
        Vector2i(1, 1),
        Vector2i(2, 0),
        Vector2i(0, 2),
    ]
    var upper_shape: Array[Vector2i] = [
        Vector2i(0, 0),
        Vector2i(1, 0),
        Vector2i(-1, 0),
        Vector2i(0, 1),
        Vector2i(0, -1),
        Vector2i(1, 1),
    ]
    var peak_shape: Array[Vector2i] = [
        Vector2i(0, 0),
        Vector2i(1, 0),
        Vector2i(0, 1),
    ]
    var strip_shape: Array[Vector2i] = [
        Vector2i(0, -2),
        Vector2i(0, -1),
        Vector2i(0, 0),
        Vector2i(0, 1),
        Vector2i(0, 2),
        Vector2i(1, -1),
        Vector2i(1, 1),
    ]

    # First shelf: broken clusters, not one rectangular wall.
    _build_cliff_cluster(
        "NorthWestShelf",
        Vector2(-38.0, -35.0),
        wide_shape,
        4.6
    )
    _build_cliff_cluster(
        "NorthEastShelf",
        Vector2(34.0, -35.0),
        wide_shape,
        4.8
    )
    _build_cliff_cluster(
        "SouthWestShelf",
        Vector2(-38.0, 35.0),
        wide_shape,
        4.4
    )
    _build_cliff_cluster(
        "SouthEastShelf",
        Vector2(34.0, 35.0),
        wide_shape,
        4.7
    )
    _build_cliff_cluster(
        "WestMidShelf",
        Vector2(-44.0, 0.0),
        strip_shape,
        4.2
    )
    _build_cliff_cluster(
        "EastMidShelf",
        Vector2(44.0, 0.0),
        strip_shape,
        4.4
    )

    # Second shelf: smaller top islands create the Forest Nature reference rhythm.
    _build_cliff_cluster(
        "NorthWestUpper",
        Vector2(-40.0, -38.0),
        upper_shape,
        8.5
    )
    _build_cliff_cluster(
        "NorthEastUpper",
        Vector2(38.0, -38.0),
        upper_shape,
        8.8
    )
    _build_cliff_cluster(
        "SouthWestUpper",
        Vector2(-40.0, 38.0),
        upper_shape,
        8.2
    )
    _build_cliff_cluster(
        "SouthEastUpper",
        Vector2(38.0, 38.0),
        upper_shape,
        8.6
    )

    # Third compact peaks make the elevation bands unmistakable.
    _build_cliff_cluster(
        "NorthWestPeak",
        Vector2(-42.0, -42.0),
        peak_shape,
        12.3
    )
    _build_cliff_cluster(
        "SouthEastPeak",
        Vector2(40.0, 40.0),
        peak_shape,
        12.6
    )

    # Two step routes make high shelves feel like destinations rather than scenery.
    _build_mountain_steps(
        Vector3(-31.0, 0.0, -26.0),
        Vector3(-1.0, 0.0, 0.0),
        8,
        4.6
    )
    _build_mountain_steps(
        Vector3(31.0, 0.0, 26.0),
        Vector3(1.0, 0.0, 0.0),
        8,
        4.7
    )


func _build_cliff_cluster(
    cluster_name: String,
    center: Vector2,
    cells: Array[Vector2i],
    top_y: float
) -> void:
    for index in range(cells.size()):
        var cell: Vector2i = cells[index]
        var x_value := center.x + float(cell.x) * MOUNTAIN_CELL_SIZE
        var z_value := center.y + float(cell.y) * MOUNTAIN_CELL_SIZE
        var core_height := top_y - GROUND_CAP_THICKNESS

        _add_solid_box(
            cluster_name + "_Core_%s" % str(index),
            Vector3(x_value, core_height * 0.5, z_value),
            Vector3(
                MOUNTAIN_CELL_SIZE,
                core_height,
                MOUNTAIN_CELL_SIZE
            ),
            CLIFF_COLOR
        )
        _place_green_box_fit(
            Vector3(
                x_value,
                top_y - GROUND_CAP_THICKNESS,
                z_value
            ),
            Vector3(
                MOUNTAIN_CELL_SIZE,
                GROUND_CAP_THICKNESS,
                MOUNTAIN_CELL_SIZE
            )
        )
        _add_collision_box_only(
            cluster_name + "_CapCollision_%s" % str(index),
            Vector3(
                x_value,
                top_y - GROUND_CAP_THICKNESS * 0.5,
                z_value
            ),
            Vector3(
                MOUNTAIN_CELL_SIZE,
                GROUND_CAP_THICKNESS,
                MOUNTAIN_CELL_SIZE
            )
        )


func _build_mountain_steps(
    start: Vector3,
    direction: Vector3,
    count: int,
    target_y: float
) -> void:
    for index in range(count):
        var progress := float(index + 1) / float(count)
        var top_y := target_y * progress
        var step_position := start + direction * float(index) * 2.1
        _add_solid_box(
            "MountainStep_%s_%s" % [str(start.x), str(index)],
            Vector3(
                step_position.x,
                top_y * 0.5,
                step_position.z
            ),
            Vector3(4.2, top_y, 5.0),
            STEP_COLOR
        )


func _build_houses_on_real_block_surfaces() -> void:
    var homes := [
        "building_home_A_red.gltf",
        "building_home_B_red.gltf",
        "building_home_A_blue.gltf",
        "building_home_B_blue.gltf",
        "building_home_A_yellow.gltf",
        "building_home_B_yellow.gltf",
    ]

    # Main road pads: subtle elevation but visibly made from green blocks.
    for z_value in [-30.0, -24.0, -8.0, 8.0, 24.0, 30.0]:
        _spawn_house_on_block_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(-10.0, 0.0, z_value),
            Vector3(0.0, 0.0, z_value),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35),
            0.65
        )
        _spawn_house_on_block_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(10.0, 0.0, z_value),
            Vector3(0.0, 0.0, z_value),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35),
            0.65
        )

    # Branch-road neighborhoods step upward toward the mountain ring.
    for x_value in [-30.0, -22.0, -14.0, 14.0, 22.0, 30.0]:
        var north_pad := _pad_surface_base_height(x_value)
        _spawn_house_on_block_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, -23.0),
            Vector3(x_value, 0.0, -16.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.15, 0.35),
            north_pad
        )
        _spawn_house_on_block_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, -9.0),
            Vector3(x_value, 0.0, -16.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.15, 0.35),
            north_pad
        )

        var south_pad := _pad_surface_base_height(x_value)
        _spawn_house_on_block_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, 7.0),
            Vector3(x_value, 0.0, 14.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.15, 0.35),
            south_pad
        )
        _spawn_house_on_block_pad(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, 21.0),
            Vector3(x_value, 0.0, 14.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.15, 0.35),
            south_pad
        )

    _spawn_house_on_block_pad(
        "building_tavern_red.gltf",
        Vector3(-16.0, 0.0, -4.0),
        Vector3(0.0, 0.0, -4.0),
        5.9,
        0.80
    )
    _spawn_house_on_block_pad(
        "building_market_red.gltf",
        Vector3(16.0, 0.0, -4.0),
        Vector3(0.0, 0.0, -4.0),
        5.6,
        0.80
    )
    _spawn_house_on_block_pad(
        "building_blacksmith_red.gltf",
        Vector3(-16.0, 0.0, 4.0),
        Vector3(0.0, 0.0, 4.0),
        5.9,
        0.80
    )
    _spawn_house_on_block_pad(
        "building_church_red.gltf",
        Vector3(16.0, 0.0, 4.0),
        Vector3(0.0, 0.0, 4.0),
        6.6,
        0.80
    )


func _pad_surface_base_height(x_value: float) -> float:
    if absf(x_value) >= 28.0:
        return 2.20
    if absf(x_value) >= 20.0:
        return 1.35
    return 0.70


func _spawn_house_on_block_pad(
    filename: String,
    base_position: Vector3,
    road_target: Vector3,
    target_height: float,
    core_top_y: float
) -> void:
    var surface_y := _build_house_block_pad(
        base_position,
        road_target,
        core_top_y
    )

    var house_position := Vector3(
        base_position.x,
        surface_y,
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
        _add_visual_box(
            "BuildingFallback",
            house_position + Vector3(0.0, target_height * 0.5, 0.0),
            Vector3(4.2, target_height, 4.0),
            Color("#D99A62")
        )

    _add_collision_box_only(
        "BuildingCollision",
        house_position + Vector3(0.0, 2.0, 0.0),
        Vector3(4.6, 4.0, 4.3)
    )


func _build_house_block_pad(
    base_position: Vector3,
    road_target: Vector3,
    core_top_y: float
) -> float:
    if core_top_y > 0.01:
        _add_solid_box(
            "HousePadCore",
            Vector3(
                base_position.x,
                core_top_y * 0.5,
                base_position.z
            ),
            Vector3(7.0, core_top_y, 7.0),
            CLIFF_COLOR
        )

    var surface_y := core_top_y + HOUSE_PAD_CAP_THICKNESS

    # 3x3 green Block Bits cap; the house is placed at this exact top Y.
    for x_offset in [-2.0, 0.0, 2.0]:
        for z_offset in [-2.0, 0.0, 2.0]:
            _place_green_box_fit(
                Vector3(
                    base_position.x + x_offset,
                    core_top_y,
                    base_position.z + z_offset
                ),
                Vector3(
                    ROAD_TILE_SIZE,
                    HOUSE_PAD_CAP_THICKNESS,
                    ROAD_TILE_SIZE
                )
            )

    _add_collision_box_only(
        "HousePadCapCollision",
        Vector3(
            base_position.x,
            core_top_y + HOUSE_PAD_CAP_THICKNESS * 0.5,
            base_position.z
        ),
        Vector3(6.0, HOUSE_PAD_CAP_THICKNESS, 6.0)
    )

    if surface_y > 0.85:
        _build_pad_steps(
            base_position,
            road_target,
            surface_y
        )

    return surface_y


func _build_pad_steps(
    pad_position: Vector3,
    road_target: Vector3,
    surface_y: float
) -> void:
    var direction := road_target - pad_position
    direction.y = 0.0
    if direction.length_squared() < 0.001:
        return
    direction = direction.normalized()

    var step_count := maxi(3, int(ceil(surface_y / 0.40)))
    for index in range(step_count):
        var progress := float(index + 1) / float(step_count)
        var top_y := surface_y * progress
        var distance := 4.4 + float(step_count - index) * 0.75
        var step_position := pad_position + direction * distance
        _add_solid_box(
            "HousePadStep",
            Vector3(
                step_position.x,
                top_y * 0.5,
                step_position.z
            ),
            Vector3(2.5, top_y, 2.2),
            STEP_COLOR
        )


func _build_resource_yard() -> void:
    var origin := Vector3(30.0, 0.0, -6.0)
    var surface_y := _build_house_block_pad(
        origin,
        Vector3(30.0, 0.0, -16.0),
        1.45
    )

    var props := [
        ["Wood_Log_Stack.gltf", Vector3(-2.1, 0.0, -2.0), 1.15],
        ["Wood_Planks_Stack_Medium.gltf", Vector3(1.5, 0.0, -2.0), 1.10],
        ["Stone_Chunks_Large.gltf", Vector3(2.0, 0.0, 1.6), 1.05],
        ["Stone_Bricks_Stack_Medium.gltf", Vector3(-2.0, 0.0, 1.5), 1.10],
        ["Pallet_Wood.gltf", Vector3(0.4, 0.0, 2.7), 1.05],
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
                surface_y + offset.y,
                origin.z + offset.z
            ),
            rng.randf_range(-18.0, 18.0),
            scale_value
        )

    _add_collision_box_only(
        "ResourceYardCollisionA",
        Vector3(origin.x - 1.8, surface_y + 0.8, origin.z - 1.5),
        Vector3(3.4, 1.6, 3.4)
    )
    _add_collision_box_only(
        "ResourceYardCollisionB",
        Vector3(origin.x + 2.0, surface_y + 0.8, origin.z + 1.2),
        Vector3(3.4, 1.6, 3.4)
    )


func _build_forest_reference_dressing() -> void:
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

    var clusters := [
        [Vector3(-38.0, 4.62, -35.0), 9.0, 9],
        [Vector3(34.0, 4.82, -35.0), 9.0, 9],
        [Vector3(-38.0, 4.42, 35.0), 9.0, 9],
        [Vector3(34.0, 4.72, 35.0), 9.0, 9],
        [Vector3(-44.0, 4.22, 0.0), 7.5, 7],
        [Vector3(44.0, 4.42, 0.0), 7.5, 7],
        [Vector3(-40.0, 8.52, -38.0), 6.5, 8],
        [Vector3(38.0, 8.82, -38.0), 6.5, 8],
        [Vector3(-40.0, 8.22, 38.0), 6.5, 8],
        [Vector3(38.0, 8.62, 38.0), 6.5, 8],
        [Vector3(-42.0, 12.32, -42.0), 4.0, 5],
        [Vector3(40.0, 12.62, 40.0), 4.0, 5],
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

    # Oversized Forest Nature rocks around cliff edges soften the square core
    # and produce the grey-rock / green-cap rhythm of the supplied reference.
    for edge in [
        Vector3(-34.0, 2.0, -28.0),
        Vector3(-30.0, 2.2, -39.0),
        Vector3(30.0, 2.2, -39.0),
        Vector3(39.0, 2.2, -28.0),
        Vector3(-39.0, 2.0, 28.0),
        Vector3(-30.0, 2.0, 39.0),
        Vector3(30.0, 2.1, 39.0),
        Vector3(39.0, 2.2, 28.0),
    ]:
        var rock_file: String = rock_files[
            rng.randi_range(0, rock_files.size() - 1)
        ]
        AssetVaultRuntime.instantiate_first_filename(
            self,
            rock_file,
            edge,
            rng.randf_range(0.0, 360.0),
            rng.randf_range(2.2, 3.3)
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
        var position := center + Vector3(
            rng.randf_range(-radius, radius),
            0.0,
            rng.randf_range(-radius, radius)
        )

        var tree_file: String = tree_files[
            rng.randi_range(0, tree_files.size() - 1)
        ]
        AssetVaultRuntime.instantiate_first_filename(
            self,
            tree_file,
            position,
            rng.randf_range(0.0, 360.0),
            rng.randf_range(1.10, 1.70)
        )

        if index % 2 == 0:
            var rock_file: String = rock_files[
                rng.randi_range(0, rock_files.size() - 1)
            ]
            AssetVaultRuntime.instantiate_first_filename(
                self,
                rock_file,
                position + Vector3(
                    rng.randf_range(-2.0, 2.0),
                    0.0,
                    rng.randf_range(-2.0, 2.0)
                ),
                rng.randf_range(0.0, 360.0),
                rng.randf_range(0.85, 1.50)
            )

        if index % 3 == 0:
            var bush_file: String = bush_files[
                rng.randi_range(0, bush_files.size() - 1)
            ]
            AssetVaultRuntime.instantiate_first_filename(
                self,
                bush_file,
                position + Vector3(
                    rng.randf_range(-1.8, 1.8),
                    0.0,
                    rng.randf_range(-1.8, 1.8)
                ),
                rng.randf_range(0.0, 360.0),
                rng.randf_range(0.80, 1.25)
            )

        if index % 2 == 1:
            var grass_file: String = grass_files[
                rng.randi_range(0, grass_files.size() - 1)
            ]
            AssetVaultRuntime.instantiate_first_filename(
                self,
                grass_file,
                position + Vector3(
                    rng.randf_range(-1.7, 1.7),
                    0.03,
                    rng.randf_range(-1.7, 1.7)
                ),
                rng.randf_range(0.0, 360.0),
                rng.randf_range(0.70, 1.0)
            )


func _build_skeletons() -> void:
    var positions := [
        Vector3(-44.0, 4.62, -10.0),
        Vector3(44.0, 4.42, 12.0),
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




func _build_training_skeleton() -> void:
    var player := get_node_or_null("Player") as CharacterBody3D
    if player == null:
        push_warning("PLAY-03: Player missing; Training Skeleton not spawned.")
        return

    var enemy := MiniUtopiaSkeletonEnemy.new()
    enemy.name = "TrainingSkeleton"
    enemy.position = Vector3(4.0, 0.45, 27.5)
    add_child(enemy)
    enemy.configure(player, "training_skeleton_01")

    print(
        "PLAY-03 Training Skeleton ready near spawn · "
        + "F / Left Click to attack."
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


func _place_green_box_fit(bottom_position: Vector3, size: Vector3) -> void:
    if not green_block_asset_id.is_empty():
        var node := AssetVaultRuntime.instantiate_by_id_box_fit(
            self,
            green_block_asset_id,
            bottom_position,
            size
        )
        if node != null:
            return

    _add_visual_box(
        "GreenBlockFallback",
        bottom_position + Vector3(0.0, size.y * 0.5, 0.0),
        size,
        GREEN_FALLBACK_COLOR
    )


func _place_yellow_box_fit(bottom_position: Vector3, size: Vector3) -> void:
    if not yellow_block_asset_id.is_empty():
        var node := AssetVaultRuntime.instantiate_by_id_box_fit(
            self,
            yellow_block_asset_id,
            bottom_position,
            size
        )
        if node != null:
            return

    _add_visual_box(
        "YellowBlockFallback",
        bottom_position + Vector3(0.0, size.y * 0.5, 0.0),
        size,
        YELLOW_FALLBACK_COLOR
    )


func _build_world_boundary() -> void:
    _add_collision_box_only(
        "BoundaryWest",
        Vector3(-49.5, 7.0, 0.0),
        Vector3(1.0, 14.0, WORLD_SIZE)
    )
    _add_collision_box_only(
        "BoundaryEast",
        Vector3(49.5, 7.0, 0.0),
        Vector3(1.0, 14.0, WORLD_SIZE)
    )
    _add_collision_box_only(
        "BoundaryNorth",
        Vector3(0.0, 7.0, -49.5),
        Vector3(WORLD_SIZE, 14.0, 1.0)
    )
    _add_collision_box_only(
        "BoundarySouth",
        Vector3(0.0, 7.0, 49.5),
        Vector3(WORLD_SIZE, 14.0, 1.0)
    )


func _build_hud() -> void:
    var layer := CanvasLayer.new()
    add_child(layer)

    var panel := ColorRect.new()
    panel.position = Vector2(18.0, 18.0)
    panel.size = Vector2(610.0, 112.0)
    panel.color = Color(0.035, 0.07, 0.085, 0.76)
    layer.add_child(panel)

    var label := Label.new()
    label.position = Vector2(16.0, 10.0)
    label.size = Vector2(580.0, 94.0)
    label.text = (
        "新手村 · 100×100 v0.3\n"
        + "SOLID aligned Block Bits ground + visible yellow road\n"
        + "houses sit on exact green-block top surfaces · irregular layered cliffs\n"
        + "Forest Nature dressing · Training Skeleton combat\n"
        + "F / Left Click · Attack · defeat Skeleton → Bone Buckler"
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

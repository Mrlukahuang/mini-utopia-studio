extends Node3D

const WORLD_SIZE := 100.0
const MAP_HALF := 50.0
const ROAD_BLOCK_SIZE := 2.0
const MAIN_ROAD_WIDTH_BLOCKS := 3
const BRANCH_ROAD_WIDTH_BLOCKS := 2
const HOUSE_TARGET_HEIGHT := 4.8
const SKELETON_COUNT := 2

const GRASS_COLOR := Color("#79C95A")
const GRASS_CAP_COLOR := Color("#8EDC62")
const CLIFF_COLOR := Color("#7E8790")
const DIRT_COLOR := Color("#B87943")
const PLAZA_COLOR := Color("#D4B174")

var rng := RandomNumberGenerator.new()
var road_asset_id := ""
var skeleton_asset_id := ""


func _ready() -> void:
    rng.seed = 100173
    _setup_environment()
    _resolve_vault_assets()
    _build_terrain()
    _build_roads()
    _build_central_plaza()
    _build_houses()
    _build_resource_yard()
    _build_forest_nature()
    _build_skeletons()
    _build_world_boundary()
    _build_hud()


func _setup_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color("#8FCBE8")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#FFE3B0")
    env.ambient_light_energy = 0.34
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.tonemap_exposure = 0.92
    env.fog_enabled = true
    env.fog_light_color = Color("#BDE0EE")
    env.fog_light_energy = 0.16
    env.fog_density = 0.0035
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-48.0, -36.0, 0.0)
    sun.light_color = Color("#FFE0A1")
    sun.light_energy = 0.82
    sun.shadow_enabled = true
    sun.shadow_opacity = 0.72
    add_child(sun)

    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-24.0, 145.0, 0.0)
    fill.light_color = Color("#A8D9EE")
    fill.light_energy = 0.08
    fill.shadow_enabled = false
    add_child(fill)


func _resolve_vault_assets() -> void:
    if not AssetVaultRuntime.is_installed():
        push_error("Newbie Village requires the Full Asset Vault.")
        return

    var road_entry := AssetVaultRuntime.first_entry_matching(
        ["block"],
        ["dirt"]
    )
    if road_entry.is_empty():
        road_entry = AssetVaultRuntime.first_entry_matching(
            ["block"],
            ["soil"]
        )
    if not road_entry.is_empty():
        road_asset_id = String(road_entry.get("id", ""))
    else:
        push_warning(
            "No Block Bits dirt/soil asset found; using solid dirt-block fallback."
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


func _build_terrain() -> void:
    # Broad, solid valley floor: deliberately rectangular / organic in massing,
    # never a repeated hex-grid terrain language.
    _add_solid_box(
        "ValleyFloor",
        Vector3(0.0, -1.0, 0.0),
        Vector3(WORLD_SIZE, 2.0, WORLD_SIZE),
        GRASS_COLOR
    )

    # Layered rock shelves with green caps create the enclosing valley.
    _add_terrace("WestShelf", Vector2(-43.0, 0.0), Vector2(14.0, 100.0), 3.0)
    _add_terrace("EastShelf", Vector2(43.0, 0.0), Vector2(14.0, 100.0), 4.0)
    _add_terrace("NorthShelf", Vector2(0.0, -43.0), Vector2(72.0, 14.0), 4.0)
    _add_terrace("SouthShelf", Vector2(0.0, 43.0), Vector2(72.0, 14.0), 3.0)

    # Two stronger skyline masses / lookout destinations.
    _add_terrace(
        "NorthWestLookout",
        Vector2(-36.5, -36.5),
        Vector2(17.0, 17.0),
        6.0
    )
    _add_terrace(
        "SouthEastLookout",
        Vector2(36.5, 36.5),
        Vector2(17.0, 17.0),
        6.5
    )

    # Smaller layered shoulders break the square silhouette and add depth.
    _add_terrace(
        "NorthEastShoulder",
        Vector2(30.0, -38.5),
        Vector2(18.0, 12.0),
        5.0
    )
    _add_terrace(
        "SouthWestShoulder",
        Vector2(-30.0, 38.5),
        Vector2(18.0, 12.0),
        4.5
    )

    # Walkable step routes to two outer exploration shelves.
    _build_grass_steps(Vector3(-31.0, 0.0, -27.0), Vector3(-1.0, 0.0, 0.0), 5, 0.62)
    _build_grass_steps(Vector3(31.0, 0.0, 27.0), Vector3(1.0, 0.0, 0.0), 6, 0.62)


func _add_terrace(
    terrain_name: String,
    center: Vector2,
    size: Vector2,
    height: float
) -> void:
    _add_solid_box(
        terrain_name + "_Cliff",
        Vector3(center.x, height * 0.5, center.y),
        Vector3(size.x, height, size.y),
        CLIFF_COLOR
    )
    _add_solid_box(
        terrain_name + "_GrassCap",
        Vector3(center.x, height + 0.18, center.y),
        Vector3(size.x, 0.36, size.y),
        GRASS_CAP_COLOR
    )


func _build_grass_steps(
    start: Vector3,
    direction: Vector3,
    count: int,
    rise: float
) -> void:
    for index in range(count):
        var top_height := rise * float(index + 1)
        var center := start + direction * float(index) * 2.2
        center.y = top_height * 0.5
        _add_solid_box(
            "ExplorationStep_%s_%s" % [str(start.x), str(index)],
            center,
            Vector3(4.6, top_height, 5.4),
            GRASS_COLOR
        )


func _build_roads() -> void:
    # Latest locked circulation: one N-S main road plus two E-W branch roads.
    for z_value in range(-38, 39, int(ROAD_BLOCK_SIZE)):
        for lane in range(-1, 2):
            _place_dirt_block(
                Vector3(
                    float(lane) * ROAD_BLOCK_SIZE,
                    0.0,
                    float(z_value)
                )
            )

    var branch_rows := [-16.0, 14.0]
    for branch_z in branch_rows:
        for x_value in range(-34, 35, int(ROAD_BLOCK_SIZE)):
            var offsets := [-1.0, 1.0]
            for z_offset in offsets:
                _place_dirt_block(
                    Vector3(
                        float(x_value),
                        0.0,
                        branch_z + z_offset
                    )
                )


func _place_dirt_block(world_position: Vector3) -> void:
    if not road_asset_id.is_empty():
        # Block Bits cubes are intentionally sunk into the valley floor so the
        # road reads as a paved dirt strip rather than a tall wall of cubes.
        var instance := AssetVaultRuntime.instantiate_by_id(
            self,
            road_asset_id,
            world_position + Vector3(0.0, -0.92, 0.0),
            0.0,
            ROAD_BLOCK_SIZE
        )
        if instance != null:
            return

    _add_visual_box(
        "DirtRoadFallback",
        world_position + Vector3(0.0, 0.06, 0.0),
        Vector3(ROAD_BLOCK_SIZE, 0.12, ROAD_BLOCK_SIZE),
        DIRT_COLOR
    )


func _build_central_plaza() -> void:
    _add_solid_box(
        "CentralPlaza",
        Vector3(0.0, 0.10, 0.0),
        Vector3(13.0, 0.20, 13.0),
        PLAZA_COLOR
    )

    # A simple readable landmark until a later interactive village centerpiece.
    _add_solid_box(
        "PlazaPedestal",
        Vector3(0.0, 0.45, 0.0),
        Vector3(2.8, 0.7, 2.8),
        Color("#B88F5A")
    )


func _build_houses() -> void:
    var homes := [
        "building_home_A_red.gltf",
        "building_home_B_red.gltf",
        "building_home_A_blue.gltf",
        "building_home_B_blue.gltf",
        "building_home_A_yellow.gltf",
        "building_home_B_yellow.gltf",
    ]

    var main_z := [-30.0, -24.0, -8.0, 0.0, 24.0, 30.0]
    for z_value in main_z:
        _spawn_building(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(-8.5, 0.0, z_value),
            Vector3(0.0, 0.0, z_value),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.25, 0.45)
        )
        _spawn_building(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(8.5, 0.0, z_value),
            Vector3(0.0, 0.0, z_value),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.25, 0.45)
        )

    var branch_x_a := [-30.0, -22.0, -14.0, 14.0, 22.0]
    for x_value in branch_x_a:
        _spawn_building(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, -22.0),
            Vector3(x_value, 0.0, -16.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35)
        )
        _spawn_building(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, -10.0),
            Vector3(x_value, 0.0, -16.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35)
        )

    var branch_x_b := [-30.0, -22.0, -14.0, 14.0, 22.0, 30.0]
    for x_value in branch_x_b:
        _spawn_building(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, 8.0),
            Vector3(x_value, 0.0, 14.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35)
        )
        _spawn_building(
            homes[rng.randi_range(0, homes.size() - 1)],
            Vector3(x_value, 0.0, 20.0),
            Vector3(x_value, 0.0, 14.0),
            HOUSE_TARGET_HEIGHT + rng.randf_range(-0.20, 0.35)
        )

    # Landmark buildings make the road core read as a village, not a housing grid.
    _spawn_building(
        "building_tavern_red.gltf",
        Vector3(-14.0, 0.0, -3.5),
        Vector3(0.0, 0.0, -3.5),
        5.6
    )
    _spawn_building(
        "building_market_red.gltf",
        Vector3(14.0, 0.0, -3.5),
        Vector3(0.0, 0.0, -3.5),
        5.2
    )
    _spawn_building(
        "building_blacksmith_red.gltf",
        Vector3(-14.0, 0.0, 3.5),
        Vector3(0.0, 0.0, 3.5),
        5.6
    )
    _spawn_building(
        "building_church_red.gltf",
        Vector3(14.0, 0.0, 3.5),
        Vector3(0.0, 0.0, 3.5),
        6.3
    )


func _spawn_building(
    filename: String,
    world_position: Vector3,
    road_target: Vector3,
    target_height: float
) -> void:
    var yaw := _yaw_toward(world_position, road_target) + 180.0
    var node := AssetVaultRuntime.instantiate_first_filename(
        self,
        filename,
        world_position,
        yaw,
        1.0,
        target_height
    )
    if node == null:
        push_warning("Missing village building asset: " + filename)
        _add_visual_box(
            "BuildingFallback",
            world_position + Vector3(0.0, target_height * 0.5, 0.0),
            Vector3(4.0, target_height, 4.0),
            Color("#D99A62")
        )

    _add_collision_box_only(
        "BuildingCollision",
        world_position + Vector3(0.0, 1.9, 0.0),
        Vector3(4.2, 3.8, 4.0)
    )


func _build_resource_yard() -> void:
    var origin := Vector3(30.0, 0.0, -16.0)
    var props := [
        ["Wood_Log_Stack.gltf", Vector3(-2.8, 0.0, -3.0), 1.15],
        ["Wood_Planks_Stack_Medium.gltf", Vector3(1.0, 0.0, -3.2), 1.10],
        ["Stone_Chunks_Large.gltf", Vector3(3.0, 0.0, 0.2), 1.05],
        ["Stone_Bricks_Stack_Medium.gltf", Vector3(-2.6, 0.0, 1.0), 1.10],
        ["Pallet_Wood.gltf", Vector3(0.8, 0.0, 3.0), 1.05],
    ]

    for item in props:
        var filename := String(item[0])
        var offset: Vector3 = item[1]
        var scale_value := float(item[2])
        AssetVaultRuntime.instantiate_first_filename(
            self,
            filename,
            origin + offset,
            rng.randf_range(-22.0, 22.0),
            scale_value
        )

    _add_collision_box_only(
        "ResourceYardCollisionA",
        origin + Vector3(-2.0, 0.8, -2.0),
        Vector3(3.2, 1.6, 3.2)
    )
    _add_collision_box_only(
        "ResourceYardCollisionB",
        origin + Vector3(2.4, 0.8, 0.5),
        Vector3(3.2, 1.6, 3.2)
    )


func _build_forest_nature() -> void:
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

    # Dense natural ring: Forest Nature Pack visually owns the valley edges.
    for index in range(95):
        var point := _random_outer_point()
        var y := _surface_y(point.x, point.y)
        var world_position := Vector3(point.x, y, point.y)

        var tree_file: String = tree_files[
            rng.randi_range(0, tree_files.size() - 1)
        ]
        AssetVaultRuntime.instantiate_first_filename(
            self,
            tree_file,
            world_position,
            rng.randf_range(0.0, 360.0),
            rng.randf_range(1.0, 1.55)
        )

        if index % 2 == 0:
            var rock_file: String = rock_files[
                rng.randi_range(0, rock_files.size() - 1)
            ]
            AssetVaultRuntime.instantiate_first_filename(
                self,
                rock_file,
                world_position + Vector3(
                    rng.randf_range(-2.2, 2.2),
                    0.0,
                    rng.randf_range(-2.2, 2.2)
                ),
                rng.randf_range(0.0, 360.0),
                rng.randf_range(0.65, 1.35)
            )

        if index % 3 == 0:
            var bush_file: String = bush_files[
                rng.randi_range(0, bush_files.size() - 1)
            ]
            AssetVaultRuntime.instantiate_first_filename(
                self,
                bush_file,
                world_position + Vector3(
                    rng.randf_range(-2.5, 2.5),
                    0.0,
                    rng.randf_range(-2.5, 2.5)
                ),
                rng.randf_range(0.0, 360.0),
                rng.randf_range(0.75, 1.2)
            )

    # Smaller village-side green pockets soften the built area without blocking roads.
    var pocket_points := [
        Vector3(-18.0, 0.0, -31.0),
        Vector3(18.0, 0.0, -31.0),
        Vector3(-27.0, 0.0, -3.0),
        Vector3(27.0, 0.0, 3.0),
        Vector3(-18.0, 0.0, 29.0),
        Vector3(18.0, 0.0, 29.0),
        Vector3(-31.0, 0.0, 25.0),
        Vector3(31.0, 0.0, -27.0),
    ]

    for point in pocket_points:
        for offset_index in range(3):
            var grass_file: String = grass_files[
                rng.randi_range(0, grass_files.size() - 1)
            ]
            AssetVaultRuntime.instantiate_first_filename(
                self,
                grass_file,
                point + Vector3(
                    rng.randf_range(-1.8, 1.8),
                    0.03,
                    rng.randf_range(-1.8, 1.8)
                ),
                rng.randf_range(0.0, 360.0),
                rng.randf_range(0.65, 1.0)
            )

        var bush_file: String = bush_files[
            rng.randi_range(0, bush_files.size() - 1)
        ]
        AssetVaultRuntime.instantiate_first_filename(
            self,
            bush_file,
            point,
            rng.randf_range(0.0, 360.0),
            rng.randf_range(0.8, 1.15)
        )


func _random_outer_point() -> Vector2:
    var side := rng.randi_range(0, 3)
    var edge := rng.randf_range(35.5, 47.0)
    var along := rng.randf_range(-46.0, 46.0)

    if side == 0:
        return Vector2(-edge, along)
    if side == 1:
        return Vector2(edge, along)
    if side == 2:
        return Vector2(along, -edge)
    return Vector2(along, edge)


func _surface_y(x_value: float, z_value: float) -> float:
    if x_value < -31.0 and z_value < -31.0:
        return 6.36
    if x_value > 31.0 and z_value > 31.0:
        return 6.86
    if x_value > 22.0 and z_value < -32.5:
        return 5.36
    if x_value < -22.0 and z_value > 32.5:
        return 4.86
    if x_value <= -36.0:
        return 3.36
    if x_value >= 36.0:
        return 4.36
    if z_value <= -36.0:
        return 4.36
    if z_value >= 36.0:
        return 3.36
    return 0.0


func _build_skeletons() -> void:
    var positions := [
        Vector3(-39.0, _surface_y(-39.0, -24.0), -24.0),
        Vector3(39.0, _surface_y(39.0, 26.0), 26.0),
    ]

    for index in range(SKELETON_COUNT):
        var position: Vector3 = positions[index]
        var skeleton: Node3D = null
        if not skeleton_asset_id.is_empty():
            skeleton = AssetVaultRuntime.instantiate_by_id(
                self,
                skeleton_asset_id,
                position,
                180.0 if index == 0 else 15.0,
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
        Vector3(-49.5, 3.0, 0.0),
        Vector3(1.0, 6.0, WORLD_SIZE)
    )
    _add_collision_box_only(
        "BoundaryEast",
        Vector3(49.5, 3.0, 0.0),
        Vector3(1.0, 6.0, WORLD_SIZE)
    )
    _add_collision_box_only(
        "BoundaryNorth",
        Vector3(0.0, 3.0, -49.5),
        Vector3(WORLD_SIZE, 6.0, 1.0)
    )
    _add_collision_box_only(
        "BoundarySouth",
        Vector3(0.0, 3.0, 49.5),
        Vector3(WORLD_SIZE, 6.0, 1.0)
    )


func _build_hud() -> void:
    var layer := CanvasLayer.new()
    add_child(layer)

    var panel := ColorRect.new()
    panel.position = Vector2(18.0, 18.0)
    panel.size = Vector2(610.0, 112.0)
    panel.color = Color(0.035, 0.07, 0.085, 0.78)
    layer.add_child(panel)

    var label := Label.new()
    label.position = Vector2(18.0, 12.0)
    label.size = Vector2(580.0, 92.0)
    label.text = (
        "新手村 · 100×100 v0.1\n"
        + "Forest Nature valley · Block Bits dirt road · Resource Bits yard\n"
        + "1 main road (3 blocks) + 2 horizontal branches (2 blocks) · 2 skeletons\n"
        + "WASD / Shift / Space"
    )
    label.add_theme_font_size_override("font_size", 17)
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

extends Node3D

# Eight imported, unmodified CC0 KayKit houses; instances repeat in four
# real streets. Preloads guarantee inclusion in the exported Web PCK.
const KAYKIT_HOUSES := [
    preload("res://assets/kaykit/medieval/building_home_A_blue.gltf"),
    preload("res://assets/kaykit/medieval/building_home_B_blue.gltf"),
    preload("res://assets/kaykit/medieval/building_home_A_green.gltf"),
    preload("res://assets/kaykit/medieval/building_home_B_green.gltf"),
    preload("res://assets/kaykit/medieval/building_home_A_red.gltf"),
    preload("res://assets/kaykit/medieval/building_home_B_red.gltf"),
    preload("res://assets/kaykit/medieval/building_home_A_yellow.gltf"),
    preload("res://assets/kaykit/medieval/building_home_B_yellow.gltf"),
    preload("res://assets/kaykit/medieval/building_tavern_blue.gltf"),
    preload("res://assets/kaykit/medieval/building_church_blue.gltf"),
    preload("res://assets/kaykit/medieval/building_market_blue.gltf"),
    preload("res://assets/kaykit/medieval/building_windmill_blue.gltf"),
    preload("res://assets/kaykit/medieval/building_blacksmith_blue.gltf"),
    preload("res://assets/kaykit/medieval/building_tower_A_blue.gltf"),
    preload("res://assets/kaykit/medieval/building_lumbermill_blue.gltf"),
    preload("res://assets/kaykit/medieval/building_well_blue.gltf"),
]

var _village_previous_web_fps := -1
var _previous_scale := 1.0
var _previous_msaa := Viewport.MSAA_DISABLED
var _static_visuals: Array[Dictionary] = []
var _static_batches: Array[MultiMeshInstance3D] = []
var _mesh_pool: Dictionary = {}
var _mat_pool: Dictionary = {}
var _villagers: Array[Node3D] = []
var _lod_elapsed := 0.0
var _fps_elapsed := 0.0
var _perf_hold_elapsed := 0.0
var _perf_pressing := false
var _perf_toggled_this_hold := false
var _perf_badge: Label
var _overview_was_on := false
var gate_unlocked := false
var gate_label: Label3D

var palette = {
    "grass": Color("#6E9F61"),
    "grass2": Color("#86B970"),
    "grass_dark": Color("#527C4C"),
    "path": Color("#C9895F"),
    "path_light": Color("#E4B27C"),
    "wood": Color("#7A4937"),
    "wood_light": Color("#A96A45"),
    "cream": Color("#EBC9A4"),
    "cream_light": Color("#F4DFC1"),
    "pink": Color("#C96D73"),
    "mint": Color("#6FAE90"),
    "lavender": Color("#8E78A9"),
    "leaf": Color("#547D45"),
    "leaf2": Color("#7DA258"),
    "stone": Color("#AAA09A"),
    "mushroom_red": Color("#C9563F"),
    "mushroom_orange": Color("#D9824E"),
    "mushroom_spot": Color("#F4DFC1"),
}

func _ready() -> void:
    # A 30 FPS cap guaranteed <=30 even on powerful iPads. Allow 60, while
    # using lower-cost Web rendering. Restore all global settings on exit.
    if OS.has_feature("web"):
        _village_previous_web_fps = Engine.max_fps
        Engine.max_fps = 60
        var viewport := get_viewport()
        _previous_scale = viewport.scaling_3d_scale
        _previous_msaa = viewport.msaa_3d
        viewport.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
        viewport.scaling_3d_scale = 0.75
        viewport.msaa_3d = Viewport.MSAA_DISABLED
        viewport.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
        RenderingServer.directional_shadow_atlas_set_size(1024, true)
    _setup_environment()
    _build_ground()
    _build_path()
    _build_village()
    _build_forest()
    _build_kaykit_villagers()
    _build_storybook_dressing()
    _build_locked_gate()
    _batch_static_visuals()
    _install_performance_badge()
    _update_villager_lod()
    _apply_shared_theme_to_hud()
    var creator_button := get_node_or_null("HUD/OpenCreatorButton") as Button
    if creator_button != null:
        creator_button.pressed.connect(_open_character_creator)

    var director_button := get_node_or_null("HUD/OpenDirectorButton") as Button
    if director_button != null:
        var selection := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
        director_button.disabled = (
            selection == null or selection.active_play_session().is_empty()
        )
        director_button.pressed.connect(_open_family_director)


# Lane B owns project-wide Theme and the HUD scene; Lane A only removes
# legacy local overrides so the shared pastel buttons/labels inherit it.
# Deliberately do not invent palette colors, fonts or StyleBoxes here.
func _apply_shared_theme_to_hud() -> void:
    for node_path in [
        "HUD/Panel/Title", "HUD/Panel/Help",
        "HUD/OpenCreatorButton", "HUD/OpenDirectorButton",
    ]:
        var control := get_node_or_null(node_path) as Control
        if control == null:
            continue
        control.remove_theme_font_override("font")
        control.remove_theme_font_size_override("font_size")
        control.remove_theme_color_override("font_color")
    var title := get_node_or_null("HUD/Panel/Title") as Label
    if title != null:
        title.text = "欢迎来到迷你乌托邦！"
    var help := get_node_or_null("HUD/Panel/Help") as Label
    if help != null:
        help.text = "创造英雄 · 探索村庄 · 拍一部小电影"



func _install_performance_badge() -> void:
    var hud := get_node_or_null("HUD") as CanvasLayer
    if hud == null:
        return
    _perf_badge = Label.new()
    _perf_badge.name = "LaneAPerformanceBadge"
    _perf_badge.position = Vector2(460, 9)
    _perf_badge.mouse_filter = Control.MOUSE_FILTER_IGNORE
    _perf_badge.text = "FPS -- | Draw --"
    _perf_badge.visible = false
    hud.add_child(_perf_badge)


func _input(event: InputEvent) -> void:
    # Hidden until a deliberate 1.2s hold on the existing top-left Logo.
    # Both touchscreen and desktop use the same non-invasive diagnostic.
    if event is InputEventScreenTouch:
        var touch := event as InputEventScreenTouch
        if touch.pressed and touch.position.x < 160.0 and touch.position.y < 164.0:
            _perf_pressing = true
            _perf_toggled_this_hold = false
            _perf_hold_elapsed = 0.0
        elif not touch.pressed:
            _perf_pressing = false
    elif event is InputEventMouseButton:
        var mouse := event as InputEventMouseButton
        if mouse.button_index == MOUSE_BUTTON_LEFT:
            if mouse.pressed and mouse.position.x < 160.0 and mouse.position.y < 164.0:
                _perf_pressing = true
                _perf_toggled_this_hold = false
                _perf_hold_elapsed = 0.0
            elif not mouse.pressed:
                _perf_pressing = false


func _toggle_performance_badge() -> void:
    if _perf_badge != null:
        _perf_badge.visible = not _perf_badge.visible


func _tick_performance_badge(delta: float) -> void:
    if _perf_pressing and not _perf_toggled_this_hold:
        _perf_hold_elapsed += delta
        if _perf_hold_elapsed >= 1.2:
            _perf_toggled_this_hold = true
            _toggle_performance_badge()
    if _perf_badge == null or not _perf_badge.visible:
        return
    _fps_elapsed += delta
    if _fps_elapsed < 0.5:
        return
    _fps_elapsed = 0.0
    var frames := float(Performance.get_monitor(Performance.TIME_FPS))
    var draw := int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
    _perf_badge.text = "FPS %.0f  |  Draw %s" % [frames, str(draw) if draw > 0 else "--"]


func _update_villager_lod() -> void:
    var player := get_node_or_null("Player") as Node3D
    var cam := get_viewport().get_camera_3d()
    if player == null or cam == null:
        return
    for npc in _villagers:
        if not is_instance_valid(npc):
            continue
        var distance_to_child := npc.global_position.distance_to(player.global_position)
        var on_screen := cam.is_position_in_frustum(npc.global_position + Vector3.UP)
        npc.set_performance_lod(distance_to_child, on_screen)


func _set_overview_visibility() -> void:
    var camera_rig := get_node_or_null("CameraRig")
    if camera_rig == null:
        return
    var overhead: bool = camera_rig.get("distance") > 20.0
    if overhead == _overview_was_on:
        return
    _overview_was_on = overhead
    # Keep the CI's overhead whole-village image complete; normal iPad camera
    # can cheaply clip distant batches behind a little pastel fog.
    for batch in _static_batches:
        if is_instance_valid(batch):
            batch.visibility_range_end = 0.0 if overhead else 65.0


func _exit_tree() -> void:
    if _village_previous_web_fps >= 0:
        Engine.max_fps = _village_previous_web_fps
        get_viewport().scaling_3d_scale = _previous_scale
        get_viewport().msaa_3d = _previous_msaa
        RenderingServer.directional_shadow_atlas_set_size(2048, true)


func _open_family_director() -> void:
    var selection := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if selection == null or selection.active_play_session().is_empty():
        return
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    get_tree().change_scene_to_file("res://scenes/director_stage.tscn")


func _open_character_creator() -> void:
    # A child never needs to open the Godot Editor or Streamlit to create.
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    get_tree().change_scene_to_file("res://scenes/family_hero_library.tscn")


func _process(delta: float) -> void:
    # Fifteen bones/collision actors are examined once per 0.25s, not every
    # actor scanning every other actor on each physics tick.
    _lod_elapsed += delta
    if _lod_elapsed >= 0.25:
        _lod_elapsed = 0.0
        _update_villager_lod()
    _tick_performance_badge(delta)
    _set_overview_visibility()
    if gate_unlocked or gate_label == null:
        return

    var player := get_node_or_null("Player") as Node3D
    if player == null:
        return

    var gate_pos := Vector3(0, 0, -31)
    var distance := Vector2(player.global_position.x, player.global_position.z).distance_to(
        Vector2(gate_pos.x, gate_pos.z)
    )
    if distance <= 6.0:
        gate_label.text = "🔓 PRESS E\nCloud Whale District"
        if Input.is_action_just_pressed("interact"):
            _unlock_gate()
    else:
        gate_label.text = "🔒 NEW WORLD\nCloud Whale District"

func _unlock_gate() -> void:
    gate_unlocked = true
    var barrier := get_node_or_null("LockedBarrier")
    if barrier:
        barrier.queue_free()
    var collision := get_node_or_null("LockedBarrierCollision")
    if collision:
        collision.queue_free()
    if gate_label:
        gate_label.text = "✨ ZONE 01 UNLOCKED\nCloud Whale District"

func _mat(color: Color, roughness := 0.86) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = color
    m.roughness = roughness
    return m

func _box(name: String, pos: Vector3, size: Vector3, color: Color, collision := false) -> MeshInstance3D:
    var mesh := BoxMesh.new()
    mesh.size = size
    var node := MeshInstance3D.new()
    node.name = name
    node.mesh = mesh
    node.material_override = _mat(color)
    node.position = pos
    add_child(node)
    if collision:
        var body := StaticBody3D.new()
        body.name = name + "Collision"
        var shape := CollisionShape3D.new()
        var box := BoxShape3D.new()
        box.size = size
        shape.shape = box
        body.position = pos
        body.add_child(shape)
        add_child(body)
    return node

func _sphere(name: String, pos: Vector3, radius: float, color: Color, squash := Vector3.ONE) -> MeshInstance3D:
    var mesh := SphereMesh.new()
    mesh.radius = radius
    mesh.height = radius * 2.0
    var node := MeshInstance3D.new()
    node.name = name
    node.mesh = mesh
    node.material_override = _mat(color)
    node.position = pos
    node.scale = squash
    add_child(node)
    return node

func _cylinder(name: String, pos: Vector3, radius: float, height: float, color: Color, collision := false) -> MeshInstance3D:
    var mesh := CylinderMesh.new()
    mesh.top_radius = radius
    mesh.bottom_radius = radius * 1.08
    mesh.height = height
    var node := MeshInstance3D.new()
    node.name = name
    node.mesh = mesh
    node.material_override = _mat(color)
    node.position = pos
    add_child(node)
    if collision:
        var body := StaticBody3D.new()
        var shape := CollisionShape3D.new()
        var cyl := CylinderShape3D.new()
        cyl.radius = radius
        cyl.height = height
        shape.shape = cyl
        body.position = pos
        body.add_child(shape)
        add_child(body)
    return node

func _setup_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color("#88BBC4")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#E7C8A4")
    env.ambient_light_energy = 0.34
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.fog_enabled = true
    env.fog_light_color = Color("#B8CFCA")
    env.fog_light_energy = 0.34
    env.fog_density = 0.012 if OS.has_feature("web") else 0.004
    env.ssao_enabled = false
    env.glow_enabled = false
    env.ssil_enabled = false
    env.ssr_enabled = false
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-48, -38, 0)
    sun.light_color = Color("#F7D6A5")
    sun.light_energy = 0.72
    sun.shadow_enabled = true
    # One shadow frustum on Web avoids multiplying the draw cost of 20 real
    # buildings and 15 skinned KayKit villagers. Keep physical shadows.
    if OS.has_feature("web"):
        sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
    sun.directional_shadow_max_distance = 38.0 if OS.has_feature("web") else 75.0
    sun.shadow_opacity = 0.65
    add_child(sun)

func _build_ground() -> void:
    _box("VillageGround", Vector3(0, -0.55, 0), Vector3(70, 1, 70), palette.grass, true)
    for p in [
        Vector3(-20,0,18), Vector3(22,0,-15), Vector3(-25,0,-20),
        Vector3(25,0,20), Vector3(0,0,-34)
    ]:
        _sphere("Hill", p + Vector3(0,-1.2,0), 8.0, palette.grass2, Vector3(1.8,0.55,1.4))
    _sphere("VillageMound", Vector3(0,-1.0,-12), 12.0, palette.grass_dark, Vector3(1.2,0.12,0.85))

func _build_path() -> void:
    for i in range(-10, 12):
        var x := sin(float(i) * 0.42) * 1.3
        var width := 0.82 if i % 2 == 0 else 0.68
        _cylinder(
            "PathStone",
            Vector3(x,0.02,float(i)*1.55),
            width,
            0.12,
            palette.path_light if i % 3 == 0 else palette.path
        )

func _build_village() -> void:
    _build_kaykit_houses()

    _cylinder("FountainBase", Vector3(0,0.25,-10), 2.2, 0.5, palette.stone, true)
    _cylinder("FountainStem", Vector3(0,1.0,-10), 0.35, 1.5, palette.cream)
    _sphere("FountainBubble", Vector3(0,2.0,-10), 0.7, Color("#72B7C9"))
    _mushroom(Vector3(-4.2,0,-11.5), 0.65, palette.mushroom_red)
    _mushroom(Vector3(4.1,0,-12.0), 0.55, palette.mushroom_orange)

func _build_kaykit_houses() -> void:
    # Twenty real KayKit buildings with walkable 6–10m gaps around the
    # existing central stone path. All use StaticBody3D, not decorative meshes
    # or post-hoc collision counts. Never place a house at the player spawn.
    var plot_index := 0
    for z in [-26.0, -18.0, -10.0, -2.0, 6.0]:
        for x in [-23.0, -15.0, 15.0, 23.0]:
            var house := StaticBody3D.new()
            house.name = "KayKitHouse%02d" % plot_index
            house.position = Vector3(x, 0.0, z)
            house.add_to_group("kaykit_village_house")
            add_child(house)
            var visual := (KAYKIT_HOUSES[plot_index % KAYKIT_HOUSES.size()] as PackedScene).instantiate() as Node3D
            if visual == null:
                push_error("KayKit building failed to load: " + str(plot_index))
                continue
            visual.name = "OfficialKayKitBuilding"
            house.set_meta("kaykit_source_model", plot_index % KAYKIT_HOUSES.size())
            visual.scale = Vector3.ONE * 4.8
            visual.rotation_degrees.y = 180.0 if x < 0.0 else 0.0
            house.add_child(visual)
            var collision := CollisionShape3D.new()
            collision.name = "CollisionShape3D"
            # Official KayKit glTF mesh extents after the 4.8x instance scale:
            # home A: 3.81 x 4.46 x 4.10 m; home B: 4.20 x 6.14 x 5.27 m.
            # Both collider types cover the complete visible building, including
            # the taller B roof and its deeper front/back walls.
            var type_index: int = plot_index % KAYKIT_HOUSES.size()
            var is_home_b: bool = type_index in [1, 3, 5, 7]
            collision.position.y = 3.15 if is_home_b else 2.30
            var shape := BoxShape3D.new()
            if type_index >= 8:
                # Full-height blockers for the real market, windmill and tower meshes.
                shape.size = Vector3(7.8, 11.0, 7.8)
                collision.position.y = 5.5
            else:
                shape.size = Vector3(4.5, 6.3, 5.6) if is_home_b else Vector3(4.2, 4.6, 4.4)
            collision.shape = shape
            house.add_child(collision)
            plot_index += 1


func _build_kaykit_villagers() -> void:
    # Fifteen separate, visible KayKit-rig villagers, not impostor billboards.
    # Five creator species heads x three clear pastel palettes, each with a
    # stable unique look ID. All are physics actors that block the player.
    var species := [
        "species_head_human_v1", "species_head_cat_v1",
        "species_head_sheep_v1", "species_head_robot_v1",
        "species_head_cloud_v1",
    ]
    var colors := ["#F7B7D2", "#B9E7D0", "#D7C2F3"]
    for i in range(15):
        var x: float = float([-6.8, -4.0, 4.0, 6.8][i % 4])
        var z: float = 16.0 - float(int(i / 4)) * 9.0 - float(i % 4) * 0.8
        var look := {
            "look_id": "KayKitVillager%02d" % i,
            "species_head_id": species[i % 5],
            "surface_color_hex": colors[int(i / 5)],
            "eye_color_hex": "#2D3150",
            "body_type": "standard" if i % 2 == 0 else "slim",
            "role_palette": colors[int(i / 5)],
            "hat_style": i % 5,
        }
        var npc := MiniUtopiaKaykitVillageNPC.new()
        npc.configure(look, Vector3(x, 0.15, z))
        add_child(npc)


func _cottage(origin: Vector3, accent: Color) -> void:
    _box("Cottage", origin + Vector3(0,1.5,0), Vector3(4.4,3.0,3.6), palette.cream, true)
    _box("CottageTrim", origin + Vector3(0,0.38,1.86), Vector3(4.55,0.35,0.16), palette.wood_light)
    var roof := _box("Roof", origin + Vector3(0,3.35,0), Vector3(5.0,0.8,4.2), accent)
    roof.rotation_degrees.z = 7.0
    _box("Door", origin + Vector3(0,1.1,1.83), Vector3(1.1,2.0,0.18), palette.wood)
    _box("Window", origin + Vector3(-1.25,1.7,1.84), Vector3(0.8,0.8,0.16), Color("#78B9C7"))
    _box("Window", origin + Vector3(1.25,1.7,1.84), Vector3(0.8,0.8,0.16), Color("#78B9C7"))
    _cylinder("Chimney", origin + Vector3(1.35,4.1,-0.6), 0.35, 1.8, palette.wood)

func _build_forest() -> void:
    # Keep the trees outside house footprints and the player's paths.
    var points = [
        Vector3(-31,0,-28), Vector3(-31,0,-16), Vector3(-31,0,-4),
        Vector3(-31,0,8), Vector3(-31,0,20), Vector3(-31,0,30),
        Vector3(31,0,-28), Vector3(31,0,-16), Vector3(31,0,-4),
        Vector3(31,0,8), Vector3(31,0,20), Vector3(31,0,30),
        Vector3(-12,0,26), Vector3(12,0,26), Vector3(-4,0,30),
        Vector3(4,0,30)
    ]
    for i in points.size():
        _tree(points[i], i % 2 == 0)

func _tree(origin: Vector3, alternate: bool) -> void:
    _cylinder("TreeTrunk", origin + Vector3(0,1.5,0), 0.42, 3.0, palette.wood, true)
    var leaf_color: Color = palette.leaf2 if alternate else palette.leaf
    _sphere("TreeCrown", origin + Vector3(0,4.1,0), 2.2, leaf_color, Vector3(1.0,1.15,1.0))
    _sphere("TreeCrown", origin + Vector3(1.0,3.8,0.4), 1.5, leaf_color)
    _sphere("TreeCrown", origin + Vector3(-1.0,3.9,-0.3), 1.55, leaf_color)

func _mushroom(origin: Vector3, scale_factor: float, cap_color: Color) -> void:
    var stem_height := 2.3 * scale_factor
    _cylinder(
        "MushroomStem",
        origin + Vector3(0, stem_height * 0.5, 0),
        0.48 * scale_factor,
        stem_height,
        palette.cream_light,
        true
    )
    _sphere(
        "MushroomCap",
        origin + Vector3(0, stem_height + 0.28 * scale_factor, 0),
        1.45 * scale_factor,
        cap_color,
        Vector3(1.25, 0.48, 1.25)
    )
    for offset in [
        Vector3(-0.58,0.18,0.18),
        Vector3(0.45,0.22,-0.32),
        Vector3(0.1,0.3,0.52),
    ]:
        _sphere(
            "MushroomSpot",
            origin + Vector3(0, stem_height + 0.66 * scale_factor, 0)
                + offset * scale_factor,
            0.2 * scale_factor,
            palette.mushroom_spot,
            Vector3(1.0,0.35,1.0)
        )

func _fence_segment(origin: Vector3, length: float, yaw_degrees: float) -> void:
    var root := Node3D.new()
    root.position = origin
    root.rotation_degrees.y = yaw_degrees
    add_child(root)

    for x in [-length * 0.5, length * 0.5]:
        var post := _cylinder(
            "FencePost",
            Vector3.ZERO,
            0.18,
            1.55,
            palette.wood,
            false
        )
        remove_child(post)
        root.add_child(post)
        post.position = Vector3(x,0.78,0)

    for y in [0.62, 1.2]:
        var rail := _box(
            "FenceRail",
            Vector3.ZERO,
            Vector3(length,0.18,0.18),
            palette.wood_light,
            false
        )
        remove_child(rail)
        root.add_child(rail)
        rail.position = Vector3(0,y,0)

func _build_storybook_dressing() -> void:
    _mushroom(Vector3(-13,0,8), 1.55, palette.mushroom_red)
    _mushroom(Vector3(13,0,7), 1.3, palette.mushroom_orange)
    _mushroom(Vector3(-22,0,-14), 1.7, palette.mushroom_red)
    _mushroom(Vector3(22,0,-20), 1.45, palette.mushroom_orange)

    _fence_segment(Vector3(-8,0,-1.5), 7.0, 8.0)
    _fence_segment(Vector3(8,0,-2.0), 7.0, -6.0)
    _fence_segment(Vector3(-12,0,-20), 6.0, -10.0)
    _fence_segment(Vector3(12,0,-23), 6.0, 12.0)

    for p in [
        Vector3(-5,0.22,-4), Vector3(5,0.22,-5),
        Vector3(-6,0.22,-16), Vector3(6,0.22,-17),
        Vector3(-2.5,0.22,-23), Vector3(3.2,0.22,-25),
    ]:
        _sphere("FlowerPatch", p, 0.42, palette.pink, Vector3(1.8,0.35,1.4))
        _sphere("FlowerLeaf", p + Vector3(0.5,0,0.2), 0.28, palette.leaf2, Vector3(1.5,0.25,1.0))

    var welcome := Label3D.new()
    welcome.text = "NEWBIE VILLAGE"
    welcome.font_size = 34
    welcome.modulate = Color("#F4DFC1")
    welcome.outline_size = 8
    welcome.outline_modulate = Color("#56372E")
    welcome.position = Vector3(0,3.0,5.5)
    welcome.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(welcome)

func _build_locked_gate() -> void:
    var z := -31.0
    _cylinder("GatePostL", Vector3(-3.2,2.2,z), 0.5, 4.4, palette.wood, true)
    _cylinder("GatePostR", Vector3(3.2,2.2,z), 0.5, 4.4, palette.wood, true)
    _box("GateBeam", Vector3(0,4.1,z), Vector3(7.2,0.65,0.8), palette.pink, true)
    _box("LockedBarrier", Vector3(0,1.5,z), Vector3(5.5,3.0,0.45), Color("#D9B8E8"), true)

    gate_label = Label3D.new()
    gate_label.text = "🔒 NEW WORLD\nCloud Whale District"
    gate_label.font_size = 42
    gate_label.modulate = Color("#FFF7E7")
    gate_label.outline_size = 8
    gate_label.outline_modulate = Color(0.2,0.12,0.18,0.9)
    gate_label.position = Vector3(0,5.2,z + 0.1)
    gate_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(gate_label)

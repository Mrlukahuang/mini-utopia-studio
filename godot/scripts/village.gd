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

const KAYKIT_FOREST_TREES := [
    preload("res://assets/kaykit/medieval/tree_single_A.gltf"),
    preload("res://assets/kaykit/medieval/tree_single_B.gltf"),
]
const KAYKIT_FOREST_ROCKS := [
    preload("res://assets/kaykit/medieval/rock_single_A.gltf"),
    preload("res://assets/kaykit/medieval/rock_single_B.gltf"),
]

const KAYKIT_GRASS := preload("res://assets/kaykit/medieval/hex_grass.gltf")
const KAYKIT_ROAD := preload("res://assets/kaykit/medieval/hex_road_A.gltf")
const KAYKIT_PROPS := [
    preload("res://assets/kaykit/medieval/barrel.gltf"),
    preload("res://assets/kaykit/medieval/crate_A_small.gltf"),
    preload("res://assets/kaykit/medieval/wheelbarrow.gltf"),
    preload("res://assets/kaykit/medieval/sack.gltf"),
    preload("res://assets/kaykit/medieval/flag_blue.gltf"),
    preload("res://assets/kaykit/medieval/crate_A_big.gltf"),
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
var _perf_touch_index := -1
var _perf_toggled_this_hold := false
var _perf_badge: Label
var _overview_was_on := false
# Web-only two-tier adaptive quality. FPS must stay below 28 for 3 seconds
# before downgrading; recovery requires above 45 for 5 seconds.
const LOW_FPS_THRESHOLD := 28.0
const HIGH_FPS_THRESHOLD := 45.0
const DOWNGRADE_SECONDS := 3.0
const UPGRADE_SECONDS := 5.0
var _quality_low := false
var _low_fps_seconds := 0.0
var _high_fps_seconds := 0.0
var _quality_warmup_seconds := 0.0
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
    _perf_badge.position = Vector2(12, 85)
    _perf_badge.autowrap_mode = TextServer.AUTOWRAP_OFF
    _perf_badge.clip_text = true
    _perf_badge.mouse_filter = Control.MOUSE_FILTER_IGNORE
    _perf_badge.text = "FPS -- | Draw -- | 画质:清晰"
    _perf_badge.visible = false
    hud.add_child(_perf_badge)

    # An actual GUI control is essential on iPad Safari: it cannot depend on
    # the browser forwarding a touch-and-hold to an uncovered Logo region.
    var info := Button.new()
    info.name = "LaneAFPSInfoButton"
    info.text = "ⓘ"
    info.tooltip_text = "显示或隐藏 FPS"
    info.custom_minimum_size = Vector2(52, 52)
    info.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
    info.anchor_left = 1.0
    info.anchor_right = 1.0
    info.offset_left = -64.0
    info.offset_right = -12.0
    info.offset_top = 12.0
    info.offset_bottom = 64.0
    info.focus_mode = Control.FOCUS_NONE
    # Keep the info button inside the actual viewport safe rectangle.
    info.resized.connect(func() -> void:
        info.clip_contents = true
    )
    info.pressed.connect(_toggle_performance_badge)
    hud.add_child(info)


func _input(event: InputEvent) -> void:
    # Touch down/up are distinct events on Safari. Keep the finger index so
    # another finger (D-pad) cannot cancel a valid hold. One second is enough.
    if event is InputEventScreenTouch:
        var touch := event as InputEventScreenTouch
        if touch.pressed:
            if _perf_touch_index < 0 and touch.position.x < 160.0 and touch.position.y < 164.0:
                _perf_touch_index = touch.index
                _perf_pressing = true
                _perf_toggled_this_hold = false
                _perf_hold_elapsed = 0.0
        elif touch.index == _perf_touch_index:
            _perf_touch_index = -1
            _perf_pressing = false
    elif event is InputEventMouseButton and _perf_touch_index < 0:
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
        if _perf_hold_elapsed >= 1.0:
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
    var quality := "流畅" if _quality_low else "清晰"
    _perf_badge.text = "FPS %.0f | Draw %s | 画质:%s" % [frames, str(draw) if draw > 0 else "--", quality]


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


func _watch_adaptive_quality(delta: float) -> void:
    if not OS.has_feature("web"):
        return
    # CI overview uses F9 and an intentionally 12fps screenshot cap. Never
    # misinterpret that diagnostic view as iPad gameplay performance.
    var rig := get_node_or_null("CameraRig")
    if rig != null and float(rig.get("distance")) > 20.0:
        _low_fps_seconds = 0.0
        _high_fps_seconds = 0.0
        return
    # Avoid switching during shader warmup, page restore or loading spikes.
    _quality_warmup_seconds += minf(delta, 0.25)
    if _quality_warmup_seconds < 4.0:
        return
    var fps := float(Performance.get_monitor(Performance.TIME_FPS))
    if fps <= 0.0:
        return
    var sample_seconds := minf(delta, 0.25)
    if not _quality_low:
        _low_fps_seconds = _low_fps_seconds + sample_seconds if fps < LOW_FPS_THRESHOLD else 0.0
        if _low_fps_seconds >= DOWNGRADE_SECONDS:
            _set_quality_low(true)
    else:
        _high_fps_seconds = _high_fps_seconds + sample_seconds if fps > HIGH_FPS_THRESHOLD else 0.0
        if _high_fps_seconds >= UPGRADE_SECONDS:
            _set_quality_low(false)


func _set_quality_low(enable: bool) -> void:
    if _quality_low == enable:
        return
    _quality_low = enable
    _low_fps_seconds = 0.0
    _high_fps_seconds = 0.0
    var viewport := get_viewport()
    viewport.scaling_3d_scale = 0.6 if enable else 0.75
    var sun := get_node_or_null("VillageSun") as DirectionalLight3D
    if sun != null:
        sun.shadow_enabled = not enable
    var camera := viewport.get_camera_3d()
    var rig := get_node_or_null("CameraRig")
    var overview := rig != null and float(rig.get("distance")) > 20.0
    if camera != null:
        camera.far = 160.0 if overview else (60.0 if enable else 85.0)
    for batch in _static_batches:
        if is_instance_valid(batch):
            batch.visibility_range_end = 0.0 if overview else (45.0 if enable else 65.0)
    print("lane_a_quality: %s scale=%.2f shadows=%s" % [
        "smooth" if enable else "clear", viewport.scaling_3d_scale, str(not enable)
    ])


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
    var active_camera := get_viewport().get_camera_3d()
    if active_camera != null and OS.has_feature("web"):
        active_camera.far = 160.0 if overhead else (60.0 if _quality_low else 85.0)
    for batch in _static_batches:
        if is_instance_valid(batch):
            batch.visibility_range_end = 0.0 if overhead else (45.0 if _quality_low else 65.0)


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
    _watch_adaptive_quality(delta)
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
    # Reuse material RID across hundreds of grass props/tree crowns.
    var key := color.to_html() + "_" + str(roughness)
    if _mat_pool.has(key):
        return _mat_pool[key] as StandardMaterial3D
    var m := StandardMaterial3D.new()
    m.albedo_color = color
    m.roughness = roughness
    _mat_pool[key] = m
    return m


func _shared_mesh(kind: String, dimensions: Vector3) -> Mesh:
    var key := kind + "/" + str(dimensions)
    if _mesh_pool.has(key):
        return _mesh_pool[key] as Mesh
    var mesh: Mesh
    match kind:
        "box":
            var cube := BoxMesh.new()
            cube.size = dimensions
            mesh = cube
        "sphere":
            var ball := SphereMesh.new()
            ball.radius = dimensions.x
            ball.height = dimensions.y
            mesh = ball
        "cylinder":
            var column := CylinderMesh.new()
            column.top_radius = dimensions.x
            column.bottom_radius = dimensions.x * 1.08
            column.height = dimensions.y
            mesh = column
    _mesh_pool[key] = mesh
    return mesh


func _register_static(node: MeshInstance3D, casts_shadow: bool = false) -> void:
    _static_visuals.append({"mesh": node, "shadow": casts_shadow})


func _batch_static_visuals() -> void:
    var groups: Dictionary = {}
    for entry in _static_visuals:
        var source := entry["mesh"] as MeshInstance3D
        if not is_instance_valid(source) or source.mesh == null or not source.visible:
            continue
        var transform := global_transform.affine_inverse() * source.global_transform
        var center := transform.origin
        var cluster := Vector2i(floori(center.x / 42.0), floori(center.z / 42.0))
        var material_id := 0
        if source.material_override != null:
            material_id = source.material_override.get_instance_id()
        var shadows: bool = entry["shadow"]
        var key := str(source.mesh.get_instance_id()) + "/" + str(material_id) + "/" + str(cluster) + "/" + str(shadows)
        if not groups.has(key):
            groups[key] = {
                "mesh": source.mesh,
                "material": source.material_override,
                "shadows": shadows,
                "transforms": [],
            }
        var transforms: Array = groups[key]["transforms"]
        transforms.append(transform)
        source.visible = false

    for key in groups:
        var entry: Dictionary = groups[key]
        var transforms: Array = entry["transforms"]
        var multi := MultiMesh.new()
        multi.transform_format = MultiMesh.TRANSFORM_3D
        multi.mesh = entry["mesh"] as Mesh
        multi.instance_count = transforms.size()
        for i in range(transforms.size()):
            multi.set_instance_transform(i, transforms[i])
        var batch := MultiMeshInstance3D.new()
        batch.name = "StaticBatch"
        batch.multimesh = multi
        batch.material_override = entry["material"] as Material
        if not entry["shadows"]:
            batch.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        batch.visibility_range_end = 65.0
        batch.visibility_range_end_margin = 5.0
        batch.add_to_group("lane_a_static_batch")
        add_child(batch)
        _static_batches.append(batch)
    print("lane_a_perf: original_static_mesh_nodes=%d batched_drawable_clusters=%d" % [_static_visuals.size(), _static_batches.size()])
    _static_visuals.clear()

func _box(name: String, pos: Vector3, size: Vector3, color: Color, collision := false) -> MeshInstance3D:
    var mesh := _shared_mesh("box", size)
    var node := MeshInstance3D.new()
    node.name = name
    node.mesh = mesh
    node.material_override = _mat(color)
    node.position = pos
    add_child(node)
    if name != "LockedBarrier":
        _register_static(node)
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
    var mesh := _shared_mesh("sphere", Vector3(radius, radius * 2.0, 0.0))
    var node := MeshInstance3D.new()
    node.name = name
    node.mesh = mesh
    node.material_override = _mat(color)
    node.position = pos
    node.scale = squash
    add_child(node)
    _register_static(node)
    return node

func _cylinder(name: String, pos: Vector3, radius: float, height: float, color: Color, collision := false) -> MeshInstance3D:
    var mesh := _shared_mesh("cylinder", Vector3(radius, height, 0.0))
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
    env.background_color = Color("#ACDAFF")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#DDEFFF")
    env.ambient_light_energy = 0.62
    env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
    env.fog_enabled = true
    env.fog_light_color = Color("#C5E6FC")
    env.fog_light_energy = 0.34
    env.fog_density = 0.012 if OS.has_feature("web") else 0.004
    env.ssao_enabled = false
    env.glow_enabled = false
    env.ssil_enabled = false
    env.ssr_enabled = false
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.name = "VillageSun"
    sun.rotation_degrees = Vector3(-48, -38, 0)
    sun.light_color = Color("#FFF4D9")
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
    var physical_ground := _box("VillageGround", Vector3(0, -0.55, 0), Vector3(70, 1, 70), palette.grass, true)
    physical_ground.visible = false
    var tiles: Array[Vector3] = []
    for row in range(-12, 13):
        for col in range(-12, 13):
            tiles.append(Vector3(float(col) * 2.9 + (1.45 if row % 2 else 0.0), -0.16, float(row) * 2.7))
    _batch_kaykit_props(KAYKIT_GRASS, tiles, 1.58, "KayKitGrass", false)
    for p in [
        Vector3(-20,0,18), Vector3(22,0,-15), Vector3(-25,0,-20),
        Vector3(25,0,20), Vector3(0,0,-34)
    ]:
        _sphere("Hill", p + Vector3(0,-1.2,0), 8.0, palette.grass2, Vector3(1.8,0.55,1.4))
    _sphere("VillageMound", Vector3(0,-1.0,-12), 12.0, palette.grass_dark, Vector3(1.2,0.12,0.85))

func _build_path() -> void:
    var stones: Array[Vector3] = []
    for i in range(-17, 18):
        stones.append(Vector3(sin(float(i) * 0.25) * 0.8, 0.03, float(i) * 1.83))
    _batch_kaykit_props(KAYKIT_ROAD, stones, 1.1, "KayKitStoneRoad", false)

func _batch_kaykit_props(model: PackedScene, locations: Array[Vector3], scale_factor: float, label: String, regional: bool) -> void:
    var template := model.instantiate() as Node3D
    if template == null:
        push_error("Official KayKit model missing: " + label)
        return
    # Imported GLTF transforms are only valid when the temporary source is
    # inside the scene tree; free it immediately after baking the MultiMesh.
    add_child(template)
    var groups: Dictionary = {}
    for point in locations:
        var key := Vector2i(floori(point.x / 24.0), floori(point.z / 24.0)) if regional else Vector2i.ZERO
        if not groups.has(key):
            groups[key] = []
        var points: Array = groups[key]
        points.append(point)
    var parts: Array[MeshInstance3D] = []
    if template is MeshInstance3D:
        parts.append(template as MeshInstance3D)
    for sub in template.find_children("*", "MeshInstance3D", true, false):
        parts.append(sub as MeshInstance3D)
    for part in parts:
        if part.mesh == null:
            continue
        var relative := template.global_transform.affine_inverse() * part.global_transform
        for cell in groups:
            var points: Array = groups[cell]
            var multi := MultiMesh.new()
            multi.transform_format = MultiMesh.TRANSFORM_3D
            multi.mesh = part.mesh
            multi.instance_count = points.size()
            for i in range(points.size()):
                multi.set_instance_transform(i,
                    Transform3D(Basis().scaled(Vector3.ONE * scale_factor), points[i]) * relative
                )
            var batch := MultiMeshInstance3D.new()
            batch.name = label + "Batch"
            batch.multimesh = multi
            batch.material_override = part.material_override
            batch.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
            batch.visibility_range_end = 65.0
            batch.add_to_group("lane_a_static_batch")
            add_child(batch)
            _static_batches.append(batch)
    remove_child(template)
    template.free()

func _market_collision(location: Vector3) -> void:
    var body := StaticBody3D.new()
    body.name = "KayKitMarketCollider"
    body.add_to_group("kaykit_village_props")
    body.position = location
    var collision := CollisionShape3D.new()
    collision.name = "CollisionShape3D"
    var shape := BoxShape3D.new()
    shape.size = Vector3(1.25, 1.25, 1.25)
    collision.position.y = 0.625
    collision.shape = shape
    body.add_child(collision)
    add_child(body)

func _build_village() -> void:
    _build_kaykit_houses()

    _cylinder("FountainBase", Vector3(0,0.25,-10), 2.2, 0.5, palette.stone, true)
    _cylinder("FountainStem", Vector3(0,1.0,-10), 0.35, 1.5, palette.cream)
    _sphere("FountainBubble", Vector3(0,2.0,-10), 0.7, Color("#72B7C9"))


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
            for mesh_node in visual.find_children("*", "MeshInstance3D", true, false):
                _register_static(mesh_node as MeshInstance3D, true)
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
    # Six genuinely different CC0 KayKit source meshes across 15 villagers.
    # No fake species heads, procedural hats or mesh-based costumes.
    var colors := ["#F7B7D2", "#B9E7D0", "#D7C2F3"]
    for i in range(15):
        var x: float = float([-6.8, -4.0, 4.0, 6.8][i % 4])
        var z: float = 16.0 - float(int(i / 4)) * 9.0 - float(i % 4) * 0.8
        var look := {
            "look_id": "KayKitVillager%02d" % i,
            "kaykit_rig_index": i % 6,
            "species_head_id": "species_head_human_v1",
            "body_type": "standard" if i % 2 == 0 else "slim",
            "surface_color_hex": colors[int(i / 5)],
        }
        var npc := MiniUtopiaKaykitVillageNPC.new()
        npc.configure(look, Vector3(x, 0.15, z))
        add_child(npc)
        _villagers.append(npc)
    for actor in _villagers:
        actor.configure_neighbors(_villagers)

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
    # Use CC0 KayKit geometry, rendered through z-clustered MultiMeshes.
    # Physics stays in primitive BoxShapes instead of mesh triangles.
    var trees: Array[Vector3] = []
    var rocks: Array[Vector3] = []
    for side in [-1.0, 1.0]:
        for i in range(10):
            var z := -29.0 + float(i) * 6.4
            trees.append(Vector3(side * 31.0, 0.0, z))
            rocks.append(Vector3(side * 28.0, 0.0, z + 3.1))
    trees.append_array([
        Vector3(-11, 0, 25), Vector3(11, 0, 25),
        Vector3(-10, 0, -30), Vector3(10, 0, -30)
    ])
    for i in range(trees.size()):
        _forest_collision(trees[i], true)
    for rock in rocks:
        _forest_collision(rock, false)
    for index in range(2):
        var tree_points: Array[Vector3] = []
        var rock_points: Array[Vector3] = []
        for i in range(trees.size()):
            if i % 2 == index:
                tree_points.append(trees[i])
        for i in range(rocks.size()):
            if i % 2 == index:
                rock_points.append(rocks[i])
        _forest_multimesh(KAYKIT_FOREST_TREES[index], tree_points, 8.0, "KayKitTree")
        _forest_multimesh(KAYKIT_FOREST_ROCKS[index], rock_points, 3.4, "KayKitRock")

func _forest_multimesh(model: PackedScene, locations: Array[Vector3], scaling: float, title: String) -> void:
    var source := model.instantiate() as Node3D
    if source == null:
        push_error("Official KayKit forest model missing: " + title)
        return
    # Spatial clustering makes WebGL's visibility range actually cull each
    # group, rather than drawing every tree in one world-sized bounding box.
    var bands: Dictionary = {}
    for pos in locations:
        var region := Vector2i(floori(pos.x / 24.0), floori(pos.z / 24.0))
        if not bands.has(region):
            bands[region] = []
        var entries: Array = bands[region]
        entries.append(pos)
    var source_parts: Array[MeshInstance3D] = []
    if source is MeshInstance3D:
        source_parts.append(source as MeshInstance3D)
    for child in source.find_children("*", "MeshInstance3D", true, false):
        source_parts.append(child as MeshInstance3D)
    for mesh_part in source_parts:
        if mesh_part.mesh == null:
            continue
        var local := source.global_transform.affine_inverse() * mesh_part.global_transform
        for region in bands:
            var points: Array = bands[region]
            var multi := MultiMesh.new()
            multi.transform_format = MultiMesh.TRANSFORM_3D
            multi.mesh = mesh_part.mesh
            multi.instance_count = points.size()
            for i in range(points.size()):
                multi.set_instance_transform(i,
                    Transform3D(Basis().scaled(Vector3.ONE * scaling), points[i]) * local
                )
            var batch := MultiMeshInstance3D.new()
            batch.name = title + "Batch"
            batch.multimesh = multi
            batch.material_override = mesh_part.material_override
            batch.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
            batch.visibility_range_end = 65.0
            batch.add_to_group("lane_a_static_batch")
            add_child(batch)
            _static_batches.append(batch)
    source.free()

func _forest_collision(location: Vector3, is_tree: bool) -> void:
    var body := StaticBody3D.new()
    body.name = "KayKitTreeCollision" if is_tree else "KayKitRockCollision"
    body.add_to_group("kaykit_village_nature")
    body.position = location
    var collider := CollisionShape3D.new()
    collider.name = "CollisionShape3D"
    var box := BoxShape3D.new()
    box.size = Vector3(1.30, 2.70, 1.30) if is_tree else Vector3(1.40, 0.95, 1.40)
    collider.position.y = box.size.y * 0.5
    collider.shape = box
    body.add_child(collider)
    add_child(body)

func _build_storybook_dressing() -> void:
    # The same 30 market objects from #404, but six low-cost batched model
    # groups instead of a unique imported scene draw for every placement.
    for category in range(KAYKIT_PROPS.size()):
        var positions: Array[Vector3] = []
        for i in range(30):
            if i % KAYKIT_PROPS.size() != category:
                continue
            var side := -1.0 if i % 2 == 0 else 1.0
            var x := side * (11.1 + float(i % 3) * 0.8)
            var z := -27.0 + float(int(i / 2) % 10) * 5.5
            var spot := Vector3(x, 0.0, z)
            positions.append(spot)
            _market_collision(spot)
        _batch_kaykit_props(KAYKIT_PROPS[category], positions, 3.3, "KayKitMarket%d" % category, true)

    # Removed the old sphere mushrooms, sphere flowers and cylinder/box
    # fences. Official KayKit scenery is now supplied by batched assets.

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

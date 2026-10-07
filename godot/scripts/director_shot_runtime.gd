class_name MiniUtopiaDirectorShotRuntime
extends Node3D

const SESSION_PATH := "res://runtime_state/director_shot_session.json"

var payload: Dictionary = {}
var actor: CharacterBody3D
var camera: Camera3D
var play_runtime: MiniUtopiaCreatorPlayRuntime
var world_context: Node3D
var bound_world_instance: Node3D
var bound_world_loaded := false
var bound_scene_path := ""
var world_load_error := ""
var blocking_start := Vector3.ZERO
var blocking_end := Vector3.ZERO
var blocking_movement_style := ""
var blocking_has_path := false
var elapsed_seconds := 0.0
var duration_seconds := 0.0
var animation_intent := "idle"
var playing := false


func load_default_session() -> Dictionary:
    return _load_json(SESSION_PATH)


func configure(runtime_payload: Dictionary) -> void:
    payload = runtime_payload.duplicate(true)
    elapsed_seconds = 0.0
    duration_seconds = float(payload.get("duration_seconds", 0.0))
    animation_intent = String(payload.get("animation_intent", "idle"))
    playing = duration_seconds > 0.0

    _clear_stage()
    _build_world_context()
    _build_actor()
    _apply_shot_blocking()
    _build_camera()

    var raw_play = payload.get("play_session", {})
    var play_payload: Dictionary = (
        raw_play
        if typeof(raw_play) == TYPE_DICTIONARY
        else {}
    )
    play_runtime = MiniUtopiaCreatorPlayRuntime.new()
    play_runtime.name = "CreatorPlayRuntime"
    add_child(play_runtime)
    play_runtime.apply_payload_to_player(actor, play_payload)

    if animation_intent == "attack":
        play_runtime.play_attack_swing()

    set_meta(
        "director_session_id",
        String(payload.get("director_session_id", ""))
    )
    set_meta(
        "episode_id",
        String(payload.get("episode_id", ""))
    )
    set_meta(
        "scene_id",
        String(payload.get("scene_id", ""))
    )
    set_meta(
        "shot_id",
        String(payload.get("shot_id", ""))
    )
    set_meta(
        "world_asset_id",
        String(payload.get("world_asset_id", ""))
    )

    print(
        "DIR-04 staged: ",
        payload.get("episode_id", "—"),
        " / ",
        payload.get("scene_id", "—"),
        " / ",
        payload.get("shot_id", "—"),
        " · actor=",
        play_payload.get("character_name", "Mini Traveler"),
        " · animation=",
        animation_intent,
        " · duration=",
        duration_seconds,
        "s"
    )


func _process(delta: float) -> void:
    if playing:
        advance_shot(delta)


func advance_shot(delta: float) -> void:
    if not playing or actor == null or play_runtime == null:
        return

    elapsed_seconds = minf(duration_seconds, elapsed_seconds + delta)
    var velocity := Vector3.ZERO
    var running := false
    var movement_mode := (
        blocking_movement_style
        if blocking_has_path and not blocking_movement_style.is_empty()
        else animation_intent
    )

    if (
        blocking_has_path
        and movement_mode in ["walk", "run"]
    ):
        var remaining := blocking_end - actor.position
        var remaining_distance := remaining.length()
        var total_distance := (
            blocking_end - blocking_start
        ).length()
        var speed := total_distance / maxf(duration_seconds, 0.001)
        if remaining_distance > 0.001 and speed > 0.0:
            var direction := remaining / remaining_distance
            var step_distance := minf(
                remaining_distance,
                speed * delta
            )
            actor.position += direction * step_distance
            velocity = direction * speed
        running = movement_mode == "run"
    else:
        match movement_mode:
            "walk":
                velocity = Vector3(0.0, 0.0, -1.6)
            "run":
                velocity = Vector3(0.0, 0.0, -3.2)
                running = true
            "attack":
                if elapsed_seconds <= delta + 0.001:
                    play_runtime.play_attack_swing()
            _:
                pass

        if velocity.length() > 0.0 and not blocking_has_path:
            actor.position += velocity * delta

    play_runtime.update_motion(
        delta,
        velocity,
        true,
        running
    )

    if elapsed_seconds >= duration_seconds:
        if (
            blocking_has_path
            and movement_mode in ["walk", "run"]
        ):
            actor.position = blocking_end
        playing = false


func reset_shot() -> void:
    elapsed_seconds = 0.0
    playing = duration_seconds > 0.0
    if actor != null and blocking_has_path:
        actor.position = blocking_start
        var raw_shot = payload.get("shot", {})
        if typeof(raw_shot) == TYPE_DICTIONARY:
            var raw_blocking = raw_shot.get("blocking", {})
            if typeof(raw_blocking) == TYPE_DICTIONARY:
                actor.rotation_degrees.y = float(
                    raw_blocking.get("facing_degrees", 0.0)
                )
    if play_runtime != null:
        play_runtime.update_motion(
            0.0,
            Vector3.ZERO,
            true,
            false
        )


func progress_ratio() -> float:
    if duration_seconds <= 0.0:
        return 0.0
    return clampf(elapsed_seconds / duration_seconds, 0.0, 1.0)


func _clear_stage() -> void:
    for child in get_children():
        child.queue_free()
    actor = null
    camera = null
    play_runtime = null
    world_context = null
    bound_world_instance = null
    bound_world_loaded = false
    bound_scene_path = ""
    world_load_error = ""
    blocking_start = Vector3.ZERO
    blocking_end = Vector3.ZERO
    blocking_movement_style = ""
    blocking_has_path = false


func _build_world_context() -> void:
    world_context = Node3D.new()
    world_context.name = "DirectorWorldContext"
    add_child(world_context)

    world_context.set_meta(
        "world_asset_id",
        String(payload.get("world_asset_id", ""))
    )

    var raw_play = payload.get("play_session", {})
    var play_payload: Dictionary = (
        raw_play
        if typeof(raw_play) == TYPE_DICTIONARY
        else {}
    )
    world_context.set_meta(
        "world_name",
        String(play_payload.get("world_name", ""))
    )

    var raw_binding = play_payload.get("world_runtime", {})
    var binding: Dictionary = (
        raw_binding
        if typeof(raw_binding) == TYPE_DICTIONARY
        else {}
    )
    var scene_path := String(binding.get("scene_path", "")).strip_edges()

    if not scene_path.is_empty() and _load_bound_world(
        world_context,
        scene_path
    ):
        world_context.set_meta("runtime_mode", "bound_scene")
        world_context.set_meta("scene_path", scene_path)
        return

    _build_fallback_world(world_context)
    world_context.set_meta("runtime_mode", "fallback_stage")


func _load_bound_world(parent: Node3D, scene_path: String) -> bool:
    bound_scene_path = scene_path
    if not ResourceLoader.exists(scene_path, "PackedScene"):
        world_load_error = "Bound World scene does not exist: " + scene_path
        push_error("DIR-05: " + world_load_error)
        return false

    var packed = load(scene_path) as PackedScene
    if packed == null:
        world_load_error = "Bound World scene could not load: " + scene_path
        push_error("DIR-05: " + world_load_error)
        return false

    var instance = packed.instantiate()
    if not (instance is Node3D):
        world_load_error = "Bound World scene root must be Node3D: " + scene_path
        push_error("DIR-05: " + world_load_error)
        instance.queue_free()
        return false

    bound_world_instance = instance as Node3D
    _prepare_bound_world(bound_world_instance)
    parent.add_child(bound_world_instance)
    _sanitize_bound_world(bound_world_instance)

    bound_world_loaded = true
    print("DIR-05 bound World loaded: ", scene_path)
    return true


func _prepare_bound_world(node: Node) -> void:
    if node is Camera3D:
        (node as Camera3D).current = false

    if node.name == "Player" or node.name == "CameraRig":
        node.process_mode = Node.PROCESS_MODE_DISABLED
        node.set_script(null)
        if node is Node3D:
            (node as Node3D).visible = false

    for child in node.get_children():
        _prepare_bound_world(child)


func _sanitize_bound_world(node: Node) -> void:
    if node is Camera3D:
        (node as Camera3D).current = false
    if node is CanvasLayer:
        (node as CanvasLayer).visible = false

    if node.name == "Player" or node.name == "CameraRig":
        node.process_mode = Node.PROCESS_MODE_DISABLED
        if node is Node3D:
            (node as Node3D).visible = false

    for child in node.get_children():
        _sanitize_bound_world(child)

    if node == bound_world_instance:
        # The scene's _ready() has already built its static visual world.
        # Freeze its gameplay processing so Director owns camera/action timing.
        node.process_mode = Node.PROCESS_MODE_DISABLED


func _build_fallback_world(parent: Node3D) -> void:
    var floor := MeshInstance3D.new()
    floor.name = "StageFloor"
    var floor_mesh := PlaneMesh.new()
    floor_mesh.size = Vector2(18.0, 18.0)
    floor.mesh = floor_mesh
    floor.material_override = _material(Color("#B9E7D0"))
    parent.add_child(floor)


func _build_actor() -> void:
    actor = CharacterBody3D.new()
    actor.name = "DirectorActor"
    actor.position = Vector3(0.0, 0.0, 0.0)
    add_child(actor)

    var visual := Node3D.new()
    visual.name = "Visual"
    actor.add_child(visual)

    _box(
        visual,
        "Body",
        Vector3(0.0, 0.92, 0.0),
        Vector3(0.76, 0.92, 0.48),
        Color("#FFF4D7")
    )
    _sphere(
        visual,
        "Head",
        Vector3(0.0, 1.58, 0.0),
        Vector3(0.70, 0.69, 0.67),
        Color("#F2C7A5")
    )
    _sphere(
        visual,
        "Hair",
        Vector3(0.0, 1.91, -0.01),
        Vector3(0.74, 0.31, 0.69),
        Color("#5B4036")
    )


func _apply_shot_blocking() -> void:
    var raw_shot = payload.get("shot", {})
    var shot_payload: Dictionary = (
        raw_shot
        if typeof(raw_shot) == TYPE_DICTIONARY
        else {}
    )
    var raw_blocking = shot_payload.get("blocking", {})
    var blocking: Dictionary = (
        raw_blocking
        if typeof(raw_blocking) == TYPE_DICTIONARY
        else {}
    )
    if blocking.is_empty():
        return

    blocking_start = _point_from_dict(
        blocking.get("actor_start", {}),
        actor.position
    )
    blocking_end = _point_from_dict(
        blocking.get("actor_end", {}),
        blocking_start
    )
    blocking_movement_style = String(
        blocking.get("movement_style", "hold")
    )
    blocking_has_path = true

    actor.position = blocking_start
    actor.rotation_degrees.y = float(
        blocking.get("facing_degrees", 0.0)
    )

    var raw_baby_offset = blocking.get("baby_offset", {})
    print(
        "DIR-06 blocking: start=",
        blocking_start,
        " end=",
        blocking_end,
        " movement=",
        blocking_movement_style
    )

    if typeof(raw_baby_offset) == TYPE_DICTIONARY:
        actor.set_meta(
            "director_baby_side_offset",
            -float(raw_baby_offset.get("x", -0.8))
        )
        actor.set_meta(
            "director_baby_follow_distance",
            absf(float(raw_baby_offset.get("z", 1.0)))
        )


func _point_from_dict(value: Variant, fallback: Vector3) -> Vector3:
    if typeof(value) != TYPE_DICTIONARY:
        return fallback
    return Vector3(
        float(value.get("x", fallback.x)),
        float(value.get("y", fallback.y)),
        float(value.get("z", fallback.z))
    )


func _build_camera() -> void:
    camera = Camera3D.new()
    camera.name = "DirectorCamera"
    add_child(camera)

    var camera_payload = payload.get("camera", {})
    var position_values = camera_payload.get(
        "position",
        [0.0, 4.2, 7.8]
    )
    var look_values = camera_payload.get(
        "look_at",
        [0.0, 1.1, 0.0]
    )
    var camera_position := _vector3(
        position_values,
        Vector3(0.0, 4.2, 7.8)
    )
    var look_target := _vector3(
        look_values,
        Vector3(0.0, 1.1, 0.0)
    )
    camera.fov = float(camera_payload.get("fov", 48.0))
    camera.current = true
    camera.look_at_from_position(
        camera_position,
        look_target,
        Vector3.UP
    )
    camera.set_meta(
        "movement",
        String(camera_payload.get("movement", ""))
    )


func _vector3(value: Variant, fallback: Vector3) -> Vector3:
    if typeof(value) != TYPE_ARRAY or value.size() < 3:
        return fallback
    return Vector3(
        float(value[0]),
        float(value[1]),
        float(value[2])
    )


func _load_json(path: String) -> Dictionary:
    if not FileAccess.file_exists(path):
        return {}
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return {}
    var parsed = JSON.parse_string(file.get_as_text())
    return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


func _box(
    parent: Node3D,
    node_name: String,
    local_position: Vector3,
    size: Vector3,
    color: Color
) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = local_position
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)
    return node


func _sphere(
    parent: Node3D,
    node_name: String,
    local_position: Vector3,
    scale_value: Vector3,
    color: Color
) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = local_position
    node.scale = scale_value
    var mesh := SphereMesh.new()
    mesh.radius = 0.5
    mesh.height = 1.0
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)
    return node


func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.82
    return material

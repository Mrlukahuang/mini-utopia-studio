class_name MiniUtopiaDirectorShotRuntime
extends Node3D

const SESSION_PATH := "res://runtime_state/director_shot_session.json"

var payload: Dictionary = {}
var actor: CharacterBody3D
var camera: Camera3D
var play_runtime: MiniUtopiaCreatorPlayRuntime
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

    match animation_intent:
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

    if velocity.length() > 0.0:
        actor.position += velocity * delta

    play_runtime.update_motion(
        delta,
        velocity,
        true,
        running
    )

    if elapsed_seconds >= duration_seconds:
        playing = false


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


func _build_world_context() -> void:
    var stage := Node3D.new()
    stage.name = "DirectorWorldContext"
    add_child(stage)

    var floor := MeshInstance3D.new()
    floor.name = "StageFloor"
    var floor_mesh := PlaneMesh.new()
    floor_mesh.size = Vector2(18.0, 18.0)
    floor.mesh = floor_mesh
    floor.material_override = _material(Color("#B9E7D0"))
    stage.add_child(floor)

    stage.set_meta(
        "world_asset_id",
        String(payload.get("world_asset_id", ""))
    )
    var raw_play = payload.get("play_session", {})
    if typeof(raw_play) == TYPE_DICTIONARY:
        stage.set_meta(
            "world_name",
            String(raw_play.get("world_name", ""))
        )


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
    camera.position = _vector3(position_values, Vector3(0.0, 4.2, 7.8))
    camera.fov = float(camera_payload.get("fov", 48.0))
    camera.current = true
    camera.look_at(
        _vector3(look_values, Vector3(0.0, 1.1, 0.0)),
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

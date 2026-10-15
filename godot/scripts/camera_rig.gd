extends Node3D

@export var target_path: NodePath
@export var distance := 7.0
@export var height := 2.2
@export var mouse_sensitivity := 0.0032
@export var follow_damping := 10.0

var yaw := 0.0
var pitch := -0.26
var target: Node3D

func _ready() -> void:
    target = get_node(target_path)
    Input.mouse_mode = (Input.MOUSE_MODE_VISIBLE if DisplayServer.is_touchscreen_available() else Input.MOUSE_MODE_CAPTURED)

func _unhandled_input(event: InputEvent) -> void:
    # The CI synthetic iPad screenshot uses an optional keyboard overview.
    # This adds no child-facing developer UI, and does not affect touch orbit.
    if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F9:
        distance = 66.0 if distance < 20.0 else 7.0
        height = 11.0 if distance > 20.0 else 2.2
        pitch = deg_to_rad(-80.0) if distance > 20.0 else -0.26
        yaw = 0.0
        # Software WebGL screenshot capture competes with an uncapped game loop.
        # Limit frames only in this opt-in CI overview; normal play is unchanged.
        Engine.max_fps = 12 if distance > 20.0 else 0
        return
    if event is InputEventScreenDrag:
        # D-pad/buttons consume their own touches; drag on the free right half
        # rotates the camera without needing a mouse or cursor capture.
        var drag := event as InputEventScreenDrag
        if drag.position.x >= get_viewport().get_visible_rect().size.x * 0.42:
            yaw -= drag.screen_relative.x * mouse_sensitivity
            pitch -= drag.screen_relative.y * mouse_sensitivity
            pitch = clamp(pitch, deg_to_rad(-60.0), deg_to_rad(12.0))
        return

    if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        yaw -= event.relative.x * mouse_sensitivity
        pitch -= event.relative.y * mouse_sensitivity
        pitch = clamp(pitch, deg_to_rad(-60.0), deg_to_rad(12.0))
    elif event is InputEventMouseButton and event.pressed and not DisplayServer.is_touchscreen_available():
        Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
    elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
        Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _process(delta: float) -> void:
    if not target:
        return
    # CI F9 overview should frame every house row, not orbit the player
    # spawn near the southern edge of the district.
    var center := Vector3(0.0, 0.0, -10.0) if distance > 20.0 else target.global_position
    var focus := center + Vector3.UP * height
    var rot := Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, pitch)
    var desired := focus + rot * Vector3(0, 0, distance)
    global_position = global_position.lerp(desired, 1.0 - exp(-follow_damping * delta))
    look_at(focus, Vector3.UP)

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
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        yaw -= event.relative.x * mouse_sensitivity
        pitch -= event.relative.y * mouse_sensitivity
        pitch = clamp(pitch, deg_to_rad(-60.0), deg_to_rad(12.0))
    elif event is InputEventMouseButton and event.pressed:
        Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
    elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
        Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _process(delta: float) -> void:
    if not target:
        return
    var focus := target.global_position + Vector3.UP * height
    var rot := Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, pitch)
    var desired := focus + rot * Vector3(0, 0, distance)
    global_position = global_position.lerp(desired, 1.0 - exp(-follow_damping * delta))
    look_at(focus, Vector3.UP)

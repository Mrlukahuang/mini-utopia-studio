extends CharacterBody3D

@export var walk_speed := 5.0
@export var run_speed := 8.0
@export var acceleration := 16.0
@export var jump_velocity := 6.3
@export var turn_speed := 12.0

var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var creator_play_runtime: MiniUtopiaCreatorPlayRuntime


func _ready() -> void:
    creator_play_runtime = MiniUtopiaCreatorPlayRuntime.new()
    creator_play_runtime.name = "CreatorPlayRuntime"
    add_child(creator_play_runtime)
    creator_play_runtime.apply_to_player(self)


func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity.y -= gravity * delta
    elif Input.is_action_just_pressed("jump"):
        velocity.y = jump_velocity

    var input_2d := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    var camera := get_viewport().get_camera_3d()
    var direction := Vector3.ZERO

    if camera and input_2d.length() > 0.01:
        var forward := -camera.global_basis.z
        forward.y = 0.0
        forward = forward.normalized()
        var right := camera.global_basis.x
        right.y = 0.0
        right = right.normalized()
        direction = (right * input_2d.x + forward * -input_2d.y).normalized()

    var target_speed := run_speed if Input.is_action_pressed("run") else walk_speed
    var target_velocity := direction * target_speed
    velocity.x = move_toward(velocity.x, target_velocity.x, acceleration * delta)
    velocity.z = move_toward(velocity.z, target_velocity.z, acceleration * delta)

    if direction.length() > 0.01:
        var desired_yaw := atan2(direction.x, direction.z)
        rotation.y = lerp_angle(rotation.y, desired_yaw, min(1.0, turn_speed * delta))

    move_and_slide()

    if creator_play_runtime != null:
        creator_play_runtime.update_motion(
            delta,
            velocity,
            is_on_floor(),
            Input.is_action_pressed("run")
        )

    if global_position.y < -10.0:
        global_position = Vector3(0, 2, 8)
        velocity = Vector3.ZERO

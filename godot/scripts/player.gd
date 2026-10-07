extends CharacterBody3D

@export var walk_speed := 5.0
@export var run_speed := 8.0
@export var acceleration := 16.0
@export var jump_velocity := 6.3
@export var turn_speed := 12.0
@export var attack_range := 2.45
@export var attack_cooldown := 0.48

var gravity: float = ProjectSettings.get_setting(
    "physics/3d/default_gravity"
)
var creator_play_runtime: MiniUtopiaCreatorPlayRuntime

var max_hp := 100
var current_hp := 100
var attack_power := 10
var defense := 8
var _attack_timer := 0.0
var _combat_label: Label3D
var _reward_banner: Label
var _reward_timer: Timer
var _spawn_position := Vector3.ZERO


func _ready() -> void:
    add_to_group("mini_utopia_player")
    _spawn_position = global_position

    creator_play_runtime = MiniUtopiaCreatorPlayRuntime.new()
    creator_play_runtime.name = "CreatorPlayRuntime"
    add_child(creator_play_runtime)
    creator_play_runtime.apply_to_player(self)

    _read_creator_stats()
    _build_combat_label()
    _build_reward_banner()
    _update_combat_label()


func _physics_process(delta: float) -> void:
    _attack_timer = maxf(0.0, _attack_timer - delta)

    if not is_on_floor():
        velocity.y -= gravity * delta
    elif Input.is_action_just_pressed("jump"):
        velocity.y = jump_velocity

    var input_2d := Input.get_vector(
        "move_left",
        "move_right",
        "move_forward",
        "move_back"
    )
    var camera := get_viewport().get_camera_3d()
    var direction := Vector3.ZERO

    if camera and input_2d.length() > 0.01:
        var forward := -camera.global_basis.z
        forward.y = 0.0
        forward = forward.normalized()
        var right := camera.global_basis.x
        right.y = 0.0
        right = right.normalized()
        direction = (
            right * input_2d.x
            + forward * -input_2d.y
        ).normalized()

    var running := Input.is_action_pressed("run")
    var target_speed := run_speed if running else walk_speed
    var target_velocity := direction * target_speed
    velocity.x = move_toward(
        velocity.x,
        target_velocity.x,
        acceleration * delta
    )
    velocity.z = move_toward(
        velocity.z,
        target_velocity.z,
        acceleration * delta
    )

    if direction.length() > 0.01:
        var desired_yaw := atan2(direction.x, direction.z)
        rotation.y = lerp_angle(
            rotation.y,
            desired_yaw,
            minf(1.0, turn_speed * delta)
        )

    if Input.is_action_just_pressed("attack"):
        _attack_nearest_enemy()

    move_and_slide()

    if creator_play_runtime != null:
        creator_play_runtime.update_motion(
            delta,
            velocity,
            is_on_floor(),
            running
        )

    if global_position.y < -10.0:
        _respawn()


func take_damage(raw_amount: int) -> void:
    if raw_amount <= 0 or current_hp <= 0:
        return

    var mitigated := maxi(
        1,
        raw_amount - int(floor(float(defense) * 0.25))
    )
    current_hp = maxi(0, current_hp - mitigated)
    _update_combat_label()

    print(
        "PLAY-03 Player hit: ",
        mitigated,
        " damage · HP ",
        current_hp,
        "/",
        max_hp
    )

    if current_hp <= 0:
        _respawn()


func _attack_nearest_enemy() -> void:
    if _attack_timer > 0.0:
        return
    _attack_timer = attack_cooldown

    if creator_play_runtime != null:
        creator_play_runtime.play_attack_swing()

    var nearest: Node3D = null
    var nearest_distance := INF
    for node in get_tree().get_nodes_in_group("mini_utopia_enemy"):
        var enemy := node as Node3D
        if enemy == null:
            continue
        var distance := global_position.distance_to(
            enemy.global_position
        )
        if distance < nearest_distance:
            nearest_distance = distance
            nearest = enemy

    if (
        nearest != null
        and nearest_distance <= attack_range
        and nearest.has_method("take_damage")
    ):
        nearest.take_damage(attack_power)
        print(
            "PLAY-03 Player attack: ATK ",
            attack_power,
            " · range ",
            snappedf(nearest_distance, 0.01)
        )


func _read_creator_stats() -> void:
    var raw_stats = get_meta("mini_utopia_stats", {})
    var stats: Dictionary = (
        raw_stats
        if typeof(raw_stats) == TYPE_DICTIONARY
        else {}
    )
    max_hp = maxi(1, int(stats.get("hp", 100)))
    current_hp = max_hp
    attack_power = maxi(1, int(stats.get("atk", 10)))
    defense = maxi(0, int(stats.get("defense", 8)))


func _respawn() -> void:
    global_position = (
        _spawn_position
        if _spawn_position.y > -5.0
        else Vector3(0.0, 2.0, 34.0)
    )
    velocity = Vector3.ZERO
    current_hp = max_hp
    _update_combat_label()
    print("PLAY-03 Player respawned with full HP.")


func show_reward_feedback(message: String) -> void:
    if _reward_banner == null:
        return
    _reward_banner.text = message
    _reward_banner.visible = true
    if _reward_timer != null:
        _reward_timer.start()


func _build_reward_banner() -> void:
    var layer := CanvasLayer.new()
    layer.name = "RewardFeedbackLayer"
    layer.layer = 25
    add_child(layer)

    _reward_banner = Label.new()
    _reward_banner.name = "RewardBanner"
    _reward_banner.set_anchors_preset(Control.PRESET_CENTER_TOP)
    _reward_banner.position = Vector2(-300.0, 26.0)
    _reward_banner.size = Vector2(600.0, 74.0)
    _reward_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    _reward_banner.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
    _reward_banner.add_theme_font_size_override("font_size", 24)
    _reward_banner.add_theme_color_override(
        "font_color",
        Color("#FFF8D6")
    )
    _reward_banner.add_theme_color_override(
        "font_shadow_color",
        Color(0.05, 0.04, 0.08, 0.92)
    )
    _reward_banner.add_theme_constant_override("shadow_offset_x", 3)
    _reward_banner.add_theme_constant_override("shadow_offset_y", 3)
    _reward_banner.visible = false
    layer.add_child(_reward_banner)

    _reward_timer = Timer.new()
    _reward_timer.name = "RewardBannerTimer"
    _reward_timer.one_shot = true
    _reward_timer.wait_time = 5.0
    _reward_timer.timeout.connect(
        func() -> void:
            if _reward_banner != null:
                _reward_banner.visible = false
    )
    add_child(_reward_timer)


func _build_combat_label() -> void:
    _combat_label = Label3D.new()
    _combat_label.name = "CombatLabel"
    _combat_label.position = Vector3(0.0, 2.34, 0.0)
    _combat_label.font_size = 34
    _combat_label.outline_size = 7
    _combat_label.modulate = Color("#FFFFFF")
    _combat_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(_combat_label)


func _update_combat_label() -> void:
    if _combat_label == null:
        return
    _combat_label.text = (
        "❤️ "
        + str(current_hp)
        + "/"
        + str(max_hp)
        + "  ⚔️ "
        + str(attack_power)
        + "  🛡️ "
        + str(defense)
    )

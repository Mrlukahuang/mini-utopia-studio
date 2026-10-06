class_name MiniUtopiaSkeletonEnemy
extends CharacterBody3D

@export var max_hp := 42
@export var attack_power := 8
@export var move_speed := 2.4
@export var aggro_range := 9.0
@export var attack_range := 1.45
@export var attack_cooldown := 1.15

var current_hp := 42
var target: CharacterBody3D
var enemy_id := "training_skeleton_01"
var _attack_timer := 0.0
var _hp_label: Label3D
var _gravity: float = ProjectSettings.get_setting(
    "physics/3d/default_gravity"
)


func configure(
    player: CharacterBody3D,
    id_value: String = "training_skeleton_01"
) -> void:
    target = player
    enemy_id = id_value


func _ready() -> void:
    current_hp = max_hp
    add_to_group("mini_utopia_enemy")
    _build_collision()
    _build_visual()
    _build_hp_label()
    _update_hp_label()


func _physics_process(delta: float) -> void:
    _attack_timer = maxf(0.0, _attack_timer - delta)

    if not is_on_floor():
        velocity.y -= _gravity * delta
    else:
        velocity.y = 0.0

    if target == null or not is_instance_valid(target):
        target = get_tree().get_first_node_in_group(
            "mini_utopia_player"
        ) as CharacterBody3D

    if target == null:
        velocity.x = move_toward(velocity.x, 0.0, 8.0 * delta)
        velocity.z = move_toward(velocity.z, 0.0, 8.0 * delta)
        move_and_slide()
        return

    var offset := target.global_position - global_position
    offset.y = 0.0
    var distance := offset.length()

    if distance <= aggro_range and distance > attack_range:
        var direction := offset.normalized()
        velocity.x = direction.x * move_speed
        velocity.z = direction.z * move_speed
        rotation.y = lerp_angle(
            rotation.y,
            atan2(direction.x, direction.z),
            minf(1.0, delta * 7.0)
        )
    else:
        velocity.x = move_toward(velocity.x, 0.0, 8.0 * delta)
        velocity.z = move_toward(velocity.z, 0.0, 8.0 * delta)

    if distance <= attack_range and _attack_timer <= 0.0:
        _attack_timer = attack_cooldown
        if target.has_method("take_damage"):
            target.take_damage(attack_power)

    move_and_slide()


func take_damage(amount: int) -> void:
    if amount <= 0 or current_hp <= 0:
        return

    current_hp = maxi(0, current_hp - amount)
    _update_hp_label()
    _flash_hit()

    print(
        "PLAY-03 Skeleton hit: ",
        amount,
        " damage · HP ",
        current_hp,
        "/",
        max_hp
    )

    if current_hp <= 0:
        _defeat()


func _defeat() -> void:
    var session_id := "NO_SESSION"
    var character_asset_id := ""
    if target != null:
        session_id = String(
            target.get_meta("mini_utopia_session_id", "NO_SESSION")
        )
        character_asset_id = String(
            target.get_meta(
                "mini_utopia_character_asset_id",
                ""
            )
        )

    var drop_id := (
        "DROP_"
        + session_id
        + "_"
        + enemy_id.to_upper()
    )
    MiniUtopiaRuntimeDropWriter.write_drop(
        {
            "drop_id": drop_id,
            "source_enemy": enemy_id,
            "definition_slug": "reward_bone_buckler",
            "rarity": "blue",
            "item_level": 1,
            "generation_seed": drop_id + "_BONE_BUCKLER",
            "character_asset_id": character_asset_id,
            "created_at": str(Time.get_unix_time_from_system()),
        }
    )

    print("PLAY-03 Skeleton defeated · Bone Buckler dropped.")
    queue_free()


func _flash_hit() -> void:
    var visual := get_node_or_null("Visual") as Node3D
    if visual == null:
        return
    visual.scale = Vector3(1.10, 0.92, 1.10)
    var tween := create_tween()
    tween.tween_property(
        visual,
        "scale",
        Vector3.ONE,
        0.13
    )


func _build_collision() -> void:
    var collision := CollisionShape3D.new()
    collision.name = "CollisionShape3D"
    collision.position = Vector3(0.0, 0.85, 0.0)
    var shape := CapsuleShape3D.new()
    shape.radius = 0.42
    shape.height = 1.65
    collision.shape = shape
    add_child(collision)


func _build_visual() -> void:
    var visual := Node3D.new()
    visual.name = "Visual"
    add_child(visual)

    var bone := Color("#EFE8D6")
    var dark := Color("#827A70")

    _add_sphere(
        visual,
        Vector3(0.0, 1.55, 0.0),
        0.27,
        bone
    )
    _add_box(
        visual,
        Vector3(0.0, 0.98, 0.0),
        Vector3(0.18, 0.62, 0.14),
        bone
    )
    _add_box(
        visual,
        Vector3(-0.24, 1.02, 0.0),
        Vector3(0.10, 0.62, 0.10),
        bone
    )
    _add_box(
        visual,
        Vector3(0.24, 1.02, 0.0),
        Vector3(0.10, 0.62, 0.10),
        bone
    )
    _add_box(
        visual,
        Vector3(-0.13, 0.40, 0.0),
        Vector3(0.11, 0.62, 0.11),
        bone
    )
    _add_box(
        visual,
        Vector3(0.13, 0.40, 0.0),
        Vector3(0.11, 0.62, 0.11),
        bone
    )
    _add_sphere(
        visual,
        Vector3(-0.09, 1.60, 0.23),
        0.055,
        dark
    )
    _add_sphere(
        visual,
        Vector3(0.09, 1.60, 0.23),
        0.055,
        dark
    )


func _build_hp_label() -> void:
    _hp_label = Label3D.new()
    _hp_label.name = "HPLabel"
    _hp_label.position = Vector3(0.0, 2.12, 0.0)
    _hp_label.font_size = 38
    _hp_label.outline_size = 8
    _hp_label.modulate = Color("#FF7171")
    _hp_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(_hp_label)


func _update_hp_label() -> void:
    if _hp_label != null:
        _hp_label.text = (
            "💀 Training Skeleton  "
            + str(current_hp)
            + "/"
            + str(max_hp)
        )


func _add_box(
    parent: Node3D,
    center: Vector3,
    size: Vector3,
    color: Color
) -> void:
    var node := MeshInstance3D.new()
    node.position = center
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)


func _add_sphere(
    parent: Node3D,
    center: Vector3,
    radius: float,
    color: Color
) -> void:
    var node := MeshInstance3D.new()
    node.position = center
    var mesh := SphereMesh.new()
    mesh.radius = radius
    mesh.height = radius * 2.0
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)


func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.88
    return material

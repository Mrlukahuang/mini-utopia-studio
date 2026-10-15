class_name MiniUtopiaKaykitVillageNPC
extends CharacterBody3D

## W1.5 villagers share the original CC0 KayKit Rig_Medium animation system.
## Each has a stable, unique visible appearance and a real moving capsule body.
var look: Dictionary = {}
var home := Vector3.ZERO
var animation_player: AnimationPlayer
var elapsed := 0.0
var moving := false
const WALK_SPEED := 0.85
const WANDER_RADIUS := 1.6


func configure(appearance: Dictionary, start: Vector3) -> void:
    look = appearance.duplicate(true)
    home = start
    position = start
    set_meta("kaykit_npc_look", String(look.get("look_id", "")))


func _ready() -> void:
    add_to_group("kaykit_village_npc")
    name = String(look.get("look_id", "KayKitVillager"))
    floor_snap_length = 0.25
    var collider := CollisionShape3D.new()
    collider.name = "CollisionShape3D"
    var shape := CapsuleShape3D.new()
    shape.radius = 0.43
    shape.height = 1.75
    collider.shape = shape
    collider.position.y = 0.9
    add_child(collider)

    animation_player = MiniUtopiaKaykitAvatarV1.mount(self, look)
    MiniUtopiaKaykitAvatarV1.play(animation_player, "Idle")
    # In addition to the official KayKit animated rig, 15 villagers have
    # five distinct toy hat silhouettes in three clearly visible colors.
    # Unlike a hidden head-bone color, these survive the Knight helmet.
    _decorate_villager()
    if animation_player == null:
        push_error("Official KayKit villager model did not load: " + name)


func _decorate_villager() -> void:
    var tint: Color = Color(String(look.get("role_palette", "#F7B7D2")))
    var style: int = int(look.get("hat_style", 0))
    var trim_color := Color("#FFF4D7")

    var coat := BoxMesh.new()
    coat.size = Vector3(0.85, 0.66, 0.22)
    _piece("VillagerCostume", coat, Vector3(0.0, 1.12, 0.44), tint)

    # The accessories use visibly different geometry, not a metadata-only ID.
    match style:
        0:
            var dome := SphereMesh.new()
            dome.radius = 0.49
            dome.height = 0.60
            _piece("VillagerHeadgear", dome, Vector3(0.0, 2.03, 0.0), tint)
        1:
            var wizard := CylinderMesh.new()
            wizard.top_radius = 0.0
            wizard.bottom_radius = 0.48
            wizard.height = 0.95
            _piece("VillagerHeadgear", wizard, Vector3(0.0, 2.44, 0.0), tint)
        2:
            var tall := CylinderMesh.new()
            tall.top_radius = 0.38
            tall.bottom_radius = 0.38
            tall.height = 0.70
            _piece("VillagerHeadgear", tall, Vector3(0.0, 2.38, 0.0), tint)
            var brim := CylinderMesh.new()
            brim.top_radius = 0.65
            brim.bottom_radius = 0.65
            brim.height = 0.13
            _piece("ToyHatBrim", brim, Vector3(0.0, 2.08, 0.0), tint)
        3:
            var left_ear := SphereMesh.new()
            left_ear.radius = 0.18
            left_ear.height = 0.85
            _piece("VillagerHeadgear", left_ear, Vector3(-0.32, 2.45, 0.0), tint)
            var right_ear := SphereMesh.new()
            right_ear.radius = 0.18
            right_ear.height = 0.85
            _piece("ToyHatRightEar", right_ear, Vector3(0.32, 2.45, 0.0), tint)
        4:
            var square := BoxMesh.new()
            square.size = Vector3(0.80, 0.54, 0.80)
            _piece("VillagerHeadgear", square, Vector3(0.0, 2.18, 0.0), tint)
            var topper := SphereMesh.new()
            topper.radius = 0.22
            topper.height = 0.44
            _piece("ToyHatTopper", topper, Vector3(0.0, 2.66, 0.0), trim_color)


func _piece(part_name: String, mesh: Mesh, location: Vector3, tint: Color) -> void:
    var node := MeshInstance3D.new()
    node.name = part_name
    node.mesh = mesh
    node.position = location
    var mat := StandardMaterial3D.new()
    mat.albedo_color = tint
    mat.roughness = 0.88
    node.material_override = mat
    add_child(node)
func _physics_process(delta: float) -> void:
    elapsed += delta
    if not is_on_floor():
        velocity.y -= 14.0 * delta
    else:
        velocity.y = -0.1

    # Quiet two-second strolling bouts alternate with idle. The low speed and
    # fixed neighbourhood keep children from being surrounded by fast actors.
    var phase := fposmod(elapsed + float(get_index()) * 1.7, 10.0)
    moving = phase > 3.0 and phase < 7.0
    if moving:
        var bearing := float(get_index()) * 2.39996
        var target := home + Vector3(cos(bearing) * WANDER_RADIUS, 0, sin(bearing) * WANDER_RADIUS)
        if phase > 5.0:
            target = home
        var offset := target - global_position
        offset.y = 0.0
        if offset.length() > 0.18:
            velocity.x = offset.normalized().x * WALK_SPEED
            velocity.z = offset.normalized().z * WALK_SPEED
            rotation.y = lerp_angle(rotation.y, atan2(velocity.x, velocity.z), minf(delta * 7.0, 1.0))
        else:
            velocity.x = 0.0
            velocity.z = 0.0
            moving = false
    else:
        velocity.x = move_toward(velocity.x, 0.0, 3.0 * delta)
        velocity.z = move_toward(velocity.z, 0.0, 3.0 * delta)

    move_and_slide()
    MiniUtopiaKaykitAvatarV1.play(
        animation_player, "Walk" if moving and Vector2(velocity.x, velocity.z).length() > 0.05 else "Idle"
    )

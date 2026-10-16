class_name MiniUtopiaKaykitVillageNPC
extends CharacterBody3D

# Original KayKit rigs: Knight plus five lightweight mesh-preserving CC0
# derivatives. Every rig retains its own source mesh, skeleton and animations.
const OFFICIAL_RIGS := [
    preload("res://assets/kaykit/adventurers/Knight.glb"),
    preload("res://assets/kaykit/adventurers/Barbarian.glb"),
    preload("res://assets/kaykit/adventurers/Mage.glb"),
    preload("res://assets/kaykit/adventurers/Rogue.glb"),
    preload("res://assets/kaykit/adventurers/Rogue_Hooded.glb"),
    preload("res://assets/kaykit/adventurers/Skeleton_Warrior.glb"),
]

## W1.5 villagers share the original CC0 KayKit Rig_Medium animation system.
## Each has a stable, unique visible appearance and a real moving capsule body.
var look: Dictionary = {}
var home := Vector3.ZERO
var animation_player: AnimationPlayer
var elapsed := 0.0
var moving := false
var greeting_bubble: Label3D
var greeting_backdrop: Sprite3D
var route_direction := 1.0
const WALK_SPEED := 1.0
const ROUTE_LENGTH := 4.5
const GREETING_DISTANCE := 3.6
const AVOID_DISTANCE := 1.35
static var _shared_bubble_texture: Texture2D
var _cached_neighbors: Array[Node3D] = []
var _lod_animation_on := true
var _lod_physics_on := true
var _greeting_enabled := false


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

    # Supply the imported rig before the shared KayKit mount helper runs;
    # the helper reuses KayKitBody and does not replace it with Knight.
    var rig_index: int = int(look.get("kaykit_rig_index", 0))
    if rig_index < 0 or rig_index >= OFFICIAL_RIGS.size():
        push_error("Unsupported KayKit village rig index: " + str(rig_index))
        return
    var rig_scene := OFFICIAL_RIGS[rig_index] as PackedScene
    var rig_instance := rig_scene.instantiate() as Node3D
    if rig_instance == null:
        push_error("KayKit village rig did not instantiate: " + str(rig_index))
        return
    rig_instance.name = "KayKitBody"
    add_child(rig_instance)
    set_meta("kaykit_npc_rig_resource", rig_scene.resource_path)
    animation_player = MiniUtopiaKaykitAvatarV1.mount(self, look)
    MiniUtopiaKaykitAvatarV1.play(animation_player, "Idle")
    # The 15 moving rigs retain collision and animations, but never render
    # shadow maps; only the single village sun and static architecture do.
    var source_body := get_node_or_null("KayKitBody") as Node3D
    if source_body != null:
        for mesh in source_body.find_children("*", "GeometryInstance3D", true, false):
            (mesh as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    # Never overlay primitive hats or costumes over the official character.
    _make_greeting()
    if animation_player == null:
        push_error("Official KayKit villager model did not load: " + name)


# Draw the same low-cost speech bubble texture for all 15 NPCs. 3D labels
# explicitly load Noto Sans SC so Safari shows Chinese instead of squares.
func _make_greeting() -> void:
    if _shared_bubble_texture == null:
        var picture := Image.create(200, 96, false, Image.FORMAT_RGBA8)
        picture.fill(Color.TRANSPARENT)
        for y in range(96):
            for x in range(200):
                var dx: int = maxi(17 - x, 0) + maxi(x - 182, 0)
                var dy: int = maxi(15 - y, 0) + maxi(y - 72, 0)
                var inside: bool = dx * dx + dy * dy <= 17 * 17
                if inside or (y > 72 and y < 91 and x >= 88 and x <= 104 - int((y - 72) * 0.33)):
                    picture.set_pixel(x, y, Color("#FFF4DC"))
        _shared_bubble_texture = ImageTexture.create_from_image(picture)
    greeting_backdrop = Sprite3D.new()
    greeting_backdrop.name = "GreetingBubble"
    greeting_backdrop.texture = _shared_bubble_texture
    greeting_backdrop.pixel_size = 0.0075
    greeting_backdrop.position = Vector3(0, 3.10, 0)
    greeting_backdrop.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    greeting_backdrop.no_depth_test = true
    greeting_backdrop.visible = false
    add_child(greeting_backdrop)

    greeting_bubble = Label3D.new()
    greeting_bubble.name = "GreetingText"
    greeting_bubble.text = "你好！"
    greeting_bubble.font = load("res://assets/fonts/NotoSansSC-UI.tres") as Font
    greeting_bubble.font_size = 49
    greeting_bubble.pixel_size = 0.0075
    greeting_bubble.outline_size = 0
    greeting_bubble.modulate = Color("#2D3150")
    greeting_bubble.position = Vector3(0, 3.16, 0.03)
    greeting_bubble.no_depth_test = true
    greeting_bubble.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    greeting_bubble.visible = false
    add_child(greeting_bubble)


# Lane A calls this at a low frequency from the village (not every NPC's
# physics tick). The collision body stays alive even when logic is asleep.
func configure_neighbors(others: Array[Node3D]) -> void:
    _cached_neighbors = others


# Only the village selects which two nearby, on-screen villagers may speak.
# Keep text and backdrop controlled together to avoid blank bubbles.
func set_greeting_enabled(enabled: bool) -> void:
    _greeting_enabled = enabled
    if greeting_bubble != null:
        greeting_bubble.visible = enabled
    if greeting_backdrop != null:
        greeting_backdrop.visible = enabled


func set_performance_lod(distance_to_player: float, in_camera: bool) -> void:
    # Greeting distance is allowed to wake logic even outside the camera:
    # a child approaching from behind must still get the hello bubble.
    var animate: bool = in_camera and distance_to_player <= 15.0
    var think: bool = distance_to_player <= GREETING_DISTANCE or animate
    if animate != _lod_animation_on:
        _lod_animation_on = animate
        if animation_player != null:
            animation_player.active = animate
    if think != _lod_physics_on:
        _lod_physics_on = think
        set_physics_process(think)
        if not think:
            velocity = Vector3.ZERO
            moving = false
            set_greeting_enabled(false)


func _physics_process(delta: float) -> void:
    elapsed += delta
    if not is_on_floor():
        velocity.y -= 14.0 * delta
    else:
        velocity.y = -0.1

    var player := get_parent().get_node_or_null("Player") as Node3D
    var nearby := player != null and global_position.distance_to(player.global_position) < GREETING_DISTANCE

    if nearby:
        # Pause and turn toward the approaching child; no forced interaction.
        var to_player: Vector3 = player.global_position - global_position
        to_player.y = 0.0
        if to_player.length_squared() > 0.04:
            rotation.y = lerp_angle(rotation.y, atan2(to_player.x, to_player.z), minf(delta * 6.0, 1.0))
        velocity.x = move_toward(velocity.x, 0.0, delta * 8.0)
        velocity.z = move_toward(velocity.z, 0.0, delta * 8.0)
        moving = false
    else:
        # Walk up/down a safe roadside lane; never target a building plot.
        # Each villager has a different idle phase to avoid marching in sync.
        var phase := fposmod(elapsed + float(get_index()) * 1.7, 10.0)
        moving = phase > 2.0 and phase < 7.0
        if absf(global_position.z - home.z) >= ROUTE_LENGTH:
            route_direction = -1.0 if global_position.z > home.z else 1.0
        var direction := Vector3(0.0, 0.0, route_direction)
        var blocked := false
        if moving:
            # Actual CharacterBody3D physics prevents crossing houses/props.
            blocked = test_move(global_transform, direction * WALK_SPEED * delta * 2.0)
            for villager in _cached_neighbors:
                if villager == self or not is_instance_valid(villager):
                    continue
                var offset: Vector3 = villager.global_position - global_position
                offset.y = 0.0
                if offset.length_squared() < AVOID_DISTANCE * AVOID_DISTANCE and offset.dot(direction) > 0.0:
                    blocked = true
                    break
        if blocked:
            route_direction = -route_direction
            moving = false
        velocity.x = move_toward(velocity.x, 0.0, delta * 5.0)
        velocity.z = move_toward(velocity.z, route_direction * WALK_SPEED if moving else 0.0, delta * 3.0)
        if moving:
            rotation.y = lerp_angle(rotation.y, atan2(0.0, route_direction), minf(delta * 7.0, 1.0))

    move_and_slide()
    if not _lod_animation_on:
        return
    MiniUtopiaKaykitAvatarV1.play(
        animation_player, "Walk" if moving and Vector2(velocity.x, velocity.z).length() > 0.05 else "Idle"
    )

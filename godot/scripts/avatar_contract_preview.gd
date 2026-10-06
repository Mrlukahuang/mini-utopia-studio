extends Node3D

const BODY_TYPES := [
    MiniUtopiaAvatarContract.BODY_SLIM,
    MiniUtopiaAvatarContract.BODY_STANDARD,
    MiniUtopiaAvatarContract.BODY_CHUBBY,
]

var _players: Array[AnimationPlayer] = []
var _status_label: Label
var _animation_index := 0
var _elapsed := 0.0


func _ready() -> void:
    _build_environment()
    _build_preview_stage()
    _build_hud()
    _probe_local_kaykit_animation_pack()


func _process(delta: float) -> void:
    _elapsed += delta
    if _elapsed < 2.8:
        return
    _elapsed = 0.0
    _animation_index = (
        _animation_index + 1
    ) % MiniUtopiaAvatarContract.BASE_ANIMATIONS.size()
    var animation_name: String = (
        MiniUtopiaAvatarContract.BASE_ANIMATIONS[_animation_index]
    )
    for player in _players:
        player.play(animation_name)
    if _status_label != null:
        _status_label.text = (
            "Shared animation contract · "
            + animation_name
            + " · Slim / Standard / Chubby"
        )


func _build_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color("#D9F0F7")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#FFF1D6")
    env.ambient_light_energy = 0.55
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-45.0, -30.0, 0.0)
    sun.light_energy = 0.95
    sun.shadow_enabled = true
    add_child(sun)

    var camera := Camera3D.new()
    camera.position = Vector3(0.0, 3.1, 8.6)
    camera.rotation_degrees = Vector3(-9.0, 0.0, 0.0)
    camera.current = true
    add_child(camera)

    var floor_body := StaticBody3D.new()
    floor_body.name = "PreviewFloor"
    floor_body.position = Vector3(0.0, -0.1, 0.0)
    add_child(floor_body)

    var floor_mesh := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = Vector3(12.0, 0.2, 5.5)
    floor_mesh.mesh = mesh
    floor_mesh.material_override = _material(Color("#F7F2E8"))
    floor_body.add_child(floor_mesh)


func _build_preview_stage() -> void:
    var positions := [-2.4, 0.0, 2.4]
    for index in range(BODY_TYPES.size()):
        var avatar := _build_avatar(
            BODY_TYPES[index],
            Vector3(positions[index], 0.0, 0.0)
        )
        add_child(avatar)


func _build_avatar(body_type: String, world_position: Vector3) -> Node3D:
    var root := Node3D.new()
    root.name = "Avatar_" + MiniUtopiaAvatarContract.body_label(body_type)
    root.position = world_position

    var visual := Node3D.new()
    visual.name = "Visual"
    root.add_child(visual)

    var width_scale := MiniUtopiaAvatarContract.body_width_scale(body_type)
    var head_scale := MiniUtopiaAvatarContract.head_width_scale(body_type)

    _add_box(
        visual,
        "Body",
        Vector3(0.0, 0.92, 0.0),
        Vector3(0.78 * width_scale, 0.92, 0.44 * width_scale),
        Color("#D7C2F3")
    )
    _add_sphere(
        visual,
        "SpeciesHead",
        Vector3(0.0, 1.72, 0.0),
        Vector3(0.70 * head_scale, 0.69, 0.67),
        Color("#F2C7A5")
    )
    _add_sphere(
        visual,
        "Hair",
        Vector3(0.0, 1.91, -0.02),
        Vector3(0.74 * head_scale, 0.31, 0.69),
        Color("#5B4036")
    )

    for side in [-1.0, 1.0]:
        _add_box(
            visual,
            "Arm",
            Vector3(0.52 * width_scale * side, 1.05, 0.0),
            Vector3(0.22, 0.72, 0.22),
            Color("#F2C7A5")
        )
        _add_box(
            visual,
            "Leg",
            Vector3(0.22 * side, 0.34, 0.0),
            Vector3(0.27, 0.68, 0.30),
            Color("#BFDFF5")
        )

    _add_sphere(
        visual,
        "EyeL",
        Vector3(-0.15 * head_scale, 1.76, 0.31),
        Vector3(0.10, 0.12, 0.08),
        Color("#7A5238")
    )
    _add_sphere(
        visual,
        "EyeR",
        Vector3(0.15 * head_scale, 1.76, 0.31),
        Vector3(0.10, 0.12, 0.08),
        Color("#7A5238")
    )

    var sockets := Node3D.new()
    sockets.name = "Sockets"
    root.add_child(sockets)
    MiniUtopiaAvatarContract.ensure_socket_nodes(sockets)
    _position_preview_sockets(sockets, width_scale)

    var label := Label3D.new()
    label.text = MiniUtopiaAvatarContract.body_label(body_type)
    label.position = Vector3(0.0, 2.48, 0.0)
    label.font_size = 40
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    root.add_child(label)

    var animation_player := _build_animation_player(root)
    _players.append(animation_player)
    animation_player.play(MiniUtopiaAvatarContract.ANIMATION_IDLE)

    return root


func _position_preview_sockets(sockets: Node3D, width_scale: float) -> void:
    var weapon_r := sockets.get_node(MiniUtopiaAvatarContract.SOCKET_WEAPON_R)
    weapon_r.position = Vector3(0.67 * width_scale, 0.90, 0.0)

    var weapon_l := sockets.get_node(MiniUtopiaAvatarContract.SOCKET_WEAPON_L)
    weapon_l.position = Vector3(-0.67 * width_scale, 0.90, 0.0)

    var backpack := sockets.get_node(MiniUtopiaAvatarContract.SOCKET_BACKPACK)
    backpack.position = Vector3(0.0, 1.12, -0.32)

    var wings := sockets.get_node(MiniUtopiaAvatarContract.SOCKET_WINGS)
    wings.position = Vector3(0.0, 1.34, -0.33)

    var accessory := sockets.get_node(MiniUtopiaAvatarContract.SOCKET_ACCESSORY)
    accessory.position = Vector3(0.30 * width_scale, 1.08, 0.26)

    var headwear := sockets.get_node(MiniUtopiaAvatarContract.SOCKET_HEADWEAR)
    headwear.position = Vector3(0.0, 2.34, 0.0)


func _build_animation_player(root: Node3D) -> AnimationPlayer:
    var player := AnimationPlayer.new()
    player.name = "AnimationPlayer"
    player.root_node = NodePath("..")
    root.add_child(player)

    var library := AnimationLibrary.new()
    library.add_animation(
        MiniUtopiaAvatarContract.ANIMATION_IDLE,
        _make_bob_animation(0.03, 1.8)
    )
    library.add_animation(
        MiniUtopiaAvatarContract.ANIMATION_WALK,
        _make_bob_animation(0.08, 0.72)
    )
    library.add_animation(
        MiniUtopiaAvatarContract.ANIMATION_RUN,
        _make_bob_animation(0.14, 0.42)
    )
    player.add_animation_library("", library)
    return player


func _make_bob_animation(amount: float, length: float) -> Animation:
    var animation := Animation.new()
    animation.length = length
    animation.loop_mode = Animation.LOOP_LINEAR

    var track := animation.add_track(Animation.TYPE_VALUE)
    animation.track_set_path(track, NodePath("Visual:position"))
    animation.track_insert_key(track, 0.0, Vector3.ZERO)
    animation.track_insert_key(
        track,
        length * 0.25,
        Vector3(0.0, amount, 0.0)
    )
    animation.track_insert_key(track, length * 0.50, Vector3.ZERO)
    animation.track_insert_key(
        track,
        length * 0.75,
        Vector3(0.0, amount, 0.0)
    )
    animation.track_insert_key(track, length, Vector3.ZERO)
    return animation


func _build_hud() -> void:
    var layer := CanvasLayer.new()
    add_child(layer)

    var panel := ColorRect.new()
    panel.position = Vector2(18.0, 18.0)
    panel.size = Vector2(760.0, 116.0)
    panel.color = Color(0.03, 0.06, 0.08, 0.78)
    layer.add_child(panel)

    var title := Label.new()
    title.position = Vector2(16.0, 10.0)
    title.text = (
        "AV-01 · Mini Utopia Humanoid Contract\n"
        + "One rig contract · Slim / Standard / Chubby · shared Idle / Walk / Run"
    )
    title.add_theme_font_size_override("font_size", 18)
    panel.add_child(title)

    _status_label = Label.new()
    _status_label.position = Vector2(16.0, 68.0)
    _status_label.text = "Shared animation contract · Idle"
    _status_label.add_theme_font_size_override("font_size", 15)
    panel.add_child(_status_label)


func _probe_local_kaykit_animation_pack() -> void:
    if not AssetVaultRuntime.is_installed():
        print("AV-01 probe: Asset Vault is not installed.")
        return

    var entries := AssetVaultRuntime.entries_matching(
        ["kaykit", "character", "animations"],
        ["rig_medium"]
    )
    if entries.is_empty():
        entries = AssetVaultRuntime.entries_matching(
            ["character", "animation"],
            ["rig_medium"]
        )

    if entries.is_empty():
        print(
            "AV-01 probe: KayKit Rig_Medium animations not detected. "
            + "Install the Character Animations ZIP into the local Asset Vault."
        )
        return

    entries.sort_custom(
        func(a: Dictionary, b: Dictionary) -> bool:
            return _animation_source_priority(
                String(a.get("source_member", ""))
            ) < _animation_source_priority(
                String(b.get("source_member", ""))
            )
    )

    print("AV-01 probe: primary rig = Rig_Medium")
    print("AV-01 probe: Rig_Medium animation sets found = ", entries.size())

    var best_skeleton_names: Array[String] = []
    var semantic_map := {
        "Idle": {},
        "Walk": {},
        "Run": {},
    }

    for entry in entries:
        var result := _inspect_animation_entry(entry)
        var skeleton_names: Array[String] = result.get("skeleton_names", [])
        if best_skeleton_names.is_empty() and not skeleton_names.is_empty():
            best_skeleton_names = skeleton_names

        var clips: Array[String] = result.get("clips", [])
        for semantic_name in semantic_map.keys():
            if not semantic_map[semantic_name].is_empty():
                continue
            var matched_clip := _best_semantic_clip(
                clips,
                String(semantic_name).to_lower()
            )
            if matched_clip.is_empty():
                continue
            semantic_map[semantic_name] = {
                "clip": matched_clip,
                "source_member": String(entry.get("source_member", "")),
            }

    if not best_skeleton_names.is_empty():
        print(
            "AV-01 probe: Rig_Medium skeleton bones = ",
            ", ".join(best_skeleton_names)
        )

    var all_found := true
    for semantic_name in ["Idle", "Walk", "Run"]:
        var mapping: Dictionary = semantic_map[semantic_name]
        if mapping.is_empty():
            all_found = false
            print(
                "AV-01 probe: ",
                semantic_name,
                " mapping = NOT FOUND"
            )
            continue
        print(
            "AV-01 probe: ",
            semantic_name,
            " mapping = ",
            mapping.get("clip", ""),
            " @ ",
            mapping.get("source_member", "")
        )

    print(
        "AV-01 probe: locomotion contract = ",
        "PASS" if all_found else "INCOMPLETE"
    )


func _inspect_animation_entry(entry: Dictionary) -> Dictionary:
    var res_path := String(entry.get("res_path", ""))
    if res_path.is_empty() or not ResourceLoader.exists(res_path):
        return {}

    var resource := ResourceLoader.load(res_path)
    if not resource is PackedScene:
        return {}

    var instance := (resource as PackedScene).instantiate()
    var skeleton_names: Array[String] = []
    var clips: Array[String] = []
    _collect_rig_details(instance, skeleton_names, clips)
    instance.queue_free()
    return {
        "skeleton_names": skeleton_names,
        "clips": clips,
    }


func _collect_rig_details(
    node: Node,
    skeleton_names: Array[String],
    clips: Array[String]
) -> void:
    if node is Skeleton3D and skeleton_names.is_empty():
        var skeleton := node as Skeleton3D
        for bone_index in range(skeleton.get_bone_count()):
            skeleton_names.append(skeleton.get_bone_name(bone_index))

    if node is AnimationPlayer:
        var animation_player := node as AnimationPlayer
        for clip_name in animation_player.get_animation_list():
            var clip_text := String(clip_name)
            if not clips.has(clip_text):
                clips.append(clip_text)

    for child in node.get_children():
        _collect_rig_details(child, skeleton_names, clips)


func _animation_source_priority(source_member: String) -> int:
    var lowered := source_member.to_lower()
    if lowered.contains("movementbasic"):
        return 0
    if lowered.contains("movement"):
        return 10
    if lowered.contains("general"):
        return 20
    if lowered.contains("combat"):
        return 100
    return 50


func _best_semantic_clip(clips: Array[String], needle: String) -> String:
    var best := ""
    var best_score := -100000

    for clip_name in clips:
        var lowered := clip_name.to_lower()
        if not lowered.contains(needle):
            continue

        var score := 0

        if lowered == needle:
            score += 1000

        if needle == "idle":
            if lowered.begins_with("idle"):
                score += 500
        elif needle == "walk":
            if lowered == "walking":
                score += 1000
            if lowered.begins_with("walking"):
                score += 500
        elif needle == "run":
            if lowered == "running":
                score += 1000
            if lowered.begins_with("running"):
                score += 500

        for bad_term in [
            "backward",
            "holding",
            "melee",
            "combat",
            "bow",
            "block",
            "crouch",
            "strafe",
            "kick",
            "punch",
            "attack",
        ]:
            if lowered.contains(bad_term):
                score -= 700

        # Prefer the simplest canonical variant when several forward clips exist.
        score -= clip_name.length()

        if score > best_score:
            best_score = score
            best = clip_name

    return best


func _add_box(
    parent: Node3D,
    node_name: String,
    position: Vector3,
    size: Vector3,
    color: Color
) -> void:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = position
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)


func _add_sphere(
    parent: Node3D,
    node_name: String,
    position: Vector3,
    scale_value: Vector3,
    color: Color
) -> void:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = position
    node.scale = scale_value
    var mesh := SphereMesh.new()
    mesh.radius = 0.5
    mesh.height = 1.0
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)


func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.88
    return material

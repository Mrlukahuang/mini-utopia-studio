extends SceneTree

# A-008: verify the original KayKit rigged Knight + selected equipment import.
const BASE := "res://assets/kaykit/adventurers/"


func _initialize() -> void:
    var knight := load(BASE + "Knight.glb") as PackedScene
    if knight == null:
        _fail("official Knight.glb did not import")
        return
    var actor := knight.instantiate()
    if actor == null:
        _fail("official Knight.glb could not instantiate")
        return
    var skeletons: Array[Skeleton3D] = []
    var players: Array[AnimationPlayer] = []
    _walk(actor, skeletons, players)
    if skeletons.is_empty() or skeletons[0].get_bone_count() < 15:
        _fail("Knight.glb is missing a real humanoid Skeleton3D")
        actor.free()
        return
    var animation_names: Array[String] = []
    for player in players:
        for animation_name in player.get_animation_list():
            animation_names.append(String(animation_name).to_lower())
    actor.free()
    if animation_names.size() < 4:
        _fail("Knight.glb has no usable bundled animations")
        return
    print("KayKit Knight validated: Skeleton3D and animations: ", animation_names)

    for item_name in ["sword_1handed", "shield_round", "staff", "wand"]:
        var scene := load(BASE + item_name + ".gltf") as PackedScene
        if scene == null:
            _fail("KayKit equipment import failed: " + item_name)
            return
        var model := scene.instantiate()
        if model == null:
            _fail("KayKit equipment instantiate failed: " + item_name)
            return
        model.free()
    print("kaykit_selected_assets_smoke: PASS")
    quit(0)


func _walk(node: Node, skeletons: Array[Skeleton3D], players: Array[AnimationPlayer]) -> void:
    if node is Skeleton3D:
        skeletons.append(node as Skeleton3D)
    if node is AnimationPlayer:
        players.append(node as AnimationPlayer)
    for child in node.get_children():
        _walk(child, skeletons, players)


func _fail(message: String) -> void:
    push_error("kaykit_selected_assets_smoke: FAIL · " + message)
    quit(1)

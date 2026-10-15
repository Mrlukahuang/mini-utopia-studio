extends SceneTree

# A-008 selected official KayKit equipment only; no family data.
func _initialize() -> void:
    for name in ["sword_1handed", "shield_round", "staff", "wand"]:
        var path := "res://assets/kaykit/adventurers/" + name + ".gltf"
        var scene := load(path) as PackedScene
        if scene == null:
            push_error("KayKit equipment import failed: " + name)
            quit(1)
            return
        var model := scene.instantiate()
        if model == null:
            push_error("KayKit equipment instantiate failed: " + name)
            quit(1)
            return
        model.free()
    print("kaykit_selected_assets_smoke: PASS")
    quit(0)

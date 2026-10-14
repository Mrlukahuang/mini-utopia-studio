extends SceneTree

func _initialize() -> void:
    var world := load("res://scenes/main.tscn") as PackedScene
    if world == null:
        _fail("main village scene is missing")
        return
    var scene := world.instantiate()
    root.add_child(scene)
    await process_frame

    var button := scene.get_node_or_null("HUD/OpenCreatorButton") as Button
    if button == null:
        _fail("child-facing Create Hero entrypoint is missing")
        return
    if button.text != "🎨 Create a Hero":
        _fail("Create Hero label is not child-facing")
        return
    if button.pressed.get_connections().is_empty():
        _fail("village Hero button does not trigger any runtime action")
        return
    if not ResourceLoader.exists("res://scenes/character_creator.tscn"):
        _fail("runtime Creator scene does not exist")
        return

    print("village_creator_entrypoint_smoke: PASS · game->Creator wired")
    quit(0)


func _fail(message: String) -> void:
    push_error("village_creator_entrypoint_smoke: FAIL · " + message)
    quit(1)

extends SceneTree

## iPad Creator gestures are sent directly to its GUI input handler;
## this makes zoom/rotation testable headlessly without a physical screen.

func _initialize() -> void:
    var packed := load("res://scenes/character_creator.tscn") as PackedScene
    if packed == null:
        _fail("Creator scene is missing")
        return
    var scene := packed.instantiate()
    root.add_child(scene)
    await process_frame

    var stage := scene.get_node_or_null(
        "RootMargin/MainColumn/CreatorBody/PreviewPanel/AvatarStage"
    ) as MiniUtopiaCreatorAvatarStage
    if stage == null:
        _fail("3D Avatar stage is missing")
        return
    var identity := stage.avatar_root_instance_id()
    var yaw_before := stage.avatar_root().rotation.y

    stage.call("_on_gui_input", _touch(0, true, Vector2(100, 150)))
    stage.call("_on_gui_input", _drag(0, Vector2(160, 150), Vector2(60, 0)))
    if is_equal_approx(yaw_before, stage.avatar_root().rotation.y):
        _fail("single finger did not rotate the same AvatarRoot")
        return
    if stage.active_touch_count() != 1:
        _fail("one active finger should be tracked")
        return

    var before_pinch := stage.camera_distance()
    stage.call("_on_gui_input", _touch(1, true, Vector2(260, 150)))
    stage.call("_on_gui_input", _drag(1, Vector2(320, 150), Vector2(60, 0)))
    if stage.camera_distance() >= before_pinch:
        _fail("spreading fingers did not zoom in")
        return

    var before_reverse := stage.camera_distance()
    stage.call("_on_gui_input", _drag(1, Vector2(280, 150), Vector2(-40, 0)))
    if stage.camera_distance() <= before_reverse:
        _fail("closing fingers did not zoom out")
        return

    stage.call("_on_gui_input", _touch(1, false, Vector2(280, 150)))
    if stage.active_touch_count() != 1:
        _fail("lifting a finger should resume one-finger mode")
        return
    stage.call("_on_gui_input", _touch(0, false, Vector2(160, 150)))
    if stage.active_touch_count() != 0:
        _fail("all touch IDs must be released")
        return
    if stage.avatar_root_instance_id() != identity:
        _fail("touch gestures recreated the canonical Hero")
        return

    print("creator_touch_gestures_smoke: PASS · orbit, pinch, release")
    quit(0)


func _touch(index: int, pressed: bool, position: Vector2) -> InputEventScreenTouch:
    var event := InputEventScreenTouch.new()
    event.index = index
    event.pressed = pressed
    event.position = position
    return event


func _drag(index: int, position: Vector2, movement: Vector2) -> InputEventScreenDrag:
    var event := InputEventScreenDrag.new()
    event.index = index
    event.position = position
    event.relative = movement
    return event


func _fail(message: String) -> void:
    push_error("creator_touch_gestures_smoke: FAIL · " + message)
    quit(1)

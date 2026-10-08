extends SceneTree


func _initialize() -> void:
    var packed := load("res://scenes/character_creator.tscn") as PackedScene
    if packed == null:
        _fail("Character Creator scene is missing")
        return

    var scene := packed.instantiate()
    root.add_child(scene)
    await process_frame

    var stage := scene.get_node(
        "RootMargin/MainColumn/CreatorBody/PreviewPanel/AvatarStage"
    ) as MiniUtopiaCreatorAvatarStage
    var controls := scene.get_node(
        "RootMargin/MainColumn/CreatorBody/PreviewPanel/AnimationControls"
    ) as HBoxContainer

    var first_root_id := stage.avatar_root_instance_id()
    var appearance_before := stage.current_appearance()
    var visual := stage.avatar_root().get_node("Visual") as Node3D
    var arm_l := visual.get_node("ArmL") as MeshInstance3D

    if stage.current_preview_animation() != "Idle":
        _fail("Creator animation preview should start at Idle")
        return

    (controls.get_node("WalkButton") as Button).pressed.emit()
    stage.advance_preview_for_test(0.25)
    if stage.current_preview_animation() != "Walk":
        _fail("Walk button did not select Walk")
        return
    if abs(arm_l.rotation.x) < 0.01:
        _fail("Walk preview did not move limbs")
        return

    (controls.get_node("RunButton") as Button).pressed.emit()
    stage.advance_preview_for_test(0.17)
    if stage.current_preview_animation() != "Run":
        _fail("Run button did not select Run")
        return
    if visual.position.y <= 0.0:
        _fail("Run preview did not bob the Avatar")
        return

    (controls.get_node("JumpButton") as Button).pressed.emit()
    stage.advance_preview_for_test(0.30)
    if stage.current_preview_animation() != "Jump":
        _fail("Jump button did not select Jump")
        return
    if visual.position.y < 0.25:
        _fail("Jump preview did not lift the Avatar")
        return

    (controls.get_node("IdleButton") as Button).pressed.emit()
    stage.advance_preview_for_test(0.10)
    if stage.current_preview_animation() != "Idle":
        _fail("Idle button did not restore Idle")
        return
    if abs(arm_l.rotation.x) > 0.001:
        _fail("Idle did not reset limb pose")
        return

    if stage.avatar_root_instance_id() != first_root_id:
        _fail("animation switching recreated AvatarRoot")
        return
    if stage.current_appearance() != appearance_before:
        _fail("animation preview changed canonical appearance")
        return

    print(
        "character_creator_animation_controls_smoke: PASS · "
        + "Idle/Walk/Run/Jump switch instantly on one AvatarRoot"
    )
    quit(0)


func _fail(message: String) -> void:
    push_error(
        "character_creator_animation_controls_smoke: FAIL · %s" % message
    )
    quit(1)

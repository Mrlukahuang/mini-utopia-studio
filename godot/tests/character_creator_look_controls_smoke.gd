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
    var first_root_id := stage.avatar_root_instance_id()

    var body_row := scene.get_node(
        "RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Content/BodyRow"
    )
    var species_grid := scene.get_node(
        "RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Content/SpeciesGrid"
    )
    var surface_grid := scene.get_node(
        "RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Content/SurfaceGrid"
    )

    (body_row.get_node("ChubbyButton") as Button).pressed.emit()
    var appearance := stage.current_appearance()
    if appearance.get("body_type") != "chubby":
        _fail("Chubby click did not update the live Avatar")
        return

    (species_grid.get_node("CatButton") as Button).pressed.emit()
    appearance = stage.current_appearance()
    if appearance.get("species_head_id") != "species_head_cat_v1":
        _fail("Cat click did not update Species")
        return
    if appearance.get("surface_type") != "fur":
        _fail("Cat did not normalize Surface to fur")
        return

    var skin_button := surface_grid.get_node("SkinButton") as Button
    var fur_button := surface_grid.get_node("FurButton") as Button
    if not skin_button.disabled:
        _fail("invalid Cat skin surface remained enabled")
        return
    if fur_button.disabled:
        _fail("valid Cat fur surface was disabled")
        return

    (species_grid.get_node("SheepButton") as Button).pressed.emit()
    appearance = stage.current_appearance()
    if appearance.get("surface_type") != "fur":
        _fail("Sheep should preserve already-compatible fur")
        return

    var wool_button := surface_grid.get_node("WoolButton") as Button
    if wool_button.disabled:
        _fail("valid Sheep wool surface was disabled")
        return
    wool_button.pressed.emit()
    appearance = stage.current_appearance()
    if appearance.get("surface_type") != "wool":
        _fail("valid Sheep wool choice did not apply")
        return

    if stage.avatar_root_instance_id() != first_root_id:
        _fail("look controls recreated AvatarRoot")
        return

    var zoom_in := scene.get_node(
        "RootMargin/MainColumn/CreatorBody/PreviewPanel/ZoomControls/ZoomInButton"
    ) as Button
    var reset := scene.get_node(
        "RootMargin/MainColumn/CreatorBody/PreviewPanel/ZoomControls/ResetButton"
    ) as Button

    var before_zoom := stage.camera_distance()
    zoom_in.pressed.emit()
    if stage.camera_distance() >= before_zoom:
        _fail("on-screen Zoom + did not move camera closer")
        return

    reset.pressed.emit()
    if abs(stage.camera_distance() - 6.2) > 0.001:
        _fail("Reset did not restore Creator camera")
        return

    print(
        "character_creator_look_controls_smoke: PASS · "
        + "Body/Species/Surface/Zoom mutate the persistent Avatar instantly"
    )
    quit(0)


func _fail(message: String) -> void:
    push_error("character_creator_look_controls_smoke: FAIL · %s" % message)
    quit(1)

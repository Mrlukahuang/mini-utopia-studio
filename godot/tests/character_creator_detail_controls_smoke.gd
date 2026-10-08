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

    var scroll := scene.get_node_or_null(
        "RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll"
    ) as ScrollContainer
    if scroll == null:
        _fail("720p Creator controls are not scrollable")
        return

    var base := (
        "RootMargin/MainColumn/CreatorBody/ChoicePanel/"
        + "Margin/Scroll/Content/"
    )
    var species_grid := scene.get_node(base + "SpeciesGrid")
    var eye_option := scene.get_node(base + "EyeStyleOption") as OptionButton
    var hair_option := scene.get_node(base + "HairStyleOption") as OptionButton
    var color_target := scene.get_node(base + "ColorTargetOption") as OptionButton
    var color_grid := scene.get_node(base + "ColorGrid")

    (species_grid.get_node("CatButton") as Button).pressed.emit()

    if eye_option.item_count != 3:
        _fail("Cat Eye compatibility list was not rebuilt")
        return
    if hair_option.item_count != 6:
        _fail("Cat Hair compatibility list was not rebuilt")
        return

    eye_option.select(0)
    eye_option.item_selected.emit(0)
    hair_option.select(2)
    hair_option.item_selected.emit(2)

    var appearance := stage.current_appearance()
    if appearance.get("eye_style_id") != "eyes_cat_v1":
        _fail("Eye Style did not update instantly")
        return
    if appearance.get("hair_style_id") != "hair_bob_v1":
        _fail("Hair Style did not update instantly")
        return

    (color_grid.get_node("PinkButton") as Button).pressed.emit()
    appearance = stage.current_appearance()
    if appearance.get("surface_color_hex") != "#F7B7D2":
        _fail("Surface color target did not update")
        return

    color_target.select(1)
    color_target.item_selected.emit(1)
    (color_grid.get_node("SkyButton") as Button).pressed.emit()
    appearance = stage.current_appearance()
    if appearance.get("eye_color_hex") != "#BDE3F5":
        _fail("Eye color target did not update")
        return
    if appearance.get("surface_color_hex") != "#F7B7D2":
        _fail("Eye color edit changed Surface color")
        return

    color_target.select(2)
    color_target.item_selected.emit(2)
    (color_grid.get_node("GoldButton") as Button).pressed.emit()
    appearance = stage.current_appearance()
    if appearance.get("hair_color_hex") != "#F2C75C":
        _fail("Hair color target did not update")
        return

    (species_grid.get_node("RobotButton") as Button).pressed.emit()
    appearance = stage.current_appearance()
    if appearance.get("eye_style_id") != "eyes_robot_v1":
        _fail("Robot did not normalize incompatible Cat Eyes")
        return
    if appearance.get("hair_style_id") != "hair_none":
        _fail("Robot did not normalize incompatible Bob Hair")
        return
    if eye_option.item_count != 2:
        _fail("Robot Eye compatibility list is wrong")
        return
    if hair_option.item_count != 3:
        _fail("Robot Hair compatibility list is wrong")
        return

    if stage.avatar_root_instance_id() != first_root_id:
        _fail("detail editing recreated AvatarRoot")
        return

    print(
        "character_creator_detail_controls_smoke: PASS · "
        + "Hair/Eyes/Colors mutate one persistent AvatarRoot"
    )
    quit(0)


func _fail(message: String) -> void:
    push_error("character_creator_detail_controls_smoke: FAIL · %s" % message)
    quit(1)

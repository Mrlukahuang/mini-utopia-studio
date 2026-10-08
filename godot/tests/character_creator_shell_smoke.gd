extends SceneTree


func _initialize() -> void:
    var packed := load("res://scenes/character_creator.tscn") as PackedScene
    if packed == null:
        _fail("Character Creator scene is missing")
        return

    var scene := packed.instantiate()
    root.add_child(scene)
    await process_frame

    if scene.name != "CharacterCreator":
        _fail("unexpected root node name")
        return

    var required := [
        "RootMargin/MainColumn/HeaderRow/CharacterLabel",
        "RootMargin/MainColumn/StepTabs/LookStep",
        "RootMargin/MainColumn/StepTabs/PersonalityStep",
        "RootMargin/MainColumn/StepTabs/OutfitStep",
        "RootMargin/MainColumn/StepTabs/ReadyStep",
        "RootMargin/MainColumn/CreatorBody/ChoicePanel",
        "RootMargin/MainColumn/CreatorBody/PreviewPanel",
        "RootMargin/MainColumn/StatusBar/StatusLabel",
        "RootMargin/MainColumn/FooterRow/BackButton",
        "RootMargin/MainColumn/FooterRow/SaveButton",
        "BridgeClient",
    ]
    for path in required:
        if scene.get_node_or_null(path) == null:
            _fail("missing child-facing Creator node: %s" % path)
            return

    var save_button := scene.get_node(
        "RootMargin/MainColumn/FooterRow/SaveButton"
    ) as Button
    var back_button := scene.get_node(
        "RootMargin/MainColumn/FooterRow/BackButton"
    ) as Button
    var status_label := scene.get_node(
        "RootMargin/MainColumn/StatusBar/StatusLabel"
    ) as Label

    if save_button.text != "💖 Save My Hero":
        _fail("Save action is not child-facing")
        return
    if back_button.text != "← Back":
        _fail("Back action is missing")
        return
    if status_label.text.is_empty():
        _fail("Creator status is empty")
        return

    print(
        "character_creator_shell_smoke: PASS · "
        + "runtime Creator shell loaded without Godot Editor UI"
    )
    quit(0)


func _fail(message: String) -> void:
    push_error("character_creator_shell_smoke: FAIL · %s" % message)
    quit(1)

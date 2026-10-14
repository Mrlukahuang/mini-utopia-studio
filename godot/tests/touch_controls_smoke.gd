extends SceneTree

## Validates touch controls without needing a physical iPad or mock browser.
## Real Safari responsiveness still requires final physical-device acceptance.
func _initialize() -> void:
    var controls := MiniUtopiaTouchControls.new()
    controls.force_visible = true
    root.add_child(controls)
    _verify.call_deferred(controls)


func _verify(controls: MiniUtopiaTouchControls) -> void:
    await process_frame

    var directions := {
        "MoveForward": "move_forward",
        "MoveLeft": "move_left",
        "MoveBack": "move_back",
        "MoveRight": "move_right",
        "Jump": "jump",
        "Interact": "interact",
    }
    for button_name in directions:
        var button := controls.get_node_or_null(
            "Overlay/" + button_name
        ) as Button
        if button == null:
            push_error("touch_controls_smoke: missing " + button_name)
            quit(1)
            return
        var action: String = directions[button_name]
        button.button_down.emit()
        if not Input.is_action_pressed(action):
            push_error("touch_controls_smoke: action press failed: " + action)
            quit(1)
            return
        button.button_up.emit()
        if Input.is_action_pressed(action):
            push_error("touch_controls_smoke: action release failed: " + action)
            quit(1)
            return

    # No sticky movement on window focus loss (or UI teardown).
    controls._press_action("move_forward")
    controls._release_all_actions()
    if Input.is_action_pressed("move_forward"):
        push_error("touch_controls_smoke: stuck movement")
        quit(1)
        return

    print("touch_controls_smoke: PASS · 6 touch controls and release contract")
    quit(0)

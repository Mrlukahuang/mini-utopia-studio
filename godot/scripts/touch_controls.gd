extends CanvasLayer
class_name MiniUtopiaTouchControls

## Touch-first runtime controls for the playable village.
## Visible on touchscreen devices; optionally forced in headless tests.
## This is not a second input model: buttons issue the same Input actions as
## keyboard/gamepad controls, so gameplay logic and shared Hero stay unchanged.

@export var force_visible := false

var _overlay: Control
var _held_actions: Dictionary = {}


func _ready() -> void:
    if not force_visible and not DisplayServer.is_touchscreen_available():
        visible = false
        return
    _build_controls()
    _replace_keyboard_help()


func _build_controls() -> void:
    if _overlay != null:
        return

    _overlay = Control.new()
    _overlay.name = "Overlay"
    _overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
    add_child(_overlay)
    _overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

    # Four directions at bottom-left; large enough for fingers.
    _make_button("MoveForward", "▲", "move_forward", false, Vector2(100, -208), Vector2(72, 72))
    _make_button("MoveLeft", "◀", "move_left", false, Vector2(20, -132), Vector2(72, 72))
    _make_button("MoveBack", "▼", "move_back", false, Vector2(100, -132), Vector2(72, 72))
    _make_button("MoveRight", "▶", "move_right", false, Vector2(180, -132), Vector2(72, 72))
    # Leave the center-right free for a one-finger camera drag.
    _make_button("Jump", "跳跃", "jump", true, Vector2(-154, -128), Vector2(112, 72))
    _make_button("Interact", "互动", "interact", true, Vector2(-154, -216), Vector2(112, 72))


func _make_button(
    button_name: String,
    caption: String,
    action: String,
    right_side: bool,
    offset: Vector2,
    size: Vector2
) -> void:
    var button := Button.new()
    button.name = button_name
    button.text = caption
    button.focus_mode = Control.FOCUS_NONE
    button.mouse_filter = Control.MOUSE_FILTER_STOP
    button.keep_pressed_outside = true
    button.clip_text = true
    button.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
    button.add_theme_font_size_override("font_size", 23)
    button.anchor_left = 1.0 if right_side else 0.0
    button.anchor_right = 1.0 if right_side else 0.0
    button.anchor_top = 1.0
    button.anchor_bottom = 1.0
    button.offset_left = offset.x
    button.offset_top = offset.y
    button.offset_right = offset.x + size.x
    button.offset_bottom = offset.y + size.y
    button.button_down.connect(_press_action.bind(action))
    button.button_up.connect(_release_action.bind(action))
    _overlay.add_child(button)


func _press_action(action: String) -> void:
    if _held_actions.has(action):
        return
    _held_actions[action] = true
    Input.action_press(action)


func _release_action(action: String) -> void:
    if not _held_actions.has(action):
        return
    _held_actions.erase(action)
    Input.action_release(action)


func _release_all_actions() -> void:
    for action in _held_actions.keys():
        Input.action_release(String(action))
    _held_actions.clear()


func _notification(what: int) -> void:
    if what == NOTIFICATION_WM_WINDOW_FOCUS_OUT:
        _release_all_actions()


func _exit_tree() -> void:
    _release_all_actions()


func _replace_keyboard_help() -> void:
    var label := get_parent().get_node_or_null("HUD/Panel/Help") as Label
    if label != null:
        label.text = "左侧方向键移动 · 右侧滑动转动镜头\n跳跃 / 互动 · 随时探索"

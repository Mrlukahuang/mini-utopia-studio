extends CanvasLayer
# Lane B ambient scene-entry fade. The layer survives scene swaps without
# editing Lane A/C scene navigation or delaying existing button actions.
const FADE_SECONDS := 0.32
var veil: ColorRect

func _ready() -> void:
    layer = 90
    veil = ColorRect.new()
    veil.name = "PastelFade"
    veil.color = Color("#FFF1E6")
    veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
    veil.modulate.a = 0.0
    add_child(veil)
    veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    call_deferred("_install_at_root")


func _install_at_root() -> void:
    if not is_inside_tree():
        return
    var root := get_tree().root
    if root.has_node("MiniUtopiaSceneFade"):
        queue_free()
        return
    reparent(root)
    name = "MiniUtopiaSceneFade"
    get_tree().scene_changed.connect(_on_scene_changed)
    get_tree().node_added.connect(_on_node_added)
    _wire_existing_buttons(root)


func _on_scene_changed(_scene: Node) -> void:
    if not is_inside_tree():
        return
    veil.modulate.a = 0.94
    var tween := create_tween()
    tween.tween_property(veil, "modulate:a", 0.0, FADE_SECONDS).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)


# A single root-level watcher gives inherited Button styling tactile motion
# across Home / Creator / My Heroes / Director without editing other lanes.
func _wire_existing_buttons(node: Node) -> void:
    if node is BaseButton:
        _wire_button(node as BaseButton)
    for child in node.get_children():
        _wire_existing_buttons(child)


func _on_node_added(node: Node) -> void:
    if node is BaseButton:
        _wire_button.call_deferred(node)


func _wire_button(button: BaseButton) -> void:
    if not is_instance_valid(button) or not button.is_inside_tree():
        return
    if button.has_meta("mini_utopia_bounce_bound"):
        return
    button.set_meta("mini_utopia_bounce_bound", true)
    button.button_down.connect(_on_button_down.bind(button))
    button.button_up.connect(_on_button_up.bind(button))
    button.mouse_exited.connect(_on_button_up.bind(button))


func _on_button_down(button: BaseButton) -> void:
    if button.disabled:
        return
    _animate_button(button, Vector2(0.96, 0.96), 0.09, Tween.TRANS_SINE)


func _on_button_up(button: BaseButton) -> void:
    _animate_button(button, Vector2.ONE, 0.19, Tween.TRANS_BACK)


func _animate_button(button: BaseButton, target: Vector2, duration: float, transition: Tween.TransitionType) -> void:
    if not is_instance_valid(button) or not button.is_inside_tree():
        return
    var prior = button.get_meta("mini_utopia_bounce_tween", null)
    if prior is Tween and prior.is_running():
        prior.kill()
    button.pivot_offset = button.size * 0.5
    var tween := button.create_tween()
    tween.tween_property(button, "scale", target, duration).set_trans(transition).set_ease(Tween.EASE_OUT)
    button.set_meta("mini_utopia_bounce_tween", tween)

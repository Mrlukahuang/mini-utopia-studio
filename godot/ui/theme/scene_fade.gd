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
    veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    veil.modulate.a = 0.0
    add_child(veil)
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


func _on_scene_changed(_scene: Node) -> void:
    if not is_inside_tree():
        return
    veil.modulate.a = 0.94
    var tween := create_tween()
    tween.tween_property(veil, "modulate:a", 0.0, FADE_SECONDS).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)

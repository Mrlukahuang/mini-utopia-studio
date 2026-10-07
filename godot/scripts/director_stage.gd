extends Node3D

var director_runtime: MiniUtopiaDirectorShotRuntime
var status_label: Label


func _ready() -> void:
    _build_environment()
    _build_overlay()

    director_runtime = MiniUtopiaDirectorShotRuntime.new()
    director_runtime.name = "DirectorShotRuntime"
    add_child(director_runtime)

    var payload := director_runtime.load_default_session()
    if payload.is_empty():
        _show_missing_payload()
        return

    stage_payload(payload)


func stage_payload(payload: Dictionary) -> void:
    if director_runtime == null:
        director_runtime = MiniUtopiaDirectorShotRuntime.new()
        director_runtime.name = "DirectorShotRuntime"
        add_child(director_runtime)

    director_runtime.configure(payload)
    _show_ready(payload)


func _build_environment() -> void:
    var environment := Environment.new()
    environment.background_mode = Environment.BG_COLOR
    environment.background_color = Color("#DCEBFF")
    environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.ambient_light_color = Color("#FFF8EC")
    environment.ambient_light_energy = 1.25

    var world_environment := WorldEnvironment.new()
    world_environment.name = "DirectorWorldEnvironment"
    world_environment.environment = environment
    add_child(world_environment)

    var key_light := DirectionalLight3D.new()
    key_light.name = "DirectorKeyLight"
    key_light.rotation_degrees = Vector3(-52.0, -28.0, 0.0)
    key_light.light_energy = 1.45
    key_light.shadow_enabled = true
    add_child(key_light)

    var fill_light := DirectionalLight3D.new()
    fill_light.name = "DirectorFillLight"
    fill_light.rotation_degrees = Vector3(-25.0, 145.0, 0.0)
    fill_light.light_energy = 0.55
    add_child(fill_light)


func _build_overlay() -> void:
    var layer := CanvasLayer.new()
    layer.name = "DirectorStageOverlay"
    add_child(layer)

    var panel := PanelContainer.new()
    panel.name = "StatusPanel"
    panel.position = Vector2(24.0, 24.0)
    panel.custom_minimum_size = Vector2(560.0, 118.0)
    layer.add_child(panel)

    var margin := MarginContainer.new()
    margin.name = "StatusMargin"
    margin.add_theme_constant_override("margin_left", 18)
    margin.add_theme_constant_override("margin_right", 18)
    margin.add_theme_constant_override("margin_top", 14)
    margin.add_theme_constant_override("margin_bottom", 14)
    panel.add_child(margin)

    status_label = Label.new()
    status_label.name = "StatusLabel"
    status_label.text = "🎬 Director Stage / 导演模式"
    status_label.add_theme_font_size_override("font_size", 18)
    margin.add_child(status_label)


func _show_missing_payload() -> void:
    if status_label == null:
        return
    status_label.text = (
        "🎬 Director Stage / 导演模式\n"
        + "⚠️ No Director payload found.\n"
        + "Return to Mini Utopia → Episodes → Stage Shot first."
    )
    push_warning(
        "DIR-04B: no director_shot_session.json; Stage Shot in Creator first."
    )


func _show_ready(payload: Dictionary) -> void:
    if status_label == null:
        return

    var camera_payload = payload.get("camera", {})
    var camera_text := ""
    if typeof(camera_payload) == TYPE_DICTIONARY:
        camera_text = String(camera_payload.get("movement", ""))

    status_label.text = (
        "🎬 Director Stage / 导演模式"
        + "\n"
        + String(payload.get("scene_id", "—"))
        + " · "
        + String(payload.get("shot_id", "—"))
        + " · "
        + String(payload.get("animation_intent", "idle")).capitalize()
        + " · "
        + str(float(payload.get("duration_seconds", 0.0)))
        + "s"
        + "\n🎥 "
        + camera_text
    )

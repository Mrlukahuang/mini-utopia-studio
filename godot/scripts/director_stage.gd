extends Node3D

var director_runtime: MiniUtopiaDirectorShotRuntime
var status_label: Label
var child_choice_buttons: Dictionary = {}
var fallback_world_environment: WorldEnvironment
var fallback_environment_resource: Environment
var fallback_key_light: DirectionalLight3D
var fallback_fill_light: DirectionalLight3D


func _ready() -> void:
    _build_environment()
    _build_overlay()

    director_runtime = MiniUtopiaDirectorShotRuntime.new()
    director_runtime.name = "DirectorShotRuntime"
    add_child(director_runtime)

    var selection := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if selection != null:
        var family_payload := _current_family_payload()
        if not family_payload.is_empty():
            _build_child_director_controls()
            stage_payload(family_payload)
            return

    var payload := director_runtime.load_default_session()
    if payload.is_empty():
        _show_missing_payload()
        return

    stage_payload(payload)


func _current_family_payload() -> Dictionary:
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null:
        return {}
    var first := family.active_play_session()
    if first.is_empty():
        return {}
    var second := family.second_cast_play_session()
    var stage := (
        MiniUtopiaFamilyDirectorSession.from_two_play_sessions(first, second)
        if not second.is_empty()
        else MiniUtopiaFamilyDirectorSession.from_play_session(first)
    )
    return MiniUtopiaFamilyDirectorSession.with_child_choices(
        stage, family.director_shot_choices
    )


func _build_child_director_controls() -> void:
    var overlay := get_node_or_null("DirectorStageOverlay") as CanvasLayer
    if overlay == null:
        return
    var controls := VBoxContainer.new()
    controls.name = "KidDirectorChoices"
    controls.position = Vector2(24, 170)
    controls.add_theme_constant_override("separation", 8)
    overlay.add_child(controls)
    var title := Label.new()
    title.text = "🎥 My Movie / 我来当导演"
    title.add_theme_font_size_override("font_size", 21)
    controls.add_child(title)
    for key in ["camera", "action", "duration_seconds"]:
        var button := Button.new()
        button.name = "Choice_" + key
        button.custom_minimum_size = Vector2(238, 54)
        button.add_theme_font_size_override("font_size", 18)
        button.pressed.connect(_cycle_child_choice.bind(key))
        controls.add_child(button)
        child_choice_buttons[key] = button
    _refresh_choice_labels()


func _refresh_choice_labels() -> void:
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null:
        return
    var choices := family.director_shot_choices
    var camera_button: Button = child_choice_buttons.get("camera")
    var action_button: Button = child_choice_buttons.get("action")
    var length_button: Button = child_choice_buttons.get("duration_seconds")
    if camera_button != null:
        camera_button.text = "📷 Camera: " + String(choices.get("camera", "follow")).capitalize()
    if action_button != null:
        action_button.text = "🎭 Action: " + String(choices.get("action", "walk")).capitalize()
    if length_button != null:
        length_button.text = "⏱️ Length: " + str(int(choices.get("duration_seconds", 15))) + "s"


func _cycle_child_choice(key: String) -> void:
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null or not child_choice_buttons.has(key):
        return
    var options: Array = []
    match key:
        "camera":
            options = ["follow", "wide", "close"]
        "action":
            options = ["walk", "run", "celebrate"]
        "duration_seconds":
            options = [15, 30]
        _:
            return
    var old_value = family.director_shot_choices.get(key, options[0])
    var index := options.find(old_value)
    family.director_shot_choices[key] = options[(index + 1) % options.size()]
    _refresh_choice_labels()
    var shot := _current_family_payload()
    if shot.is_empty():
        return
    if director_runtime != null:
        remove_child(director_runtime)
        director_runtime.free()
        director_runtime = null
    stage_payload(shot)


func stage_payload(payload: Dictionary) -> void:
    if director_runtime == null:
        director_runtime = MiniUtopiaDirectorShotRuntime.new()
        director_runtime.name = "DirectorShotRuntime"
        add_child(director_runtime)

    director_runtime.configure(payload)
    _set_fallback_environment_enabled(
        not director_runtime.bound_world_loaded
    )
    _show_ready(payload)


func _build_environment() -> void:
    fallback_environment_resource = Environment.new()
    fallback_environment_resource.background_mode = Environment.BG_COLOR
    fallback_environment_resource.background_color = Color("#DCEBFF")
    fallback_environment_resource.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    fallback_environment_resource.ambient_light_color = Color("#FFF8EC")
    fallback_environment_resource.ambient_light_energy = 1.25

    fallback_world_environment = WorldEnvironment.new()
    fallback_world_environment.name = "DirectorWorldEnvironment"
    fallback_world_environment.environment = fallback_environment_resource
    add_child(fallback_world_environment)

    fallback_key_light = DirectionalLight3D.new()
    fallback_key_light.name = "DirectorKeyLight"
    fallback_key_light.rotation_degrees = Vector3(-52.0, -28.0, 0.0)
    fallback_key_light.light_energy = 1.45
    fallback_key_light.shadow_enabled = true
    add_child(fallback_key_light)

    fallback_fill_light = DirectionalLight3D.new()
    fallback_fill_light.name = "DirectorFillLight"
    fallback_fill_light.rotation_degrees = Vector3(-25.0, 145.0, 0.0)
    fallback_fill_light.light_energy = 0.55
    add_child(fallback_fill_light)


func _set_fallback_environment_enabled(enabled: bool) -> void:
    if fallback_world_environment != null:
        fallback_world_environment.environment = (
            fallback_environment_resource
            if enabled
            else null
        )
    if fallback_key_light != null:
        fallback_key_light.visible = enabled
    if fallback_fill_light != null:
        fallback_fill_light.visible = enabled


func _build_overlay() -> void:
    var layer := CanvasLayer.new()
    layer.name = "DirectorStageOverlay"
    add_child(layer)

    var panel := PanelContainer.new()
    panel.name = "StatusPanel"
    panel.position = Vector2(24.0, 24.0)
    panel.custom_minimum_size = Vector2(560.0, 118.0)
    layer.add_child(panel)

    var buttons := HBoxContainer.new()
    buttons.name = "DirectorControls"
    buttons.set_anchors_preset(Control.PRESET_TOP_RIGHT)
    buttons.offset_left = -390.0
    buttons.offset_right = -20.0
    buttons.offset_top = 24.0
    buttons.offset_bottom = 78.0
    buttons.add_theme_constant_override("separation", 10)
    layer.add_child(buttons)

    var replay := Button.new()
    replay.name = "ReplayButton"
    replay.text = "↻ Replay"
    replay.custom_minimum_size = Vector2(160.0, 54.0)
    replay.add_theme_font_size_override("font_size", 20)
    replay.pressed.connect(_on_replay_pressed)
    buttons.add_child(replay)

    var home := Button.new()
    home.name = "BackToVillageButton"
    home.text = "← Village"
    home.custom_minimum_size = Vector2(185.0, 54.0)
    home.add_theme_font_size_override("font_size", 20)
    home.pressed.connect(_on_back_to_village_pressed)
    buttons.add_child(home)

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


func _on_replay_pressed() -> void:
    if director_runtime != null:
        director_runtime.reset_shot()


func _on_back_to_village_pressed() -> void:
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    get_tree().change_scene_to_file("res://scenes/main.tscn")


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

    var world_line := "Fallback Stage"
    if director_runtime != null and director_runtime.bound_world_loaded:
        world_line = "Real World · " + director_runtime.bound_scene_path
    elif director_runtime != null and not director_runtime.world_load_error.is_empty():
        world_line = "Fallback · " + director_runtime.world_load_error

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
        + "\n🌍 "
        + world_line
    )

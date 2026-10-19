extends Node3D

var director_runtime: MiniUtopiaDirectorShotRuntime
var status_label: Label
var child_choice_buttons: Dictionary = {}
var film_bridge: MiniUtopiaBridgeClient
var film_title_input: LineEdit
var film_note_input: LineEdit
var save_film_button: Button
var record_voice_button: Button
var music_preview: MiniUtopiaFamilyMusicPreview
var voice_recorder: MiniUtopiaFamilyVoiceRecorder
var saved_film_id := ""
var saved_film_revision := ""
var voice_refresh_blocked := false
var fallback_world_environment: WorldEnvironment
var fallback_environment_resource: Environment
var fallback_key_light: DirectionalLight3D
var fallback_fill_light: DirectionalLight3D


func _ready() -> void:
    _build_environment()
    _build_overlay()

    film_bridge = MiniUtopiaBridgeClient.new()
    film_bridge.name = "DirectorFamilyFilmBridge"
    add_child(film_bridge)
    film_bridge.request_succeeded.connect(_on_film_bridge_success)
    film_bridge.request_failed.connect(_on_film_bridge_failure)
    var family_state := get_node_or_null(
        "/root/FamilySceneState"
    ) as MiniUtopiaFamilySceneState
    if family_state != null:
        family_state.bind_family_client(film_bridge)

    music_preview = MiniUtopiaFamilyMusicPreview.new()
    music_preview.name = "DirectorMusicPreview"
    add_child(music_preview)

    voice_recorder = MiniUtopiaFamilyVoiceRecorder.new()
    voice_recorder.name = "PrivateShotVoiceRecorder"
    add_child(voice_recorder)
    voice_recorder.voice_ready.connect(_on_voice_ready)
    voice_recorder.voice_failed.connect(_on_voice_failed)

    director_runtime = MiniUtopiaDirectorShotRuntime.new()
    director_runtime.name = "DirectorShotRuntime"
    add_child(director_runtime)

    var selection := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if selection != null:
        var family_payload := _current_family_payload()
        if not family_payload.is_empty():
            _build_child_director_controls()
            if not selection.opened_saved_film.is_empty():
                var reopened: Dictionary = selection.opened_saved_film
                var draft: Dictionary = reopened.get("draft", {})
                saved_film_id = String(reopened.get("film_id", ""))
                saved_film_revision = String(reopened.get("revision", ""))
                film_title_input.text = String(
                    draft.get("display_name", "My Mini Utopia Movie")
                )
                film_note_input.text = String(draft.get("private_story_note", ""))
                _refresh_choice_labels()
                _refresh_record_button()
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
    var intro_margin := overlay.get_node_or_null("KidDirectorCard/DirectorIntroMargin")
    if intro_margin != null:
        intro_margin.hide()
    var controls := VBoxContainer.new()
    controls.name = "KidDirectorChoices"
    controls.position = Vector2(34, 190)
    controls.add_theme_constant_override("separation", 4)
    overlay.add_child(controls)
    var title := Label.new()
    title.text = "我的小电影"
    title.add_theme_font_override("font", preload("res://assets/fonts/Fredoka-UI.tres"))
    title.add_theme_font_size_override("font_size", 25)
    controls.add_child(title)
    for key in ["camera", "action", "duration_seconds", "caption_preset", "music_id"]:
        var button := Button.new()
        button.name = "Choice_" + key
        button.custom_minimum_size = Vector2(324, 60)
        button.add_theme_font_size_override("font_size", 19)
        button.pressed.connect(_cycle_child_choice.bind(key))
        controls.add_child(button)
        match key:
            "camera": button.icon = preload("res://assets/ui/icons/camera.svg")
            "action": button.icon = preload("res://assets/ui/icons/action.svg")
            "duration_seconds": button.icon = preload("res://assets/ui/icons/length.svg")
            "caption_preset": button.icon = preload("res://assets/ui/icons/subtitle.svg")
        child_choice_buttons[key] = button
    _refresh_choice_labels()

    film_title_input = LineEdit.new()
    film_title_input.name = "MyFilmTitle"
    film_title_input.text = "我的小电影"
    film_title_input.placeholder_text = "给电影起个名字"
    film_title_input.max_length = 64
    film_title_input.custom_minimum_size = Vector2(324, 50)
    controls.add_child(film_title_input)

    film_note_input = LineEdit.new()
    film_note_input.name = "MyFilmNote"
    film_note_input.placeholder_text = "写下你的小故事"
    film_note_input.max_length = 280
    film_note_input.custom_minimum_size = Vector2(324, 48)
    controls.add_child(film_note_input)

    save_film_button = Button.new()
    save_film_button.name = "SaveMyMovieButton"
    save_film_button.text = "保存电影"
    save_film_button.custom_minimum_size = Vector2(324, 60)
    save_film_button.disabled = not film_bridge.has_family_session()
    save_film_button.pressed.connect(_on_save_private_film_pressed)
    controls.add_child(save_film_button)

    record_voice_button = Button.new()
    record_voice_button.name = "RecordShotVoiceButton"
    record_voice_button.text = "录一段声音"
    record_voice_button.icon = preload("res://assets/ui/icons/voice.svg")
    record_voice_button.custom_minimum_size = Vector2(324, 60)
    record_voice_button.add_theme_font_size_override("font_size", 18)
    record_voice_button.pressed.connect(_on_voice_tapped)
    controls.add_child(record_voice_button)
    _refresh_record_button()


func _refresh_record_button() -> void:
    if record_voice_button == null:
        return
    record_voice_button.disabled = (
        voice_refresh_blocked or saved_film_id.is_empty() or film_bridge == null
        or not film_bridge.has_family_session()
        or film_bridge.is_busy()
        or (voice_recorder != null and voice_recorder.recording)
    )


func _refresh_choice_labels() -> void:
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null:
        return
    var choices := family.director_shot_choices
    var camera_button: Button = child_choice_buttons.get("camera")
    var action_button: Button = child_choice_buttons.get("action")
    var length_button: Button = child_choice_buttons.get("duration_seconds")
    var caption_button: Button = child_choice_buttons.get("caption_preset")
    if camera_button != null:
        camera_button.text = "镜头  " + {"follow":"跟随","wide":"远景","close":"特写"}.get(String(choices.get("camera", "follow")), "跟随")
    if action_button != null:
        action_button.text = "动作  " + {"walk":"走路","run":"跑步","celebrate":"庆祝"}.get(String(choices.get("action", "walk")), "走路")
    if length_button != null:
        length_button.text = "时长  " + str(int(choices.get("duration_seconds", 15))) + "秒"
    if caption_button != null:
        var preset_id := String(choices.get("caption_preset", "none"))
        var caption := MiniUtopiaFamilyDirectorSession.caption_text(preset_id)
        caption_button.text = "字幕  " + ("开启" if not caption.is_empty() else "关闭")
    var music_button: Button = child_choice_buttons.get("music_id")
    if music_button != null:
        var music_id := String(choices.get("music_id", "none"))
        music_button.text = "音乐  " + String(
            MiniUtopiaFamilyDirectorSession.MUSIC_TITLES.get(music_id, "关闭")
        )


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
        "caption_preset":
            options = ["none", "hello", "adventure", "hooray"]
        "music_id":
            options = ["none", "sunny_meadow", "cloud_parade", "moonlit_garden"]
        _:
            return
    var old_value = family.director_shot_choices.get(key, options[0])
    var index := options.find(old_value)
    family.director_shot_choices[key] = options[(index + 1) % options.size()]
    _refresh_choice_labels()
    if key == "music_id" and music_preview != null:
        if not music_preview.choose_on_user_tap(String(family.director_shot_choices[key])):
            status_label.text = "音乐预览暂时不可用"
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

    # Decorative panel uses the inherited global Theme. Preserve existing
    # KidDirectorChoices / StatusPanel paths and functional signal connections.
    var choices_card := PanelContainer.new()
    choices_card.name = "KidDirectorCard"
    choices_card.position = Vector2(22, 168)
    choices_card.custom_minimum_size = Vector2(378, 700)
    choices_card.mouse_filter = Control.MOUSE_FILTER_IGNORE
    layer.add_child(choices_card)

    # A friendly idle state for the isolated Web screenshot and for children
    # arriving without a playable Hero. It hides when real choices are shown.
    var intro_margin := MarginContainer.new()
    intro_margin.name = "DirectorIntroMargin"
    intro_margin.add_theme_constant_override("margin_left", 22)
    intro_margin.add_theme_constant_override("margin_right", 20)
    intro_margin.add_theme_constant_override("margin_top", 28)
    choices_card.add_child(intro_margin)
    var intro := Label.new()
    intro.name = "DirectorIntro"
    intro.text = "选好英雄，开始拍电影！"
    intro.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    intro.add_theme_font_override("font", preload("res://assets/fonts/Fredoka-UI.tres"))
    intro.add_theme_font_size_override("font_size", 25)
    intro_margin.add_child(intro)

    var panel := PanelContainer.new()
    panel.name = "StatusPanel"
    panel.position = Vector2(24.0, 24.0)
    panel.custom_minimum_size = Vector2(620.0, 128.0)
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
    replay.text = "再看一次"
    replay.custom_minimum_size = Vector2(160.0, 54.0)
    replay.add_theme_font_size_override("font_size", 20)
    replay.pressed.connect(_on_replay_pressed)
    buttons.add_child(replay)

    var home := Button.new()
    home.name = "BackToVillageButton"
    home.text = "返回村子"
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
    status_label.text = "我的小电影"
    status_label.add_theme_font_size_override("font_size", 18)
    margin.add_child(status_label)


func _on_replay_pressed() -> void:
    if director_runtime != null:
        director_runtime.reset_shot()


func _on_back_to_village_pressed() -> void:
    if music_preview != null:
        music_preview.clear_preview()
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    get_tree().change_scene_to_file("res://scenes/main.tscn")


func _private_film_draft() -> Dictionary:
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null or family.active_play_session().is_empty():
        return {}
    var name := film_title_input.text.strip_edges()
    if name.is_empty():
        return {}
    var second_id: Variant = null
    if not family.second_cast_is_parent_guest:
        var second := family.second_cast_play_session()
        if not second.is_empty():
            second_id = String(second.get("character_asset_id", ""))
    return {
        "schema_version": "1.0", "display_name": name,
        "character_id": String(family.active_character.get("character_id", "")),
        "second_character_id": second_id,
        "camera": String(family.director_shot_choices.get("camera", "follow")),
        "action": String(family.director_shot_choices.get("action", "walk")),
        "duration_seconds": int(family.director_shot_choices.get("duration_seconds", 15)),
        "caption_preset": String(family.director_shot_choices.get("caption_preset", "none")),
        "music_id": String(family.director_shot_choices.get("music_id", "none")),
        "private_story_note": film_note_input.text.strip_edges()
    }


func _on_save_private_film_pressed() -> void:
    if film_bridge == null or not film_bridge.has_family_session() or film_bridge.is_busy():
        return
    var draft := _private_film_draft()
    if draft.is_empty():
        status_label.text = "先给电影起名，再选英雄"
        return
    var error := (
        film_bridge.create_family_film(draft)
        if saved_film_id.is_empty()
        else film_bridge.update_family_film(
            saved_film_id, saved_film_revision, draft
        )
    )
    if error != OK:
        status_label.text = "保存失败，请重试"
        return
    save_film_button.disabled = true
    status_label.text = "正在保存电影…"


func _on_voice_tapped() -> void:
    if voice_refresh_blocked or saved_film_id.is_empty() or film_bridge == null or film_bridge.is_busy():
        return
    if not voice_recorder.start_on_user_tap():
        status_label.text = "需要安全连接才能录音"
        return
    _refresh_record_button()
    status_label.text = "正在录音（最多9秒）…"


func _on_voice_ready(media_type: String, audio: PackedByteArray) -> void:
    if voice_refresh_blocked or film_bridge == null or film_bridge.upload_private_film_voice(
        saved_film_id, audio, media_type, saved_film_revision
    ) != OK:
        status_label.text = "声音上传失败，请重试"
    else:
        status_label.text = "正在保存声音…"
    _refresh_record_button()


func _on_voice_failed() -> void:
    status_label.text = "暂时无法使用麦克风"
    _refresh_record_button()


func _on_film_bridge_success(kind: String, payload: Dictionary) -> void:
    if kind == "films:get":
        var current_id := String(payload.get("film_id", ""))
        var current_revision := String(payload.get("revision", ""))
        var draft = payload.get("draft", null)
        var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
        var valid := (
            voice_refresh_blocked and current_id == saved_film_id
            and current_revision.is_valid_int() and int(current_revision) > 0
            and typeof(draft) == TYPE_DICTIONARY and family != null
            and String(draft.get("schema_version", "")) == "1.0"
            and String(draft.get("character_id", "")) == String(family.active_character.get("character_id", ""))
            and String(draft.get("display_name", "")).strip_edges() != ""
            and String(draft.get("camera", "")) in ["follow", "wide", "close"]
            and String(draft.get("action", "")) in ["walk", "run", "celebrate"]
            and int(draft.get("duration_seconds", 0)) in [15, 30]
            and MiniUtopiaFamilyDirectorSession.CAPTION_PRESETS.has(String(draft.get("caption_preset", "")))
            and MiniUtopiaFamilyDirectorSession.MUSIC_TITLES.has(String(draft.get("music_id", "none")))
        )
        if not valid:
            status_label.text = "电影内容无法安全刷新，请重新打开"
            _refresh_record_button()
            return
        var second_id = draft.get("second_character_id", null)
        var second := family.second_cast_play_session()
        if second_id != null and String(second_id) != String(second.get("character_asset_id", "")):
            status_label.text = "演员已变化，请重新打开电影"
            _refresh_record_button()
            return
        family.director_shot_choices = {
            "camera": String(draft["camera"]), "action": String(draft["action"]),
            "duration_seconds": int(draft["duration_seconds"]),
            "caption_preset": String(draft["caption_preset"]),
            "music_id": String(draft.get("music_id", "none")),
        }
        film_title_input.text = String(draft["display_name"])
        film_note_input.text = String(draft.get("private_story_note", ""))
        saved_film_revision = current_revision
        family.opened_saved_film = payload.duplicate(true)
        if music_preview != null:
            music_preview.clear_preview()
        _refresh_choice_labels()
        var shot := _current_family_payload()
        if not shot.is_empty():
            stage_payload(shot)
            voice_refresh_blocked = false
            status_label.text = "电影已更新，请确认最新内容后重新录音"
        else:
            status_label.text = "无法恢复镜头，请重新打开电影"
        _refresh_record_button()
        return
    if kind == "films:voice:0":
        saved_film_revision = String(payload.get("revision", ""))
        status_label.text = "声音已保存，请家长确认"
        _refresh_record_button()
        return

    if kind not in ["films:post", "films:put"]:
        return
    var id := String(payload.get("film_id", ""))
    var revision := String(payload.get("revision", ""))
    if not id.begins_with("FILM_") or revision.is_empty():
        status_label.text = "保存未成功，请重试"
        save_film_button.disabled = false
        return
    saved_film_id = id
    saved_film_revision = revision
    save_film_button.disabled = false
    _refresh_record_button()
    status_label.text = "电影已保存！"
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family != null and family.second_cast_is_parent_guest:
        status_label.text += "\n客串邀请只在本次游戏有效"


func _on_film_bridge_failure(
    kind: String, status_code: int, _code: String, _message: String
) -> void:
    if kind == "films:voice:0":
        if status_code == 409:
            voice_refresh_blocked = true
            status_label.text = "电影版本已变化，正在刷新，请重新确认后录音"
            if film_bridge != null and not saved_film_id.is_empty():
                film_bridge.get_family_film(saved_film_id)
        else:
            status_label.text = "声音未保存，请检查麦克风"
        _refresh_record_button()
        return
    if kind == "films:get":
        voice_refresh_blocked = true
        status_label.text = "无法刷新电影，请重新打开"
        return
    if kind not in ["films:post", "films:put"]:
        return
    if status_code == 409:
        voice_refresh_blocked = true
        _refresh_record_button()
    save_film_button.disabled = false
    status_label.text = (
        "电影内容已更新，请重新打开"
        if status_code == 409
        else "暂时无法保存，请重试"
    )


func _show_missing_payload() -> void:
    if status_label == null:
        return
    status_label.text = "还没有拍摄内容，请先选择一个场景"
    push_warning(
        "DIR-04B: no director_shot_session.json; Stage Shot in Creator first."
    )


func _show_ready(payload: Dictionary) -> void:
    if status_label == null:
        return
    # Stage IDs, internal scene paths and synthetic CI identifiers belong only
    # in diagnostics, never the child-facing Director status panel.
    var seconds := int(round(float(payload.get("duration_seconds", 0.0))))
    status_label.text = "镜头准备好了！"
    if seconds > 0:
        status_label.text += "\n时长 " + str(seconds) + " 秒"

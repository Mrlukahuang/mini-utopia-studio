extends SceneTree

func _initialize() -> void:
    var family := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    family.disconnect_family()
    family.connect_family(
        "https://family.example",
        "synthetic_film_save_session_0123456789abcdefgh",
        "child_a"
    )
    var hero := {"schema_version":"1.0","character_id":"CHAR_SAVE_A",
        "display_name":"Star Sheep","profile":{"avatar":{
        "rig_family":MiniUtopiaAvatarContract.RIG_FAMILY}}}
    var second := hero.duplicate(true)
    second["character_id"] = "CHAR_SAVE_B"
    family.select_character(hero)
    family.select_equipment({
        "character_asset_id":"CHAR_SAVE_A", "equipped":{}, "final_stats":{}
    })
    family.select_second_cast_character(second)
    family.select_second_cast_equipment({
        "character_asset_id":"CHAR_SAVE_B", "equipped":{}, "final_stats":{}
    })
    var stage = load("res://scenes/director_stage.tscn").instantiate()
    root.add_child(stage)
    await process_frame

    var button := stage.get_node_or_null(
        "DirectorStageOverlay/KidDirectorChoices/SaveMyMovieButton"
    ) as Button
    if button == null or button.custom_minimum_size.y < 48:
        _fail("touch save button missing")
        return
    if button.pressed.get_connections().is_empty() or button.disabled:
        _fail("movie save is not wired to a scoped family session")
        return
    var voice_button := stage.get_node_or_null(
        "DirectorStageOverlay/KidDirectorChoices/RecordShotVoiceButton"
    ) as Button
    if voice_button == null or voice_button.custom_minimum_size.y < 48:
        _fail("touch recording button missing")
        return
    if not voice_button.disabled or stage.voice_recorder.start_on_user_tap():
        _fail("must save film first and never invoke desktop microphone")
        return

    stage.film_title_input.text = "Our Adventure"
    stage.film_note_input.text = "A story in the clouds"
    family.director_shot_choices["camera"] = "close"
    family.director_shot_choices["action"] = "celebrate"
    family.director_shot_choices["duration_seconds"] = 30
    family.director_shot_choices["caption_preset"] = "adventure"
    var draft: Dictionary = stage._private_film_draft()
    if draft.get("character_id") != "CHAR_SAVE_A":
        _fail("primary character ID was lost")
        return
    if draft.get("second_character_id") != "CHAR_SAVE_B":
        _fail("owned second character omitted")
        return
    if draft.get("duration_seconds") != 30 or draft.get("camera") != "close":
        _fail("child choices did not reach private draft")
        return
    if draft.get("caption_preset") != "adventure":
        _fail("kid-safe subtitle choice did not reach canonical film draft")
        return
    if draft.get("private_story_note") != "A story in the clouds":
        _fail("story note was not preserved")
        return

    family.second_cast_is_parent_guest = true
    draft = stage._private_film_draft()
    if draft.get("second_character_id") != null:
        _fail("sibling guest leaked into persistent private film draft")
        return
    stage._on_film_bridge_success("films:post", {
        "film_id":"FILM_TEST_SAVED", "revision":"1"
    })
    if stage.saved_film_id != "FILM_TEST_SAVED" or stage.saved_film_revision != "1":
        _fail("canonical saved film ID was replaced")
        return
    if voice_button.disabled:
        _fail("record button was not enabled after private save")
        return
    stage._on_film_bridge_success("films:voice:0", {
        "film_id":"FILM_TEST_SAVED", "revision":"3"
    })
    if stage.saved_film_revision != "3":
        _fail("voice recording did not advance current film revision")
        return
    stage._on_film_bridge_success("films:put", {
        "film_id":"FILM_TEST_SAVED", "revision":"2"
    })
    if stage.saved_film_revision != "2":
        _fail("film edit did not advance revision")
        return

    family.disconnect_family()
    print("family_save_film_ui_smoke: PASS")
    quit(0)

func _fail(msg: String) -> void:
    push_error("family_save_film_ui_smoke: FAIL " + msg)
    quit(1)

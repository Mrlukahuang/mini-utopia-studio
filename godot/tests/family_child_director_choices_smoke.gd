extends SceneTree

## Interactive controls must actually change a 15/30-second live shot, while
## retaining canonical character IDs and their individual outfits.

func _initialize() -> void:
    var family := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null:
        _fail("FamilySceneState autoload missing")
        return
    family.disconnect_family()
    family.select_character(_hero("CHAR_DIRECTOR_A", "#F7B7D2"))
    family.select_equipment(_gear("CHAR_DIRECTOR_A", "ITEM_A_CROWN"))
    # Two actors in one film, from already-authorized test snapshots.
    if not family.connect_family(
        "https://family.example",
        "synthetic_director_test_session_0123456789"
    ):
        _fail("scoped film session missing")
        return
    family.select_character(_hero("CHAR_DIRECTOR_A", "#F7B7D2"))
    family.select_equipment(_gear("CHAR_DIRECTOR_A", "ITEM_A_CROWN"))
    family.select_second_cast_character(_hero("CHAR_DIRECTOR_B", "#B9E7D0"))
    family.select_second_cast_equipment(_gear("CHAR_DIRECTOR_B", "ITEM_B_CROWN"))

    var stage = load("res://scenes/director_stage.tscn").instantiate()
    root.add_child(stage)
    await process_frame

    # Sound helper is opt-in, initiated by a real user tap in the eventual
    # W2-01b UI; this smoke confirms it never autoplays or accepts a path.
    var sound := MiniUtopiaFamilyMusicPreview.new()
    sound.name = "SyntheticMusicPreview"
    stage.add_child(sound)
    if sound.autoplay or sound.stream != null:
        _fail("W2 audio must be off until a direct child tap")
        return
    if sound.choose_on_user_tap("../../private_child_recording.wav"):
        _fail("music preview accepted a non-catalog path")
        return
    if sound.stream != null:
        _fail("unknown music ID leaked a player stream")
        return
    if not sound.choose_on_user_tap("sunny_meadow") or sound.stream == null:
        _fail("first bundled music WAV did not load on direct tap")
        return
    if sound.volume_db > -6.0:
        _fail("music preview did not apply safe initial volume")
        return
    if not sound.choose_on_user_tap("none") or sound.stream != null:
        _fail("music off choice did not stop and clear audio")
        return
    sound.clear_preview()

    var controls := stage.get_node_or_null(
        "DirectorStageOverlay/KidDirectorChoices"
    ) as VBoxContainer
    if controls == null:
        _fail("child director controls missing")
        return
    for key in ["camera", "action", "duration_seconds", "caption_preset", "music_id"]:
        var button := controls.get_node_or_null("Choice_" + key) as Button
        if button == null or button.custom_minimum_size.y < 48:
            _fail("iPad director touch button missing or undersized: " + key)
            return
        if button.pressed.get_connections().is_empty():
            _fail("choice button not connected: " + key)
            return

    if stage.director_runtime.actor == null or stage.director_runtime.second_actor == null:
        _fail("two saved Heroes not staged")
        return
    stage._cycle_child_choice("music_id")
    if stage.music_preview == null or stage.music_preview.stream == null:
        _fail("Director tap did not play selected bundled music")
        return
    var music_button := controls.get_node("Choice_music_id") as Button
    if music_button.text != "音乐  阳光草地":
        _fail("Director music choice is not displayed in Chinese")
        return
    stage._cycle_child_choice("music_id")
    if music_button.text != "音乐  云朵游行":
        _fail("second music title is not Chinese")
        return
    stage._cycle_child_choice("music_id")
    if music_button.text != "音乐  月光花园":
        _fail("third music title is not Chinese")
        return
    stage._cycle_child_choice("music_id")
    if stage.music_preview.stream != null or music_button.text != "音乐  关闭":
        _fail("music off did not stop preview")
        return
    stage._cycle_child_choice("music_id")
    if family.director_shot_choices.get("music_id") != "sunny_meadow":
        _fail("Director music choice did not select whitelisted music")
        return
    if stage._private_film_draft().get("music_id") != "sunny_meadow":
        _fail("Music choice did not persist in canonical draft")
        return
    stage._cycle_child_choice("caption_preset")
    if family.director_shot_choices.get("caption_preset") != "hello":
        _fail("kid-safe subtitle choice did not advance")
        return
    if stage.director_runtime.subtitle_label == null or stage.director_runtime.subtitle_label.text != "Hello, friend!":
        _fail("live subtitle text not drawn by shared movie runtime")
        return
    stage.director_runtime.advance_shot(3.0)
    if not stage.director_runtime.subtitle_panel.visible:
        _fail("subtitle should appear during its timed dialogue beat")
        return
    stage._on_replay_pressed()
    if stage.director_runtime.subtitle_panel.visible:
        _fail("subtitle did not reset on Replay")
        return
    stage._cycle_child_choice("camera")
    if family.director_shot_choices["camera"] != "wide":
        _fail("camera option did not advance")
        return
    if stage.director_runtime.camera_start_fov != 58.0:
        _fail("wide camera field of view not applied")
        return

    stage._cycle_child_choice("action")
    if stage.director_runtime.blocking_movement_style != "run":
        _fail("run action not applied to actor path")
        return
    stage._cycle_child_choice("duration_seconds")
    if stage.director_runtime.duration_seconds != 30.0:
        _fail("30-second timeline not applied to runtime")
        return
    if family.director_shot_choices["duration_seconds"] != 30:
        _fail("child film length not retained across restage")
        return
    if stage.director_runtime.actor.get_meta(
        "mini_utopia_character_asset_id", ""
    ) != "CHAR_DIRECTOR_A":
        _fail("camera choice replaced first saved Hero")
        return
    if stage.director_runtime.second_actor.get_meta(
        "mini_utopia_character_asset_id", ""
    ) != "CHAR_DIRECTOR_B":
        _fail("camera choice replaced second saved Hero")
        return
    if stage.director_runtime.second_play_runtime.payload.get(
        "equipment", {}
    ).get("equipped", {}).get("headwear", {}).get(
        "item_instance_id"
    ) != "ITEM_B_CROWN":
        _fail("film editing lost second Hero wardrobe")
        return
    stage._cycle_child_choice("action")
    if stage.director_runtime.blocking_movement_style != "hold":
        _fail("celebrate action should hold actor position")
        return
    stage.director_runtime.advance_shot(8.2)
    if stage.director_runtime.performance_last_cue != "celebrate":
        _fail("30-second timeline did not retime performance cues")
        return
    stage._on_replay_pressed()
    if stage.director_runtime.elapsed_seconds != 0.0:
        _fail("Replay did not reset edited shot")
        return

    family.disconnect_family()
    if family.director_shot_choices["duration_seconds"] != 15 or family.director_shot_choices.get("caption_preset") != "none" or family.director_shot_choices.get("music_id", "none") != "none":
        _fail("child choices leaked to the next profile after logout")
        return

    print("family_child_director_choices_smoke: PASS · 2 Heroes, camera, action, 30s")
    quit(0)


func _hero(cid: String, tint: String) -> Dictionary:
    return {
        "schema_version": "1.0", "character_id": cid, "display_name": cid,
        "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
            "surface_color_hex": tint,
            "species_head_id": "species_head_cat_v1",
        }}
    }


func _gear(cid: String, item: String) -> Dictionary:
    return {
        "character_asset_id": cid,
        "equipped": {"headwear": {
            "item_instance_id": item, "display_name": "My Crown",
            "rarity": "gold"
        }},
        "final_stats": {}
    }


func _fail(message: String) -> void:
    push_error("family_child_director_choices_smoke: FAIL · " + message)
    quit(1)

extends SceneTree

## One child-facing game->film shot with a server-saved Hero contract.
## This test does not record or publish a real child's media.

func _initialize() -> void:
    var selection := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    if selection == null:
        _fail("FamilySceneState is not registered")
        return
    selection.clear_selection()
    var contract := {
        "schema_version": "1.0",
        "character_id": "CHAR_DIRECTOR_LILY",
        "display_name": "Lily",
        "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
            "body_type": "slim",
            "species_head_id": "species_head_cat_v1",
            "surface_color_hex": "#D7C2F3",
            "eye_color_hex": "#7A5238",
            "hair_style_id": "hair_none"
        }}
    }
    if not selection.select_character(contract):
        _fail("saved Hero could not be selected")
        return

    var session := MiniUtopiaFamilyDirectorSession.from_play_session(
        selection.active_play_session()
    )
    if session.is_empty():
        _fail("Director session was not built")
        return
    if session.get("duration_seconds") != 15.0:
        _fail("family scene should be 15 seconds")
        return
    if session.get("play_session", {}).get("character_asset_id") != "CHAR_DIRECTOR_LILY":
        _fail("Director session replaced Character identity")
        return
    if session.get("play_session", {}).get("world_runtime", {}).get("scene_path") != "res://scenes/main.tscn":
        _fail("Director did not bind the playable village")
        return

    var packed := load("res://scenes/director_stage.tscn") as PackedScene
    if packed == null:
        _fail("Director Stage scene missing")
        return
    var stage := packed.instantiate()
    root.add_child(stage)
    await process_frame
    await process_frame

    var runtime = stage.get_node_or_null("DirectorShotRuntime")
    if runtime == null or runtime.actor == null or runtime.camera == null:
        _fail("Director runtime did not stage actor/camera")
        return
    if runtime.actor.get_meta("mini_utopia_character_asset_id", "") != "CHAR_DIRECTOR_LILY":
        _fail("Director loaded fixture instead of saved Character")
        return
    if not runtime.bound_world_loaded:
        _fail("Director failed to load same playable village")
        return
    if not runtime.playing:
        _fail("15-second family performance did not start")
        return
    var replay := stage.get_node_or_null("DirectorStageOverlay/DirectorControls/ReplayButton") as Button
    var back := stage.get_node_or_null("DirectorStageOverlay/DirectorControls/BackToVillageButton") as Button
    if replay == null or back == null:
        _fail("touch-friendly Replay / Village navigation missing")
        return
    if replay.pressed.get_connections().is_empty() or back.pressed.get_connections().is_empty():
        _fail("Director controls do not perform actions")
        return
    runtime.advance_shot(4.1)
    if runtime.elapsed_seconds < 4.0 or runtime.performance_last_cue != "celebrate":
        _fail("family performance cue did not trigger")
        return
    stage._on_replay_pressed()
    if runtime.elapsed_seconds != 0.0 or not runtime.playing:
        _fail("Replay button did not reset 15s performance")
        return

    selection.clear_selection()
    print("family_director_launch_smoke: PASS · saved Hero, real village, cues, replay")
    quit(0)


func _fail(message: String) -> void:
    push_error("family_director_launch_smoke: FAIL · " + message)
    quit(1)

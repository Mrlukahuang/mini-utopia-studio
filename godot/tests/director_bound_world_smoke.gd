extends SceneTree


func _initialize() -> void:
    var runtime := MiniUtopiaDirectorShotRuntime.new()
    root.add_child(runtime)

    runtime.configure({
        "director_session_id": "DIR_BOUND_WORLD_SMOKE",
        "episode_id": "EP_BOUND",
        "scene_id": "SCENE_01",
        "shot_id": "SHOT_01_01",
        "story_id": "STORY_BOUND",
        "world_asset_id": "LOC_BOUND",
        "character_asset_id": "CHAR_BOUND",
        "duration_seconds": 1.0,
        "animation_intent": "idle",
        "camera": {
            "position": [0.0, 4.2, 7.8],
            "look_at": [0.0, 1.1, 0.0],
            "fov": 52.0,
            "movement": "Wide establishing"
        },
        "shot": {
            "shot_id": "SHOT_01_01",
            "scene_id": "SCENE_01",
            "duration_seconds": 1.0,
            "asset_ids": ["CHAR_BOUND", "LOC_BOUND"],
            "shot_type": "Establishing",
            "camera": "Wide establishing",
            "action": "Hold.",
            "expression": "curious",
            "dialogue": [],
            "continuity_notes": []
        },
        "play_session": {
            "schema_version": "1.0",
            "session_id": "DIRECTOR_BOUND_PLAY",
            "source": "director",
            "character_asset_id": "CHAR_BOUND",
            "character_name": "Nancy",
            "character": {
                "mode": "procedural",
                "rig_family": "kaykit_humanoid_v1",
                "body_type": "standard",
                "socket_names": [
                    "Socket_Weapon_R",
                    "Socket_Weapon_L",
                    "Socket_Backpack",
                    "Socket_Wings",
                    "Socket_Accessory",
                    "Socket_Headwear"
                ],
                "species_head_id": "species_head_human_v1",
                "surface_type": "skin",
                "surface_color_hex": "#F2C7A5",
                "eye_style_id": "eyes_round_soft_v1",
                "hair_style_id": "hair_bob_v1",
                "scale": 1.0,
                "animation_clips": {
                    "idle": "Idle",
                    "walk": "Walk",
                    "run": "Run"
                },
                "body_color_hex": "#FFF4D7",
                "accent_color_hex": "#B9E7D0",
                "hair_color_hex": "#5B4036",
                "eye_color_hex": "#7A5238",
                "playable_height_units": 3.4,
                "head_to_body_ratio": 0.34
            },
            "equipment": {
                "schema_version": "1.0",
                "character_asset_id": "CHAR_BOUND",
                "rig_family": "kaykit_humanoid_v1",
                "body_type": "standard",
                "socket_names": [
                    "Socket_Weapon_R",
                    "Socket_Weapon_L",
                    "Socket_Backpack",
                    "Socket_Wings",
                    "Socket_Accessory",
                    "Socket_Headwear"
                ],
                "final_stats": {"hp": 100, "atk": 10, "defense": 8},
                "equipped": {}
            },
            "baby": null,
            "quest": null,
            "world_gameplay": null,
            "creative_layout": null,
            "world_runtime": {
                "schema_version": "1.0",
                "world_asset_id": "LOC_BOUND",
                "scene_path": "res://tests/fixtures/director_bound_world_test.tscn",
                "scene_label": "Director Bound World Test",
                "source": "system_builtin",
                "playable": true
            },
            "world_asset_id": "LOC_BOUND",
            "world_name": "Bound Test World",
            "created_at": "2026-10-07T00:00:00Z"
        }
    })

    _verify.call_deferred(runtime)


func _verify(runtime: MiniUtopiaDirectorShotRuntime) -> void:
    await process_frame
    await process_frame

    if not runtime.bound_world_loaded:
        push_error("director_bound_world_smoke: bound World did not load")
        quit(1)
        return
    if runtime.bound_scene_path != "res://tests/fixtures/director_bound_world_test.tscn":
        push_error("director_bound_world_smoke: scene path mismatch")
        quit(1)
        return
    if runtime.bound_world_instance == null:
        push_error("director_bound_world_smoke: World instance missing")
        quit(1)
        return
    if runtime.bound_world_instance.name != "DirectorBoundWorldTest":
        push_error("director_bound_world_smoke: wrong World root")
        quit(1)
        return

    var context = runtime.get_node_or_null("DirectorWorldContext")
    if context == null:
        push_error("director_bound_world_smoke: context missing")
        quit(1)
        return
    if context.get_node_or_null("StageFloor") != null:
        push_error("director_bound_world_smoke: fallback floor should not exist")
        quit(1)
        return
    if String(context.get_meta("runtime_mode", "")) != "bound_scene":
        push_error("director_bound_world_smoke: runtime mode not bound_scene")
        quit(1)
        return
    if runtime.actor == null or runtime.camera == null:
        push_error("director_bound_world_smoke: actor/camera missing")
        quit(1)
        return

    print("director_bound_world_smoke: PASS · bound scene + actor + camera")
    quit(0)

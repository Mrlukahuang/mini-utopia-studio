extends SceneTree


func _initialize() -> void:
    var runtime := MiniUtopiaDirectorShotRuntime.new()
    root.add_child(runtime)

    runtime.configure({
        "director_session_id": "DIR_CAMERA_SMOKE",
        "episode_id": "EP_CAMERA",
        "scene_id": "SCENE_01",
        "shot_id": "SHOT_01_01",
        "story_id": "STORY_CAMERA",
        "world_asset_id": "LOC_CAMERA",
        "character_asset_id": "CHAR_CAMERA",
        "duration_seconds": 2.0,
        "animation_intent": "idle",
        "camera": {
            "position": [0.0, 2.0, 10.0],
            "look_at": [0.0, 1.0, 0.0],
            "fov": 60.0,
            "movement": "Wide push-in",
            "end_position": [0.0, 2.0, 4.0],
            "end_look_at": [0.0, 1.0, 0.0],
            "end_fov": 40.0,
            "movement_mode": "push_in",
            "easing": "linear"
        },
        "shot": {
            "shot_id": "SHOT_01_01",
            "scene_id": "SCENE_01",
            "duration_seconds": 2.0,
            "asset_ids": ["CHAR_CAMERA", "LOC_CAMERA"],
            "shot_type": "Establishing",
            "camera": "Wide push-in",
            "action": "Hold.",
            "expression": "curious",
            "dialogue": [],
            "continuity_notes": []
        },
        "play_session": {
            "schema_version": "1.0",
            "session_id": "DIRECTOR_CAMERA_PLAY",
            "source": "director",
            "character_asset_id": "CHAR_CAMERA",
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
                "character_asset_id": "CHAR_CAMERA",
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
            "world_runtime": null,
            "world_asset_id": "LOC_CAMERA",
            "world_name": "Camera World",
            "created_at": "2026-10-07T00:00:00Z"
        }
    })
    runtime.set_process(false)

    if runtime.camera.position.distance_to(
        Vector3(0.0, 2.0, 10.0)
    ) > 0.01:
        push_error("director_camera_motion_smoke: start position mismatch")
        quit(1)
        return
    if absf(runtime.camera.fov - 60.0) > 0.01:
        push_error("director_camera_motion_smoke: start FOV mismatch")
        quit(1)
        return

    runtime.reset_shot()
    runtime.advance_shot(1.0)
    if runtime.camera.position.distance_to(
        Vector3(0.0, 2.0, 7.0)
    ) > 0.02:
        push_error(
            "director_camera_motion_smoke: midpoint position mismatch · "
            + str(runtime.camera.position)
        )
        quit(1)
        return
    if absf(runtime.camera.fov - 50.0) > 0.02:
        push_error("director_camera_motion_smoke: midpoint FOV mismatch")
        quit(1)
        return

    runtime.advance_shot(1.0)
    if runtime.camera.position.distance_to(
        Vector3(0.0, 2.0, 4.0)
    ) > 0.02:
        push_error("director_camera_motion_smoke: end position mismatch")
        quit(1)
        return
    if absf(runtime.camera.fov - 40.0) > 0.02:
        push_error("director_camera_motion_smoke: end FOV mismatch")
        quit(1)
        return

    print(
        "director_camera_motion_smoke: PASS · camera start/mid/end + FOV"
    )
    quit(0)

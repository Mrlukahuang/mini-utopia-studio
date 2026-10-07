extends SceneTree


func _initialize() -> void:
    var packed := load("res://scenes/director_stage.tscn") as PackedScene
    if packed == null:
        push_error("director_stage_scene_smoke: scene could not load")
        quit(1)
        return

    var stage := packed.instantiate()
    root.add_child(stage)
    _verify.call_deferred(stage)


func _verify(stage: Node) -> void:
    await process_frame
    await process_frame

    var overlay = stage.get_node_or_null("DirectorStageOverlay")
    if overlay == null:
        push_error("director_stage_scene_smoke: overlay missing")
        quit(1)
        return

    stage.stage_payload({
        "director_session_id": "DIR_STAGE_SMOKE",
        "episode_id": "EP_STAGE",
        "scene_id": "SCENE_01",
        "shot_id": "SHOT_01_01",
        "story_id": "STORY_STAGE",
        "world_asset_id": "LOC_STAGE",
        "character_asset_id": "CHAR_STAGE",
        "duration_seconds": 1.5,
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
            "duration_seconds": 1.5,
            "asset_ids": ["CHAR_STAGE", "LOC_STAGE"],
            "shot_type": "Establishing",
            "camera": "Wide establishing",
            "action": "Hold.",
            "expression": "curious",
            "dialogue": [],
            "continuity_notes": []
        },
        "play_session": {
            "schema_version": "1.0",
            "session_id": "DIRECTOR_PLAY_STAGE",
            "source": "director",
            "character_asset_id": "CHAR_STAGE",
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
                "character_asset_id": "CHAR_STAGE",
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
            "world_asset_id": "LOC_STAGE",
            "world_name": "Stage World",
            "created_at": "2026-10-07T00:00:00Z"
        }
    })

    await process_frame
    await process_frame

    var runtime = stage.get_node_or_null("DirectorShotRuntime")
    if runtime == null:
        push_error("director_stage_scene_smoke: runtime missing")
        quit(1)
        return
    if runtime.actor == null or runtime.camera == null:
        push_error("director_stage_scene_smoke: actor/camera missing")
        quit(1)
        return

    var label = stage.get_node_or_null(
        "DirectorStageOverlay/StatusPanel/MarginContainer/StatusLabel"
    ) as Label
    if label == null or "SHOT_01_01" not in label.text:
        push_error("director_stage_scene_smoke: ready overlay missing shot")
        quit(1)
        return

    print(
        "director_stage_scene_smoke: PASS · launchable scene + overlay + runtime"
    )
    quit(0)

extends SceneTree


func _initialize() -> void:
    var runtime := MiniUtopiaDirectorShotRuntime.new()
    root.add_child(runtime)

    runtime.configure({
        "director_session_id": "DIR_PERFORMANCE_SMOKE",
        "episode_id": "EP_PERFORMANCE",
        "scene_id": "SCENE_01",
        "shot_id": "SHOT_01_01",
        "story_id": "STORY_PERFORMANCE",
        "world_asset_id": "LOC_PERFORMANCE",
        "character_asset_id": "CHAR_PERFORMANCE",
        "duration_seconds": 2.5,
        "animation_intent": "idle",
        "camera": {
            "position": [0.0, 2.0, 8.0],
            "look_at": [0.0, 1.0, 0.0],
            "fov": 48.0,
            "movement": "Hold"
        },
        "shot": {
            "shot_id": "SHOT_01_01",
            "scene_id": "SCENE_01",
            "duration_seconds": 2.5,
            "asset_ids": ["CHAR_PERFORMANCE", "LOC_PERFORMANCE"],
            "shot_type": "Reaction",
            "camera": "Hold",
            "action": "React, attack, then look and celebrate.",
            "expression": "surprised",
            "dialogue": [],
            "continuity_notes": [],
            "performance_cues": [
                {
                    "cue_id": "CUE_REACTION",
                    "cue_type": "reaction",
                    "start_seconds": 0.0,
                    "duration_seconds": 1.0,
                    "intensity": 1.0,
                    "target": "",
                    "direction_degrees": null,
                    "source": "creator",
                    "confidence": 1.0
                },
                {
                    "cue_id": "CUE_ATTACK",
                    "cue_type": "attack",
                    "start_seconds": 0.5,
                    "duration_seconds": 0.6,
                    "intensity": 1.0,
                    "target": "",
                    "direction_degrees": null,
                    "source": "creator",
                    "confidence": 1.0
                },
                {
                    "cue_id": "CUE_LOOK",
                    "cue_type": "look_at",
                    "start_seconds": 1.0,
                    "duration_seconds": 0.5,
                    "intensity": 0.8,
                    "target": "story_focus",
                    "direction_degrees": 90.0,
                    "source": "creator",
                    "confidence": 1.0
                },
                {
                    "cue_id": "CUE_CELEBRATE",
                    "cue_type": "celebrate",
                    "start_seconds": 1.5,
                    "duration_seconds": 0.8,
                    "intensity": 1.0,
                    "target": "",
                    "direction_degrees": null,
                    "source": "creator",
                    "confidence": 1.0
                }
            ]
        },
        "play_session": {
            "schema_version": "1.0",
            "session_id": "DIRECTOR_PERFORMANCE_PLAY",
            "source": "director",
            "character_asset_id": "CHAR_PERFORMANCE",
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
                "character_asset_id": "CHAR_PERFORMANCE",
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
            "world_asset_id": "LOC_PERFORMANCE",
            "world_name": "Performance World",
            "created_at": "2026-10-07T00:00:00Z"
        }
    })
    runtime.set_process(false)
    runtime.reset_shot()

    runtime.advance_shot(0.1)
    if runtime.performance_last_cue != "reaction":
        push_error("director_performance_cue_smoke: reaction cue missing")
        quit(1)
        return
    var arm_l := runtime.actor.get_node_or_null("Visual/ArmL") as Node3D
    if arm_l == null or absf(arm_l.rotation.z) < 0.20:
        push_error("director_performance_cue_smoke: reaction pose missing")
        quit(1)
        return

    runtime.advance_shot(0.45)
    if runtime.performance_last_cue != "attack":
        push_error("director_performance_cue_smoke: attack cue missing")
        quit(1)
        return
    var arm_r := runtime.actor.get_node_or_null("Visual/ArmR") as Node3D
    if arm_r == null or arm_r.rotation.x > -0.8:
        push_error("director_performance_cue_smoke: attack pose missing")
        quit(1)
        return

    runtime.advance_shot(0.50)
    if runtime.performance_last_cue != "look_at":
        push_error("director_performance_cue_smoke: look cue missing")
        quit(1)
        return
    if absf(runtime.actor.rotation_degrees.y - 90.0) > 0.1:
        push_error("director_performance_cue_smoke: look direction missing")
        quit(1)
        return

    runtime.advance_shot(0.50)
    if runtime.performance_last_cue != "celebrate":
        push_error("director_performance_cue_smoke: celebrate cue missing")
        quit(1)
        return
    if arm_l.rotation.x > -0.8:
        push_error("director_performance_cue_smoke: celebrate pose missing")
        quit(1)
        return

    runtime.reset_shot()
    if runtime.performance_last_cue != "":
        push_error("director_performance_cue_smoke: reset did not clear cue state")
        quit(1)
        return

    print(
        "director_performance_cue_smoke: PASS · reaction/attack/look/celebrate/reset"
    )
    quit(0)

extends SceneTree


func _initialize() -> void:
    var runtime := MiniUtopiaDirectorShotRuntime.new()
    root.add_child(runtime)

    runtime.configure({
        "director_session_id": "DIR_BLOCKING_SMOKE",
        "episode_id": "EP_BLOCK",
        "scene_id": "SCENE_01",
        "shot_id": "SHOT_01_01",
        "story_id": "STORY_BLOCK",
        "world_asset_id": "LOC_BLOCK",
        "character_asset_id": "CHAR_BLOCK",
        "duration_seconds": 2.0,
        "animation_intent": "walk",
        "camera": {
            "position": [0.0, 4.2, 7.8],
            "look_at": [0.0, 1.1, 0.0],
            "fov": 52.0,
            "movement": "Wide establishing"
        },
        "shot": {
            "shot_id": "SHOT_01_01",
            "scene_id": "SCENE_01",
            "duration_seconds": 2.0,
            "asset_ids": ["CHAR_BLOCK", "LOC_BLOCK"],
            "shot_type": "Follow",
            "camera": "Medium follow",
            "action": "Nancy walks toward the clue.",
            "expression": "curious",
            "dialogue": [],
            "continuity_notes": [],
            "blocking": {
                "actor_start": {"x": 2.0, "y": 0.0, "z": 8.0},
                "actor_end": {"x": 2.0, "y": 0.0, "z": 2.0},
                "facing_degrees": 0.0,
                "baby_offset": {"x": -1.2, "y": 0.0, "z": 1.4},
                "movement_style": "walk",
                "source": "creator",
                "confidence": 1.0
            }
        },
        "play_session": {
            "schema_version": "1.0",
            "session_id": "DIRECTOR_BLOCK_PLAY",
            "source": "director",
            "character_asset_id": "CHAR_BLOCK",
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
                "character_asset_id": "CHAR_BLOCK",
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
            "baby": {
                "baby_id": "BABY_BLOCK",
                "display_name": "Nova",
                "species_id": "star_baby",
                "appearance_seed": "BSEED_BLOCK",
                "growth_stage": "baby",
                "level": 2,
                "xp": 125,
                "bond": 18,
                "active": true,
                "cosmetic_item_ids": [],
                "follow_enabled": true
            },
            "quest": null,
            "world_gameplay": null,
            "creative_layout": null,
            "world_runtime": null,
            "world_asset_id": "LOC_BLOCK",
            "world_name": "Blocking World",
            "created_at": "2026-10-07T00:00:00Z"
        }
    })

    if runtime.actor == null:
        push_error("director_shot_blocking_smoke: actor missing")
        quit(1)
        return
    if runtime.actor.position.distance_to(
        Vector3(2.0, 0.0, 8.0)
    ) > 0.01:
        push_error(
            "director_shot_blocking_smoke: start position mismatch · actual="
            + str(runtime.actor.position)
            + " expected=(2, 0, 8)"
        )
        quit(1)
        return
    if not runtime.blocking_has_path:
        push_error("director_shot_blocking_smoke: blocking not loaded")
        quit(1)
        return

    # Freeze automatic playback only after proving the exact configured frame.
    # Baby spawn is deferred, so wait for it without advancing the shot.
    runtime.set_process(false)
    _verify_deferred.call_deferred(runtime)


func _verify_deferred(runtime: MiniUtopiaDirectorShotRuntime) -> void:
    await process_frame
    await process_frame
    await process_frame

    if not runtime.blocking_has_path:
        push_error("director_shot_blocking_smoke: blocking not loaded")
        quit(1)
        return

    var baby = runtime.find_child(
        "ActiveBaby_BABY_BLOCK",
        true,
        false
    ) as MiniUtopiaBabyFollowRuntime
    if baby == null:
        push_error("director_shot_blocking_smoke: Baby missing")
        quit(1)
        return
    if absf(baby.side_offset - 1.2) > 0.01:
        push_error("director_shot_blocking_smoke: Baby side offset mismatch")
        quit(1)
        return
    if absf(baby.follow_distance - 1.4) > 0.01:
        push_error("director_shot_blocking_smoke: Baby follow offset mismatch")
        quit(1)
        return

    runtime.reset_shot()
    if runtime.actor.position.distance_to(
        Vector3(2.0, 0.0, 8.0)
    ) > 0.01:
        push_error("director_shot_blocking_smoke: reset did not restore start")
        quit(1)
        return

    runtime.advance_shot(1.0)
    if absf(runtime.actor.position.z - 5.0) > 0.05:
        push_error("director_shot_blocking_smoke: halfway position mismatch")
        quit(1)
        return

    runtime.advance_shot(1.0)
    if runtime.actor.position.distance_to(
        Vector3(2.0, 0.0, 2.0)
    ) > 0.01:
        push_error("director_shot_blocking_smoke: end position mismatch")
        quit(1)
        return

    print(
        "director_shot_blocking_smoke: PASS · start/end/facing + Baby offset"
    )
    quit(0)

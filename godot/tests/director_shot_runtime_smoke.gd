extends SceneTree


func _initialize() -> void:
    var runtime := MiniUtopiaDirectorShotRuntime.new()
    root.add_child(runtime)

    runtime.configure({
        "director_session_id": "DIR_SMOKE",
        "episode_id": "EP_SMOKE",
        "scene_id": "SCENE_01",
        "shot_id": "SHOT_01_01",
        "story_id": "STORY_SMOKE",
        "world_asset_id": "LOC_NEWBIE",
        "character_asset_id": "CHAR_NANCY",
        "duration_seconds": 2.0,
        "animation_intent": "walk",
        "camera": {
            "position": [0.0, 4.2, 7.8],
            "look_at": [0.0, 1.1, 0.0],
            "fov": 52.0,
            "movement": "Wide establishing · gentle push-in"
        },
        "shot": {
            "shot_id": "SHOT_01_01",
            "scene_id": "SCENE_01",
            "duration_seconds": 2.0,
            "asset_ids": ["CHAR_NANCY", "LOC_NEWBIE"],
            "shot_type": "Establishing",
            "camera": "Wide establishing",
            "action": "Nancy walks into frame.",
            "expression": "curious",
            "dialogue": [],
            "continuity_notes": ["Nova follows."]
        },
        "play_session": {
            "schema_version": "1.0",
            "session_id": "DIRECTOR_PLAY_SMOKE",
            "source": "director",
            "character_asset_id": "CHAR_NANCY",
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
                "character_asset_id": "CHAR_NANCY",
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
                "final_stats": {"hp": 100, "atk": 22, "defense": 8},
                "equipped": {
                    "weapon_main": {
                        "item_instance_id": "ITEM_SWORD",
                        "definition_id": "EQ_SWORD",
                        "display_name": "Starwood Sword",
                        "slot": "weapon_main",
                        "rarity": "purple",
                        "mesh_asset_id": null,
                        "animation_class": "one_handed",
                        "rolled_stats": {"hp": 0, "atk": 12, "defense": 0}
                    }
                }
            },
            "baby": {
                "baby_id": "BABY_DIRECTOR",
                "display_name": "Nova",
                "species_id": "star_baby",
                "appearance_seed": "BSEED_SMOKE",
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
            "world_asset_id": "LOC_NEWBIE",
            "world_name": "Newbie Village",
            "created_at": "2026-10-07T00:00:00Z"
        }
    })

    _verify.call_deferred(runtime)


func _verify(runtime: MiniUtopiaDirectorShotRuntime) -> void:
    await process_frame
    await process_frame
    await process_frame

    if runtime.actor == null:
        push_error("director_shot_runtime_smoke: actor missing")
        quit(1)
        return
    if runtime.camera == null:
        push_error("director_shot_runtime_smoke: camera missing")
        quit(1)
        return
    if runtime.get_node_or_null("DirectorWorldContext") == null:
        push_error("director_shot_runtime_smoke: world context missing")
        quit(1)
        return

    var sword = runtime.actor.find_child(
        "Equipment_weapon_main",
        true,
        false
    )
    if sword == null:
        push_error("director_shot_runtime_smoke: equipment missing")
        quit(1)
        return

    var baby = runtime.find_child(
        "ActiveBaby_BABY_DIRECTOR",
        true,
        false
    )
    if baby == null:
        push_error("director_shot_runtime_smoke: Baby missing")
        quit(1)
        return

    var start_z := runtime.actor.position.z
    runtime.advance_shot(0.5)
    if runtime.elapsed_seconds < 0.49:
        push_error("director_shot_runtime_smoke: timing did not advance")
        quit(1)
        return
    if runtime.actor.position.z >= start_z:
        push_error("director_shot_runtime_smoke: walk staging did not move actor")
        quit(1)
        return
    if runtime.progress_ratio() <= 0.0:
        push_error("director_shot_runtime_smoke: progress ratio did not advance")
        quit(1)
        return
    if String(runtime.get_meta("shot_id", "")) != "SHOT_01_01":
        push_error("director_shot_runtime_smoke: shot metadata missing")
        quit(1)
        return

    print(
        "director_shot_runtime_smoke: PASS · actor + equipment + Baby + camera + timing"
    )
    quit(0)

extends SceneTree

func _initialize() -> void:
    var reward_inbox_path := MiniUtopiaQuestRewardWriter.INBOX_PATH
    if FileAccess.file_exists(reward_inbox_path):
        DirAccess.remove_absolute(
            ProjectSettings.globalize_path(reward_inbox_path)
        )

    var world := Node3D.new()
    world.name = "QuestSmokeWorld"
    root.add_child(world)

    var player := Node3D.new()
    player.name = "QuestSmokePlayer"
    player.set_meta("mini_utopia_session_id", "PLAY_SMOKE")
    player.set_meta("mini_utopia_character_asset_id", "CHAR_SMOKE")
    world.add_child(player)

    var runtime := MiniUtopiaQuestRuntime.new()
    runtime.name = "QuestRuntime"
    root.add_child(runtime)

    runtime.configure(
        player,
        {
            "quest_id": "QUEST_SMOKE",
            "title": "Smoke Adventure",
            "world_asset_id": "LOC_SMOKE",
            "objectives": [
                {
                    "objective_id": "arrive",
                    "objective_type": "go_to_location",
                    "label": "Arrive",
                    "target_id": "LOC_SMOKE",
                    "target_count": 1,
                    "order": 0,
                    "metadata": {},
                },
                {
                    "objective_id": "discover",
                    "objective_type": "interact",
                    "label": "Discover clue",
                    "target_id": "clue_01",
                    "target_count": 1,
                    "order": 1,
                    "metadata": {
                        "position": [1.0, 0.0, 0.0],
                        "prompt": "Discover · E",
                    },
                },
                {
                    "objective_id": "fight",
                    "objective_type": "defeat_enemy",
                    "label": "Fight",
                    "target_id": "enemy_01",
                    "target_count": 1,
                    "order": 2,
                    "metadata": {},
                },
                {
                    "objective_id": "loot",
                    "objective_type": "collect_item",
                    "label": "Collect",
                    "target_id": "item_01",
                    "target_count": 1,
                    "order": 3,
                    "metadata": {},
                },
                {
                    "objective_id": "portal",
                    "objective_type": "open_portal",
                    "label": "Open Portal",
                    "target_id": "portal_01",
                    "target_count": 1,
                    "order": 4,
                    "metadata": {
                        "position": [3.0, 0.0, 0.0],
                        "prompt": "Portal · E",
                    },
                },
            ],
        }
    )

    await process_frame

    if runtime.current_objective_id() != "discover":
        push_error(
            "quest_runtime_smoke: ARRIVE did not auto-advance"
        )
        quit(1)
        return

    player.global_position = Vector3(1.0, 0.0, 0.0)
    if not runtime.try_interact():
        push_error(
            "quest_runtime_smoke: discovery interaction did not advance"
        )
        quit(1)
        return

    if not runtime.record_event("defeat_enemy", "enemy_01", 1):
        push_error(
            "quest_runtime_smoke: enemy event did not advance"
        )
        quit(1)
        return

    if not runtime.record_event("collect_item", "item_01", 1):
        push_error(
            "quest_runtime_smoke: item event did not advance"
        )
        quit(1)
        return

    player.global_position = Vector3(3.0, 0.0, 0.0)
    if not runtime.try_interact():
        push_error(
            "quest_runtime_smoke: portal interaction did not advance"
        )
        quit(1)
        return

    if not runtime.is_complete():
        push_error(
            "quest_runtime_smoke: Quest did not complete"
        )
        quit(1)
        return

    await process_frame

    if not FileAccess.file_exists(reward_inbox_path):
        push_error(
            "quest_runtime_smoke: Quest completion receipt was not written"
        )
        quit(1)
        return

    var reward_file := FileAccess.open(
        reward_inbox_path,
        FileAccess.READ
    )
    var reward_payload = JSON.parse_string(
        reward_file.get_as_text()
    )
    var completions: Array = reward_payload.get("completions", [])
    if completions.size() != 1:
        push_error(
            "quest_runtime_smoke: expected exactly one completion receipt"
        )
        quit(1)
        return
    if String(completions[0].get("quest_id", "")) != "QUEST_SMOKE":
        push_error(
            "quest_runtime_smoke: completion receipt Quest mismatch"
        )
        quit(1)
        return
    if String(completions[0].get("session_id", "")) != "PLAY_SMOKE":
        push_error(
            "quest_runtime_smoke: completion receipt Session mismatch"
        )
        quit(1)
        return

    print(
        "quest_runtime_smoke: PASS · generic Quest complete + reward receipt"
    )
    quit(0)

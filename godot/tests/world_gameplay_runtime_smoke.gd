extends SceneTree

func _initialize() -> void:
    var player := Node3D.new()
    player.name = "WorldGameplaySmokePlayer"
    root.add_child(player)

    var runtime := MiniUtopiaWorldGameplayRuntime.new()
    runtime.name = "WorldGameplayRuntime"
    root.add_child(runtime)

    runtime.configure(
        player,
        {
            "schema_version": "1.0",
            "world_asset_id": "LOC_NEWBIE_VILLAGE",
            "modes": ["explore", "quest", "story_play"],
            "quest_ids": ["QUEST_ONE"],
            "story_ids": ["STORY_ONE"],
            "targets": [
                {
                    "target_id": "training_skeleton_01",
                    "target_type": "defeat_enemy",
                    "position": null,
                    "metadata": {},
                },
                {
                    "target_id": "newbie_village_portal",
                    "target_type": "open_portal",
                    "position": [0.0, 0.45, -30.0],
                    "metadata": {"prompt": "Portal · E"},
                },
            ],
        }
    )

    for mode in ["explore", "quest", "story_play"]:
        if not runtime.supports_mode(mode):
            push_error(
                "world_gameplay_smoke: missing mode " + mode
            )
            quit(1)
            return

    if runtime.quest_ids() != ["QUEST_ONE"]:
        push_error("world_gameplay_smoke: Quest references mismatch")
        quit(1)
        return

    if runtime.story_ids() != ["STORY_ONE"]:
        push_error("world_gameplay_smoke: Story references mismatch")
        quit(1)
        return

    var portal := runtime.target_by_id("newbie_village_portal")
    if portal.is_empty():
        push_error("world_gameplay_smoke: Portal target missing")
        quit(1)
        return

    if (
        String(
            player.get_meta(
                "mini_utopia_world_gameplay_id",
                ""
            )
        )
        != "LOC_NEWBIE_VILLAGE"
    ):
        push_error("world_gameplay_smoke: Player World metadata mismatch")
        quit(1)
        return

    print(
        "world_gameplay_smoke: PASS · one World → Explore + Quest + Story Play"
    )
    quit(0)

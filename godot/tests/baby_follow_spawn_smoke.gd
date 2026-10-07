extends SceneTree

func _initialize() -> void:
    var world := Node3D.new()
    world.name = "SmokeWorld"
    root.add_child(world)

    var player := CharacterBody3D.new()
    player.name = "SmokePlayer"
    world.add_child(player)

    var runtime := MiniUtopiaCreatorPlayRuntime.new()
    runtime.name = "CreatorPlayRuntime"
    player.add_child(runtime)
    runtime._player = player

    runtime._spawn_baby(
        {
            "baby_id": "BABY_SMOKE_001",
            "display_name": "Nova Smoke",
            "species_id": "star_baby",
            "active": true,
        }
    )

    await process_frame
    await process_frame

    var baby := world.get_node_or_null(
        "ActiveBaby_BABY_SMOKE_001"
    ) as MiniUtopiaBabyFollowRuntime
    if baby == null:
        push_error(
            "baby_follow_smoke: deferred Active Baby did not enter SceneTree"
        )
        quit(1)
        return

    if baby.target != player:
        push_error(
            "baby_follow_smoke: Active Baby target was not configured"
        )
        quit(1)
        return

    var name_label := baby.find_child(
        "BabyName",
        true,
        false
    ) as Label3D
    if name_label == null or "Nova Smoke" not in name_label.text:
        push_error(
            "baby_follow_smoke: visible Baby name label missing"
        )
        quit(1)
        return

    var before := baby.global_position
    player.global_position += Vector3(3.0, 0.0, 0.0)
    baby._process(0.35)
    if baby.global_position.distance_to(before) < 0.05:
        push_error(
            "baby_follow_smoke: Active Baby did not follow moved Player"
        )
        quit(1)
        return

    print(
        "baby_follow_smoke: PASS · deferred spawn + visible name + follow"
    )
    quit(0)

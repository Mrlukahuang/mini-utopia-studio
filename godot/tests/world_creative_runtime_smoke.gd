extends SceneTree

func _initialize() -> void:
    var runtime := MiniUtopiaWorldCreativeRuntime.new()
    root.add_child(runtime)
    runtime.configure({
        "world_asset_id": "LOC_SMOKE",
        "decorations": [
            {
                "decoration_id": "DECOR_STAR",
                "prop_type": "star_lamp",
                "display_name": "Star Lamp",
                "position": [2.0, 0.0, 3.0],
                "rotation_y": 45.0,
                "scale": 1.2,
            },
            {
                "decoration_id": "DECOR_BENCH",
                "prop_type": "toy_bench",
                "display_name": "Toy Bench",
                "position": [-2.0, 0.0, 1.0],
                "rotation_y": 90.0,
                "scale": 1.0,
            }
        ]
    })

    if runtime.get_child_count() != 2:
        push_error("world_creative_runtime_smoke: expected 2 decorations")
        quit(1)
        return

    var star := runtime.get_node_or_null("Creative_DECOR_STAR") as Node3D
    var bench := runtime.get_node_or_null("Creative_DECOR_BENCH") as Node3D
    if star == null or bench == null:
        push_error("world_creative_runtime_smoke: named decorations missing")
        quit(1)
        return

    if star.position != Vector3(2.0, 0.0, 3.0):
        push_error("world_creative_runtime_smoke: Star Lamp position mismatch")
        quit(1)
        return

    if absf(star.scale.x - 1.2) > 0.01:
        push_error("world_creative_runtime_smoke: Star Lamp scale mismatch")
        quit(1)
        return

    print("world_creative_runtime_smoke: PASS · saved delta spawned")
    quit(0)

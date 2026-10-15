extends SceneTree

func _initialize() -> void:
    var world := load("res://scenes/main.tscn") as PackedScene
    if world == null:
        _fail("main village scene is missing")
        return
    var scene := world.instantiate()
    root.add_child(scene)
    await process_frame

    var button := scene.get_node_or_null("HUD/OpenCreatorButton") as Button
    if button == null:
        _fail("child-facing Create Hero entrypoint is missing")
        return
    if button.text != "🎨 Create a Hero":
        _fail("Create Hero label is not child-facing")
        return
    if button.pressed.get_connections().is_empty():
        _fail("village Hero button does not trigger any runtime action")
        return
    if not ResourceLoader.exists("res://scenes/character_creator.tscn"):
        _fail("runtime Creator scene does not exist")
        return

    # W1.5: actually instantiate imported 3D houses and animated villager
    # bodies, rather than asserting a claimed population count in metadata.
    var houses := get_nodes_in_group("kaykit_village_house")
    if houses.size() < 20:
        _fail("required twenty KayKit buildings not visible in live village")
        return
    var shapes_by_source := {}
    for house in houses:
        shapes_by_source[int(house.get_meta("kaykit_source_model", -1))] = true
        var body := house as StaticBody3D
        if body == null or body.get_node_or_null("OfficialKayKitBuilding") == null:
            _fail("house does not contain official KayKit mesh")
            return
        var shape := body.get_node_or_null("CollisionShape3D") as CollisionShape3D
        if shape == null or shape.shape == null or shape.disabled:
            _fail("KayKit house is missing a blocking collider")
            return

    if shapes_by_source.size() < 10:
        _fail("different colors do not count as ten different KayKit building shapes")
        return

    # Actual official GLTF surfaces remain in scene nodes, but their drawing
    # is done by grouped MultiMeshes; physics blocks remain independent.
    var rendered_batches := get_nodes_in_group("lane_a_static_batch")
    if rendered_batches.size() < 8:
        _fail("static architecture was not turned into real MultiMesh draw batches")
        return
    var disabled_original_meshes := 0
    for house in houses:
        var official := house.get_node_or_null("OfficialKayKitBuilding") as Node3D
        for part in official.find_children("*", "MeshInstance3D", true, false):
            if not (part as MeshInstance3D).visible:
                disabled_original_meshes += 1
    if disabled_original_meshes < 20:
        _fail("unbatched building meshes still render separately")
        return
    var perf := scene.get_node_or_null("HUD/LaneAPerformanceBadge") as Label
    if perf == null or perf.visible:
        _fail("FPS diagnostic must be hidden until long press")
        return
    scene.call("_toggle_performance_badge")
    if not perf.visible or not perf.text.contains("FPS"):
        _fail("long-hold FPS diagnostic toggle is not connected")
        return
    scene.call("_toggle_performance_badge")
    if perf.visible:
        _fail("FPS diagnostic cannot be hidden again")
        return

    var villagers := get_nodes_in_group("kaykit_village_npc")
    if villagers.size() < 15:
        _fail("required fifteen animated KayKit villagers not present")
        return
    var unique_looks := {}
    for villager in villagers:
        var body := villager as CharacterBody3D
        var look_id := String(villager.get_meta("kaykit_npc_look", ""))
        unique_looks[look_id] = true
        var collider := body.get_node_or_null("CollisionShape3D") as CollisionShape3D
        var official := body.get_node_or_null("KayKitBody") as Node3D
        var animation := official.find_child("AnimationPlayer", true, false) as AnimationPlayer if official != null else null
        if (collider == null or collider.shape == null or collider.disabled
            or official == null or not official.visible or animation == null
            or not animation.has_animation("Idle")
            or not animation.has_animation("Walking_A")):
            _fail("villager has no official visible KayKit rig / animations / collision")
            return
    if unique_looks.size() != 15:
        _fail("villagers repeat a look identity")
        return
    # Different roles must be visible meshes rather than 15 identical names.
    for villager in villagers:
        var costume := villager.get_node_or_null("VillagerCostume") as MeshInstance3D
        var headwear := villager.get_node_or_null("VillagerHeadgear") as MeshInstance3D
        if costume == null or costume.mesh == null or headwear == null or headwear.mesh == null:
            _fail("one of fifteen villagers has no visible distinct costume or hat")
            return


    var player := scene.get_node_or_null("Player") as CharacterBody3D
    if player == null or player.get_node_or_null("CollisionShape3D") == null:
        _fail("player has no physical collider")
        return

    # Test actual physics-space intersections at known playable obstacles.
    # Checking that a shape exists alone cannot prove it blocks a ray.
    await physics_frame
    var space: PhysicsDirectSpaceState3D = (scene as Node3D).get_world_3d().direct_space_state
    var house_hit: Dictionary = space.intersect_ray(
        PhysicsRayQueryParameters3D.create(
            Vector3(-23.0, 1.5, 10.0), Vector3(-23.0, 1.5, 4.0)
        )
    )
    if house_hit.is_empty() or not (house_hit["collider"] as Node).is_in_group("kaykit_village_house"):
        _fail("actual physics ray passed through KayKit house")
        return
    # Home B's official glTF is 6.14 m tall and 5.27 m deep when
    # scaled; a one-size 4.3x4.4 box used to allow roof/wall penetration.
    var tall_house_wall: Dictionary = space.intersect_ray(
        PhysicsRayQueryParameters3D.create(
            Vector3(-15.0, 1.5, 10.0), Vector3(-15.0, 1.5, 8.45)
        )
    )
    var tall_house_roof: Dictionary = space.intersect_ray(
        PhysicsRayQueryParameters3D.create(
            Vector3(-19.0, 5.5, 6.0), Vector3(-16.5, 5.5, 6.0)
        )
    )
    if (tall_house_wall.is_empty() or tall_house_roof.is_empty()
        or not (tall_house_wall["collider"] as Node).is_in_group("kaykit_village_house")
        or not (tall_house_roof["collider"] as Node).is_in_group("kaykit_village_house")):
        _fail("KayKit home B roof or full wall depth allows penetration")
        return
    var npc_hit: Dictionary = space.intersect_ray(
        PhysicsRayQueryParameters3D.create(
            Vector3(-6.8, 0.9, 19.0), Vector3(-6.8, 0.9, 13.0)
        )
    )
    if npc_hit.is_empty() or not (npc_hit["collider"] as Node).is_in_group("kaykit_village_npc"):
        _fail("actual physics ray passed through roaming KayKit NPC")
        return

    # The bubble is a real 3D child-only Chinese greeting, not a debug label.
    # Moving a synthetic player nearby should reveal it; leaving hides it.
    var npc := villagers[0] as CharacterBody3D
    var greeting := npc.get_node_or_null("GreetingText") as Label3D
    var bubble := npc.get_node_or_null("GreetingBubble") as Sprite3D
    if greeting == null or greeting.text != "你好！" or bubble == null or bubble.visible:
        _fail("NPC did not create a private, initially hidden greeting bubble")
        return
    player.global_position = npc.global_position + Vector3(0.0, 1.0, 2.1)
    await physics_frame
    if not greeting.visible or not bubble.visible:
        _fail("approaching a villager did not reveal the greeting")
        return
    player.global_position = Vector3(0.0, 1.0, 34.0)
    await physics_frame
    if bubble.visible:
        _fail("villager greeting stayed open after player left")
        return

    # Distant NPC bodies keep capsules blocking players; animation and
    # physics thinking sleep until the camera/player approaches.
    npc.set_performance_lod(30.0, false)
    if npc.is_physics_processing() or npc.animation_player.active:
        _fail("far NPC still runs full physics or skeletal animation")
        return
    npc.set_performance_lod(2.0, true)
    if not npc.is_physics_processing() or not npc.animation_player.active:
        _fail("near NPC failed to wake after distance-based LOD")
        return

    print("village_creator_entrypoint_smoke: PASS · 20 KayKit houses / 15 animated collider NPCs")
    quit(0)


func _fail(message: String) -> void:
    push_error("village_creator_entrypoint_smoke: FAIL · " + message)
    quit(1)

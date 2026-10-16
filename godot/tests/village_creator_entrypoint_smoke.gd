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
    if button.text != "Create a Hero":
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

    # Simulate the two runtime quality tiers deterministically, independent
    # of CI/headless FPS. Automatic 3s/5s thresholds remain in village.gd.
    var sun := scene.get_node_or_null("VillageSun") as DirectionalLight3D
    if sun == null or not sun.shadow_enabled:
        _fail("expected one sun shadow before adaptive quality downgrade")
        return
    scene.call("_set_quality_low", true)
    if not scene._quality_low or sun.shadow_enabled or absf(root.get_viewport().scaling_3d_scale - 0.6) > 0.005:
        _fail("low quality did not reduce 3D scale to 0.6 and disable sun shadows")
        return
    scene.call("_set_quality_low", false)
    if scene._quality_low or not sun.shadow_enabled or absf(root.get_viewport().scaling_3d_scale - 0.75) > 0.005:
        _fail("high quality did not restore 0.75 3D scale and one sun shadow")
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
    # LOD intentionally wakes sleeping NPCs only every 0.25 seconds.
    await create_timer(0.38).timeout
    await physics_frame
    if not greeting.visible or not bubble.visible:
        _fail("approaching a villager did not reveal the greeting")
        return
    player.global_position = Vector3(0.0, 1.0, 34.0)
    await create_timer(0.38).timeout
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

    # Simulate a child traversing the central village road and returning to
    # spawn, with real CharacterBody3D movement and physics-world overlaps.
    if not await _walk_main_road_round_trip(scene as Node3D, player):
        return

    print("village_creator_entrypoint_smoke: PASS · 20 KayKit houses / 15 animated collider NPCs")
    quit(0)


# A full outbound/return trip round the fountain along the central path.
# Use small real physics movements, not teleporting or ray-only assertions.
func _walk_main_road_round_trip(scene: Node3D, player: CharacterBody3D) -> bool:
    var saved := player.global_position
    player.set_physics_process(false)
    player.velocity = Vector3.ZERO
    player.global_position = Vector3(0.0, 0.15, 15.0)
    await physics_frame
    var waypoints: Array[Vector3] = [
        Vector3(0.0, 0.15, -3.5),
        Vector3(3.1, 0.15, -5.0),
        Vector3(3.1, 0.15, -15.0),
        Vector3(0.0, 0.15, -17.0),
        Vector3(0.0, 0.15, -25.0),
        Vector3(0.0, 0.15, -17.0),
        Vector3(-3.1, 0.15, -15.0),
        Vector3(-3.1, 0.15, -5.0),
        Vector3(0.0, 0.15, -3.5),
        Vector3(0.0, 0.15, 15.0),
    ]
    var collider := player.get_node("CollisionShape3D") as CollisionShape3D
    var world := scene.get_world_3d()
    var checks := 0
    for target in waypoints:
        var steps := 0
        while Vector2(player.global_position.x, player.global_position.z).distance_to(
            Vector2(target.x, target.z)
        ) > 0.55 and steps < 140:
            await physics_frame
            var delta_pos := target - player.global_position
            delta_pos.y = 0.0
            var motion := delta_pos.normalized() * minf(0.42, delta_pos.length())
            var contact := player.move_and_collide(motion)
            if contact != null:
                # Sliding along a building or NPC must never penetrate them.
                var tangent := motion.slide(contact.get_normal())
                if tangent.length_squared() > 0.0001:
                    player.move_and_collide(tangent)
            var test := PhysicsShapeQueryParameters3D.new()
            test.shape = collider.shape
            test.transform = collider.global_transform
            test.exclude = [player.get_rid()]
            var overlaps := world.direct_space_state.intersect_shape(test, 16)
            for overlap in overlaps:
                var hit := overlap["collider"] as Node
                if hit != null and (
                    hit.is_in_group("kaykit_village_house")
                    or hit.is_in_group("kaykit_village_npc")
                    or hit.is_in_group("kaykit_village_nature")
                ):
                    _fail("road walk penetrated solid obstacle: " + hit.name)
                    return false
            checks += 1
            steps += 1
        if steps >= 140:
            _fail("player became stuck on the main village road before " + str(target))
            return false
    player.global_position = saved
    player.set_physics_process(true)
    print("lane_a_road_walk: PASS physics_steps=%d complete_return=true" % checks)
    return true


func _fail(message: String) -> void:
    push_error("village_creator_entrypoint_smoke: FAIL · " + message)
    quit(1)

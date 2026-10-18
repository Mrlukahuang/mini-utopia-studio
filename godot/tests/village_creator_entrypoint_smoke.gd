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
    var environments := scene.find_children("*", "WorldEnvironment", true, false)
    var environment_node := environments[0] as WorldEnvironment if not environments.is_empty() else null
    if environment_node == null or environment_node.environment == null:
        _fail("village pastel sky Environment was not created")
        return
    var environment := environment_node.environment
    if environment.background_color.b < environment.background_color.r or environment.ambient_light_energy < 0.5:
        _fail("village sky is too dim or no longer pastel blue")
        return
    # Preserve the original low-energy distance haze for contrast while
    # preventing that same fog from repainting the BG_COLOR sky gray-blue.
    if (not environment.fog_enabled
        or environment.fog_sky_affect > 0.05
        or absf(environment.fog_light_energy - 0.34) > 0.01):
        _fail("fog either darkens the sky or washes out the village")
        return
    var touch := scene.get_node_or_null("TouchControls") as MiniUtopiaTouchControls
    if touch != null:
        # Headless tests do not have a touchscreen. Build the same buttons
        # explicitly so a missing Web glyph cannot silently regress.
        touch._build_controls()
        var forward := touch.get_node_or_null("Overlay/MoveForward") as Button
        if forward == null or forward.text != "上":
            _fail("forward touch button uses an unsupported Web glyph")
            return
        forward.button_down.emit()
        if not Input.is_action_pressed("move_forward"):
            _fail("forward touch button no longer presses the move action")
            return
        forward.button_up.emit()
        if Input.is_action_pressed("move_forward"):
            _fail("forward touch button failed to release move action")
            return
    if touch != null and touch.has_node("Overlay/Jump"):
        var jump := touch.get_node("Overlay/Jump") as Button
        if jump.offset_right > -10.0:
            _fail("iPad Jump button extends too close to the right-edge safe margin")
            return

    var perf := scene.get_node_or_null("HUD/LaneAPerformanceBadge") as Label
    if perf == null or perf.visible:
        _fail("FPS diagnostic must be hidden until long press")
        return
    var info := scene.get_node_or_null("HUD/LaneAFPSInfoButton") as Button
    if info == null or info.text != "i" or info.disabled:
        _fail("iPad Safari lacks the always-tappable FPS info button")
        return
    info.pressed.emit()
    if not perf.visible or not perf.text.contains("FPS"):
        _fail("tapping the info button failed to open FPS stats")
        return
    info.pressed.emit()
    if perf.visible:
        _fail("tapping the info button again failed to hide FPS stats")
        return

    var hold := InputEventScreenTouch.new()
    hold.index = 3
    hold.pressed = true
    hold.position = Vector2(42, 38)
    scene._input(hold)
    scene.call("_tick_performance_badge", 1.02)
    if not perf.visible:
        _fail("one-second InputEventScreenTouch hold failed to open FPS stats")
        return
    hold.pressed = false
    scene._input(hold)
    info.pressed.emit()
    if perf.visible:
        _fail("touch release or info button did not hide FPS stats")
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

    # The outer terrain is purely visual: fill overhead blue exposure
    # without expanding walkable ground or adding costly edge collisions.
    var meadow := scene.get_node_or_null("WoodlandMeadowApron") as MeshInstance3D
    if meadow == null or not (meadow.mesh is BoxMesh):
        _fail("woodland exterior has no visual terrain backdrop")
        return
    var meadow_size := (meadow.mesh as BoxMesh).size
    if meadow_size.x < 100.0 or meadow_size.z < 100.0 or meadow.position.y > -0.2:
        _fail("outer woodland meadow is too small or covers KayKit ground")
        return
    if scene.get_node_or_null("WoodlandMeadowApronCollision") != null or meadow.visible:
        _fail("outer meadow must be collider-free and statically batched")
        return

    var forest_obstacles := get_nodes_in_group("kaykit_village_nature")
    if forest_obstacles.size() < 44:
        _fail("original KayKit forest has fewer than 44 physical trees/rocks")
        return
    for thing in forest_obstacles:
        var shape := thing.get_node_or_null("CollisionShape3D") as CollisionShape3D
        if not (thing is StaticBody3D) or shape == null or not (shape.shape is BoxShape3D):
            _fail("forest collision was not a lightweight box")
            return
    var forest_batches := 0
    for node in get_nodes_in_group("lane_a_static_batch"):
        if String(node.name).contains("KayKitTree") or String(node.name).contains("KayKitRock"):
            forest_batches += 1
            if node.cast_shadow != GeometryInstance3D.SHADOW_CASTING_SETTING_OFF:
                _fail("forest geometry still casts costly shadows")
                return
    var natural_edges := get_nodes_in_group("lane_a_natural_edge")
    if natural_edges.size() != 4:
        _fail("woodland does not contain all four physical boundary rails")
        return
    for edge in natural_edges:
        var blocker := edge.get_node_or_null("CollisionShape3D") as CollisionShape3D
        if not (edge is StaticBody3D) or blocker == null or not (blocker.shape is BoxShape3D):
            _fail("natural edge must block with lightweight BoxShape3D")
            return
    var dressed_edge := false
    var dressed_hills := false
    for batch_node in get_nodes_in_group("lane_a_static_batch"):
        if String(batch_node.name).begins_with("KayKitEdgeTree"):
            dressed_edge = true
        if String(batch_node.name).begins_with("KayKitHill"):
            dressed_hills = true
    if not dressed_edge or not dressed_hills:
        _fail("forest edges or hill silhouettes have no real KayKit scenery")
        return

    print("lane_a_forest: shadowless_draw_batches=%d" % forest_batches)
    if forest_batches < 2:
        _fail("forest trees and rocks did not render in efficient MultiMesh batches: " + str(forest_batches))
        return

    var market := get_nodes_in_group("kaykit_village_props")
    if market.size() != 30:
        _fail("market props do not retain exactly 30 simple physical blockers")
        return
    for item in market:
        var collider := item.get_node_or_null("CollisionShape3D") as CollisionShape3D
        if not (item is StaticBody3D) or collider == null or not (collider.shape is BoxShape3D):
            _fail("KayKit market prop must use a lightweight BoxShape3D")
            return
    var grass := 0
    var road := 0
    var market_batches := 0
    for entry in get_nodes_in_group("lane_a_static_batch"):
        var batch := entry as MultiMeshInstance3D
        if batch == null or batch.multimesh == null:
            continue
        var count := batch.multimesh.instance_count
        if String(batch.name).begins_with("KayKitGrass"):
            grass += count
        elif String(batch.name).begins_with("KayKitStoneRoad"):
            road += count
        elif String(batch.name).begins_with("KayKitMarket"):
            market_batches += 1
            if batch.cast_shadow != GeometryInstance3D.SHADOW_CASTING_SETTING_OFF:
                _fail("small market objects still cast expensive shadow maps")
                return
    if grass < 625 or road < 35 or market_batches < 2:
        _fail("official KayKit terrain/market were not batched: " + str([grass, road, market_batches]))
        return
    print("lane_a_props: grass_instances=%d road_instances=%d market_batches=%d" % [grass, road, market_batches])

    var villagers := get_nodes_in_group("kaykit_village_npc")
    if villagers.size() < 15:
        _fail("required fifteen animated KayKit villagers not present")
        return
    # Spawn in many street blocks, not a dense line of neighbours by the gate.
    var occupied_blocks: Dictionary = {}
    for a in range(villagers.size()):
        var first := villagers[a] as MiniUtopiaKaykitVillageNPC
        var first_home: Vector3 = first.home
        occupied_blocks[floori(first_home.z / 8.0)] = true
        if absf(first_home.x) < 4.5:
            _fail("villager spawned on the central stone road")
            return
        for b in range(a + 1, villagers.size()):
            var other := villagers[b] as MiniUtopiaKaykitVillageNPC
            if first_home.distance_to(other.home) < 3.0:
                _fail("two KayKit villagers spawn too close together")
                return
    if occupied_blocks.size() < 6:
        _fail("villagers are still clustered in too few village blocks")
        return
    var unique_looks := {}
    var unique_source_rigs := {}
    for villager in villagers:
        var body := villager as CharacterBody3D
        var look_id := String(villager.get_meta("kaykit_npc_look", ""))
        unique_looks[look_id] = true
        var source_path := String(villager.get_meta("kaykit_npc_rig_resource", ""))
        if not source_path.begins_with("res://assets/kaykit/adventurers/"):
            _fail("villager must reference a real imported KayKit rig, not a pretend look")
            return
        unique_source_rigs[source_path] = true
        # A physical CollisionShape3D is fine; visible MeshInstance3D
        # primitives directly under the actor (hats, ears, boxes) are not.
        for child in villager.get_children():
            if child is MeshInstance3D:
                _fail("villager still draws a primitive hat or costume")
                return
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
    if unique_source_rigs.size() < 6:
        _fail("villagers repeat the same underlying Knight model instead of six official rigs")
        return

    var player := scene.get_node_or_null("Player") as CharacterBody3D
    # #460 diagnosis: measure actual landed physical capsule and source Knight
    # bounds against the visible KayKit ground. Logs only; no gameplay change.
    await create_timer(0.6).timeout
    var capsule := player.get_node("CollisionShape3D") as CollisionShape3D
    var capsule_bottom: float = capsule.global_position.y - (capsule.shape as CapsuleShape3D).height * 0.5
    var knight := player.get_node_or_null("KayKitBody") as Node3D
    var knight_min_y := INF
    var knight_max_y := -INF
    if knight != null:
        for part in knight.find_children("*", "MeshInstance3D", true, false):
            var mesh_part := part as MeshInstance3D
            if mesh_part.mesh == null or not mesh_part.is_visible_in_tree():
                continue
            var bounds: AABB = mesh_part.mesh.get_aabb()
            for corner in range(8):
                var point: Vector3 = bounds.get_endpoint(corner)
                var y: float = (mesh_part.global_transform * point).y
                knight_min_y = minf(knight_min_y, y)
                knight_max_y = maxf(knight_max_y, y)
    # True root cause: cosmetic Hill/VillageMound meshes must never rise
    # above the flat collision plane. These 6 decorative patches are batched.
    var ground_patches := 0
    for patch_node in scene.get_children():
        if not (patch_node is MeshInstance3D):
            continue
        if not (String(patch_node.name).begins_with("Hill")
                or String(patch_node.name) == "VillageMound"):
            continue
        var patch_mesh := patch_node as MeshInstance3D
        if not (patch_mesh.mesh is CylinderMesh):
            _fail("raised non-colliding decorative grass hill remains: " + patch_mesh.name)
            return
        var patch_top := (patch_mesh.global_transform * patch_mesh.mesh.get_aabb().get_endpoint(7)).y
        if patch_top > -0.049:
            _fail("grass patch visually intersects landed player: %s at Y=%f" % [patch_mesh.name, patch_top])
            return
        if patch_top < -0.16:
            _fail("grass patch disappeared beneath KayKit tiles: " + patch_mesh.name)
            return
        ground_patches += 1
    if ground_patches != 6:
        _fail("expected six batched ground-level grass patches: " + str(ground_patches))
        return
    var tiles_top_y := -0.16
    var grass_batches := get_nodes_in_group("lane_a_static_batch")
    for batch_node in grass_batches:
        if String(batch_node.name).begins_with("KayKitGrass"):
            var grass_batch := batch_node as MultiMeshInstance3D
            tiles_top_y = maxf(tiles_top_y, -0.16 + grass_batch.multimesh.mesh.get_aabb().end.y * 1.58)
    print("lane_a_460_probe: root_y=%.3f capsule_bottom=%.3f knight_min=%.3f knight_max=%.3f physical_ground_top=-0.050 grass_top=%.3f on_floor=%s" % [
        player.global_position.y, capsule_bottom, knight_min_y, knight_max_y, tiles_top_y, str(player.is_on_floor())
    ])
    if player == null or player.get_node_or_null("CollisionShape3D") == null:
        _fail("player has no physical collider")
        return

    # Name and combat values must share one camera-facing label anchored
    # above the active KayKit Hero's head, not a second floating HUD label.
    var head_labels := player.find_children("CombatLabel", "Label3D", true, false)
    if head_labels.size() != 1:
        _fail("player requires exactly one name + stats billboard")
        return
    var head_label := head_labels[0] as Label3D
    if (head_label.billboard != BaseMaterial3D.BILLBOARD_ENABLED
        or head_label.position.y < 2.5
        or head_label.width < 500.0):
        _fail("Hero name billboard is off-center or too narrow")
        return
    var play_state := player.get_node_or_null("CreatorPlayRuntime") as MiniUtopiaCreatorPlayRuntime
    if play_state == null:
        _fail("selected Hero session missing from player")
        return
    var earlier_name: String = String(play_state.payload.get("character_name", ""))
    play_state.payload["character_name"] = "小冒险家"
    player.call("_update_combat_label")
    if (not head_label.text.begins_with("小冒险家\n")
        or not head_label.text.contains("❤️ ")
        or not head_label.text.contains("⚔️ ")
        or not head_label.text.contains("🛡️ ")):
        _fail("Hero name and HP/ATK/DEF do not appear in a single billboard")
        return
    play_state.payload["character_name"] = earlier_name
    player.call("_update_combat_label")

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

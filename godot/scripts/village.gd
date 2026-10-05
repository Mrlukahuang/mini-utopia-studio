extends Node3D

var palette = {
    "grass": Color("#6E9F61"),
    "grass2": Color("#86B970"),
    "grass_dark": Color("#527C4C"),
    "path": Color("#C9895F"),
    "path_light": Color("#E4B27C"),
    "wood": Color("#7A4937"),
    "wood_light": Color("#A96A45"),
    "cream": Color("#EBC9A4"),
    "cream_light": Color("#F4DFC1"),
    "pink": Color("#C96D73"),
    "mint": Color("#6FAE90"),
    "lavender": Color("#8E78A9"),
    "leaf": Color("#547D45"),
    "leaf2": Color("#7DA258"),
    "stone": Color("#AAA09A"),
    "mushroom_red": Color("#C9563F"),
    "mushroom_orange": Color("#D9824E"),
    "mushroom_spot": Color("#F4DFC1"),
}

func _ready() -> void:
    _setup_environment()
    _build_ground()
    _build_path()
    _build_village()
    _build_forest()
    _build_storybook_dressing()
    _build_locked_gate()

func _mat(color: Color, roughness := 0.86) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = color
    m.roughness = roughness
    return m

func _box(name: String, pos: Vector3, size: Vector3, color: Color, collision := false) -> MeshInstance3D:
    var mesh := BoxMesh.new()
    mesh.size = size
    var node := MeshInstance3D.new()
    node.name = name
    node.mesh = mesh
    node.material_override = _mat(color)
    node.position = pos
    add_child(node)
    if collision:
        var body := StaticBody3D.new()
        var shape := CollisionShape3D.new()
        var box := BoxShape3D.new()
        box.size = size
        shape.shape = box
        body.position = pos
        body.add_child(shape)
        add_child(body)
    return node

func _sphere(name: String, pos: Vector3, radius: float, color: Color, squash := Vector3.ONE) -> MeshInstance3D:
    var mesh := SphereMesh.new()
    mesh.radius = radius
    mesh.height = radius * 2.0
    var node := MeshInstance3D.new()
    node.name = name
    node.mesh = mesh
    node.material_override = _mat(color)
    node.position = pos
    node.scale = squash
    add_child(node)
    return node

func _cylinder(name: String, pos: Vector3, radius: float, height: float, color: Color, collision := false) -> MeshInstance3D:
    var mesh := CylinderMesh.new()
    mesh.top_radius = radius
    mesh.bottom_radius = radius * 1.08
    mesh.height = height
    var node := MeshInstance3D.new()
    node.name = name
    node.mesh = mesh
    node.material_override = _mat(color)
    node.position = pos
    add_child(node)
    if collision:
        var body := StaticBody3D.new()
        var shape := CollisionShape3D.new()
        var cyl := CylinderShape3D.new()
        cyl.radius = radius
        cyl.height = height
        shape.shape = cyl
        body.position = pos
        body.add_child(shape)
        add_child(body)
    return node

func _setup_environment() -> void:
    var world_env := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color("#88BBC4")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#E7C8A4")
    env.ambient_light_energy = 0.34
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.fog_enabled = true
    env.fog_light_color = Color("#B8CFCA")
    env.fog_light_energy = 0.34
    env.fog_density = 0.004
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-48, -38, 0)
    sun.light_color = Color("#F7D6A5")
    sun.light_energy = 0.72
    sun.shadow_enabled = true
    sun.shadow_opacity = 0.8
    add_child(sun)

func _build_ground() -> void:
    _box("VillageGround", Vector3(0, -0.55, 0), Vector3(70, 1, 70), palette.grass, true)
    for p in [
        Vector3(-20,0,18), Vector3(22,0,-15), Vector3(-25,0,-20),
        Vector3(25,0,20), Vector3(0,0,-34)
    ]:
        _sphere("Hill", p + Vector3(0,-1.2,0), 8.0, palette.grass2, Vector3(1.8,0.55,1.4))
    _sphere("VillageMound", Vector3(0,-1.0,-12), 12.0, palette.grass_dark, Vector3(1.2,0.12,0.85))

func _build_path() -> void:
    for i in range(-10, 12):
        var x := sin(float(i) * 0.42) * 1.3
        var width := 0.82 if i % 2 == 0 else 0.68
        _cylinder(
            "PathStone",
            Vector3(x,0.02,float(i)*1.55),
            width,
            0.12,
            palette.path_light if i % 3 == 0 else palette.path
        )

func _build_village() -> void:
    _cottage(Vector3(-7,0,-5), palette.pink)
    _cottage(Vector3(7,0,-8), palette.mint)
    _cottage(Vector3(-10,0,-15), palette.lavender)
    _cottage(Vector3(10,0,-18), palette.cream)

    _cylinder("FountainBase", Vector3(0,0.25,-10), 2.2, 0.5, palette.stone, true)
    _cylinder("FountainStem", Vector3(0,1.0,-10), 0.35, 1.5, palette.cream)
    _sphere("FountainBubble", Vector3(0,2.0,-10), 0.7, Color("#72B7C9"))
    _mushroom(Vector3(-4.2,0,-11.5), 1.15, palette.mushroom_red)
    _mushroom(Vector3(4.1,0,-12.0), 0.85, palette.mushroom_orange)

func _cottage(origin: Vector3, accent: Color) -> void:
    _box("Cottage", origin + Vector3(0,1.5,0), Vector3(4.4,3.0,3.6), palette.cream, true)
    _box("CottageTrim", origin + Vector3(0,0.38,1.86), Vector3(4.55,0.35,0.16), palette.wood_light)
    var roof := _box("Roof", origin + Vector3(0,3.35,0), Vector3(5.0,0.8,4.2), accent)
    roof.rotation_degrees.z = 7.0
    _box("Door", origin + Vector3(0,1.1,1.83), Vector3(1.1,2.0,0.18), palette.wood)
    _box("Window", origin + Vector3(-1.25,1.7,1.84), Vector3(0.8,0.8,0.16), Color("#78B9C7"))
    _box("Window", origin + Vector3(1.25,1.7,1.84), Vector3(0.8,0.8,0.16), Color("#78B9C7"))
    _cylinder("Chimney", origin + Vector3(1.35,4.1,-0.6), 0.35, 1.8, palette.wood)

func _build_forest() -> void:
    var points = [
        Vector3(-16,0,7), Vector3(-20,0,1), Vector3(-18,0,-9),
        Vector3(16,0,5), Vector3(20,0,-3), Vector3(18,0,-13),
        Vector3(-15,0,-25), Vector3(15,0,-27), Vector3(25,0,12),
        Vector3(-27,0,13), Vector3(-27,0,-4), Vector3(27,0,-7),
        Vector3(-23,0,25), Vector3(20,0,27), Vector3(6,0,25),
        Vector3(-7,0,27)
    ]
    for i in points.size():
        _tree(points[i], i % 2 == 0)

func _tree(origin: Vector3, alternate: bool) -> void:
    _cylinder("TreeTrunk", origin + Vector3(0,1.5,0), 0.42, 3.0, palette.wood, true)
    var leaf_color: Color = palette.leaf2 if alternate else palette.leaf
    _sphere("TreeCrown", origin + Vector3(0,4.1,0), 2.2, leaf_color, Vector3(1.0,1.15,1.0))
    _sphere("TreeCrown", origin + Vector3(1.0,3.8,0.4), 1.5, leaf_color)
    _sphere("TreeCrown", origin + Vector3(-1.0,3.9,-0.3), 1.55, leaf_color)

func _mushroom(origin: Vector3, scale_factor: float, cap_color: Color) -> void:
    var stem_height := 2.3 * scale_factor
    _cylinder(
        "MushroomStem",
        origin + Vector3(0, stem_height * 0.5, 0),
        0.48 * scale_factor,
        stem_height,
        palette.cream_light,
        true
    )
    _sphere(
        "MushroomCap",
        origin + Vector3(0, stem_height + 0.28 * scale_factor, 0),
        1.45 * scale_factor,
        cap_color,
        Vector3(1.25, 0.48, 1.25)
    )
    for offset in [
        Vector3(-0.58,0.18,0.18),
        Vector3(0.45,0.22,-0.32),
        Vector3(0.1,0.3,0.52),
    ]:
        _sphere(
            "MushroomSpot",
            origin + Vector3(0, stem_height + 0.66 * scale_factor, 0)
                + offset * scale_factor,
            0.2 * scale_factor,
            palette.mushroom_spot,
            Vector3(1.0,0.35,1.0)
        )

func _fence_segment(origin: Vector3, length: float, yaw_degrees: float) -> void:
    var root := Node3D.new()
    root.position = origin
    root.rotation_degrees.y = yaw_degrees
    add_child(root)

    for x in [-length * 0.5, length * 0.5]:
        var post := _cylinder(
            "FencePost",
            Vector3.ZERO,
            0.18,
            1.55,
            palette.wood,
            false
        )
        remove_child(post)
        root.add_child(post)
        post.position = Vector3(x,0.78,0)

    for y in [0.62, 1.2]:
        var rail := _box(
            "FenceRail",
            Vector3.ZERO,
            Vector3(length,0.18,0.18),
            palette.wood_light,
            false
        )
        remove_child(rail)
        root.add_child(rail)
        rail.position = Vector3(0,y,0)

func _build_storybook_dressing() -> void:
    _mushroom(Vector3(-13,0,8), 1.55, palette.mushroom_red)
    _mushroom(Vector3(13,0,7), 1.3, palette.mushroom_orange)
    _mushroom(Vector3(-22,0,-14), 1.7, palette.mushroom_red)
    _mushroom(Vector3(22,0,-20), 1.45, palette.mushroom_orange)

    _fence_segment(Vector3(-8,0,-1.5), 7.0, 8.0)
    _fence_segment(Vector3(8,0,-2.0), 7.0, -6.0)
    _fence_segment(Vector3(-12,0,-20), 6.0, -10.0)
    _fence_segment(Vector3(12,0,-23), 6.0, 12.0)

    for p in [
        Vector3(-5,0.22,-4), Vector3(5,0.22,-5),
        Vector3(-6,0.22,-16), Vector3(6,0.22,-17),
        Vector3(-2.5,0.22,-23), Vector3(3.2,0.22,-25),
    ]:
        _sphere("FlowerPatch", p, 0.42, palette.pink, Vector3(1.8,0.35,1.4))
        _sphere("FlowerLeaf", p + Vector3(0.5,0,0.2), 0.28, palette.leaf2, Vector3(1.5,0.25,1.0))

    var welcome := Label3D.new()
    welcome.text = "NEWBIE VILLAGE"
    welcome.font_size = 34
    welcome.modulate = Color("#F4DFC1")
    welcome.outline_size = 8
    welcome.outline_modulate = Color("#56372E")
    welcome.position = Vector3(0,3.0,5.5)
    welcome.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(welcome)

func _build_locked_gate() -> void:
    var z := -31.0
    _cylinder("GatePostL", Vector3(-3.2,2.2,z), 0.5, 4.4, palette.wood, true)
    _cylinder("GatePostR", Vector3(3.2,2.2,z), 0.5, 4.4, palette.wood, true)
    _box("GateBeam", Vector3(0,4.1,z), Vector3(7.2,0.65,0.8), palette.pink, true)
    _box("LockedBarrier", Vector3(0,1.5,z), Vector3(5.5,3.0,0.45), Color("#D9B8E8"), true)

    var label := Label3D.new()
    label.text = "🔒 NEW WORLD\nComing next"
    label.font_size = 42
    label.modulate = Color("#FFF7E7")
    label.outline_size = 8
    label.outline_modulate = Color(0.2,0.12,0.18,0.9)
    label.position = Vector3(0,5.2,z + 0.1)
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(label)

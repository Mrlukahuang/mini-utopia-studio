extends Node3D

var palette = {
    "grass": Color("#8ECF82"),
    "grass2": Color("#A8DA8C"),
    "path": Color("#E8C994"),
    "wood": Color("#9D6549"),
    "cream": Color("#FFE7C8"),
    "pink": Color("#F3A7B9"),
    "mint": Color("#86CDBA"),
    "lavender": Color("#B6A0DC"),
    "leaf": Color("#6FB36C"),
    "leaf2": Color("#94C66C"),
    "stone": Color("#C9BDB2"),
}

func _ready() -> void:
    _setup_environment()
    _build_ground()
    _build_path()
    _build_village()
    _build_forest()
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
    env.background_color = Color("#A8D8E8")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#FFF1DE")
    env.ambient_light_energy = 0.72
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.fog_enabled = true
    env.fog_light_color = Color("#D9EEF0")
    env.fog_light_energy = 0.65
    env.fog_density = 0.008
    world_env.environment = env
    add_child(world_env)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-52, -35, 0)
    sun.light_color = Color("#FFF1D2")
    sun.light_energy = 1.35
    sun.shadow_enabled = true
    add_child(sun)

func _build_ground() -> void:
    _box("VillageGround", Vector3(0, -0.55, 0), Vector3(70, 1, 70), palette.grass, true)
    for p in [Vector3(-20,0,18), Vector3(22,0,-15), Vector3(-25,0,-20)]:
        _sphere("Hill", p + Vector3(0,-1.2,0), 8.0, palette.grass2, Vector3(1.8,0.55,1.4))

func _build_path() -> void:
    for i in range(-10, 11):
        var x := sin(float(i) * 0.42) * 1.3
        _cylinder("PathStone", Vector3(x,0.02,float(i)*1.55), 0.75, 0.12, palette.path)

func _build_village() -> void:
    _cottage(Vector3(-7,0,-5), palette.pink)
    _cottage(Vector3(7,0,-8), palette.mint)
    _cottage(Vector3(-10,0,-15), palette.lavender)
    _cottage(Vector3(10,0,-18), palette.cream)

    _cylinder("FountainBase", Vector3(0,0.25,-10), 2.2, 0.5, palette.stone, true)
    _cylinder("FountainStem", Vector3(0,1.0,-10), 0.35, 1.5, palette.cream)
    _sphere("FountainBubble", Vector3(0,2.0,-10), 0.7, Color("#9EDBEC"))

func _cottage(origin: Vector3, accent: Color) -> void:
    _box("Cottage", origin + Vector3(0,1.5,0), Vector3(4.4,3.0,3.6), palette.cream, true)
    var roof := _box("Roof", origin + Vector3(0,3.35,0), Vector3(5.0,0.8,4.2), accent)
    roof.rotation_degrees.z = 7.0
    _box("Door", origin + Vector3(0,1.1,1.83), Vector3(1.1,2.0,0.18), palette.wood)
    _box("Window", origin + Vector3(-1.25,1.7,1.84), Vector3(0.8,0.8,0.16), Color("#9EDBEC"))
    _box("Window", origin + Vector3(1.25,1.7,1.84), Vector3(0.8,0.8,0.16), Color("#9EDBEC"))
    _cylinder("Chimney", origin + Vector3(1.35,4.1,-0.6), 0.35, 1.8, palette.wood)

func _build_forest() -> void:
    var points = [
        Vector3(-16,0,7), Vector3(-20,0,1), Vector3(-18,0,-9),
        Vector3(16,0,5), Vector3(20,0,-3), Vector3(18,0,-13),
        Vector3(-15,0,-25), Vector3(15,0,-27), Vector3(25,0,12),
        Vector3(-27,0,13)
    ]
    for i in points.size():
        _tree(points[i], i % 2 == 0)

func _tree(origin: Vector3, alternate: bool) -> void:
    _cylinder("TreeTrunk", origin + Vector3(0,1.5,0), 0.42, 3.0, palette.wood, true)
    var leaf_color: Color = palette.leaf2 if alternate else palette.leaf
    _sphere("TreeCrown", origin + Vector3(0,4.1,0), 2.2, leaf_color, Vector3(1.0,1.15,1.0))
    _sphere("TreeCrown", origin + Vector3(1.0,3.8,0.4), 1.5, leaf_color)
    _sphere("TreeCrown", origin + Vector3(-1.0,3.9,-0.3), 1.55, leaf_color)

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

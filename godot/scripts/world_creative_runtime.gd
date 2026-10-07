class_name MiniUtopiaWorldCreativeRuntime
extends Node3D

var layout: Dictionary = {}


func configure(payload: Dictionary) -> void:
    layout = payload.duplicate(true)
    _clear()
    var raw = layout.get("decorations", [])
    if typeof(raw) != TYPE_ARRAY:
        return
    for item in raw:
        if typeof(item) == TYPE_DICTIONARY:
            _spawn(item)
    print(
        "WORLD-02 Creative layout: ",
        raw.size(),
        " decorations"
    )


func _clear() -> void:
    for child in get_children():
        child.queue_free()


func _spawn(item: Dictionary) -> void:
    var root := Node3D.new()
    root.name = "Creative_" + _text(item.get("decoration_id", "Decoration"))
    add_child(root)

    var raw_position = item.get("position", [0.0, 0.0, 0.0])
    if typeof(raw_position) == TYPE_ARRAY and raw_position.size() >= 3:
        root.position = Vector3(
            float(raw_position[0]),
            float(raw_position[1]),
            float(raw_position[2])
        )
    root.rotation_degrees.y = float(item.get("rotation_y", 0.0))
    root.scale = Vector3.ONE * float(item.get("scale", 1.0))

    var prop_type := _text(item.get("prop_type", "star_lamp"))
    match prop_type:
        "flower_pot":
            _flower_pot(root)
        "toy_bench":
            _toy_bench(root)
        "mini_flag":
            _mini_flag(root)
        "cloud_cushion":
            _cloud_cushion(root)
        _:
            _star_lamp(root)


func _star_lamp(root: Node3D) -> void:
    _box(root, "Pole", Vector3(0, .75, 0), Vector3(.18,1.5,.18), Color("#FFF4D7"))
    _sphere(root, "Star", Vector3(0,1.7,0), Vector3(.45,.45,.45), Color("#FFD968"))


func _flower_pot(root: Node3D) -> void:
    _box(root, "Pot", Vector3(0,.25,0), Vector3(.58,.50,.58), Color("#CFA77E"))
    _sphere(root, "Flower", Vector3(0,.72,0), Vector3(.38,.30,.38), Color("#F59BC2"))


func _toy_bench(root: Node3D) -> void:
    _box(root, "Seat", Vector3(0,.58,0), Vector3(1.5,.18,.48), Color("#CFA77E"))
    _box(root, "Back", Vector3(0,.90,-.18), Vector3(1.5,.62,.16), Color("#CFA77E"))
    _box(root, "LegL", Vector3(-.56,.29,0), Vector3(.14,.58,.14), Color("#8B6A55"))
    _box(root, "LegR", Vector3(.56,.29,0), Vector3(.14,.58,.14), Color("#8B6A55"))


func _mini_flag(root: Node3D) -> void:
    _box(root, "Pole", Vector3(0,.8,0), Vector3(.10,1.6,.10), Color("#FFF4D7"))
    _box(root, "Flag", Vector3(.36,1.35,0), Vector3(.72,.42,.08), Color("#78D66C"))


func _cloud_cushion(root: Node3D) -> void:
    _sphere(root, "Cushion", Vector3(0,.28,0), Vector3(.60,.28,.50), Color("#EAF4FF"))


func _box(parent: Node3D, node_name: String, pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = pos
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)
    return node


func _sphere(parent: Node3D, node_name: String, pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = pos
    node.scale = size
    var mesh := SphereMesh.new()
    mesh.radius = .5
    mesh.height = 1.0
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)
    return node


func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = .82
    return material


static func _text(value: Variant) -> String:
    if value == null:
        return ""
    return str(value)

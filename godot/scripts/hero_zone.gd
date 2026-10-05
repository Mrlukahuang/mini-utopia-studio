extends Node3D

const HeroLoader = preload("res://scripts/hero_runtime_loader.gd")

var palette := {
    "cloud": Color("#DCE4E1"),
    "cloud_shadow": Color("#B8C9C5"),
    "grass": Color("#6F9B78"),
    "stone": Color("#AFA6A0"),
    "accent": Color("#C97A72"),
    "cream": Color("#F0D6B3"),
}

func _ready() -> void:
    _build_landing()
    _build_clouds()
    _build_sign()
    var loader := HeroLoader.new()
    loader.name = "HeroRuntimeLoader"
    add_child(loader)

func _mat(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.9
    return material

func _box(name: String, pos: Vector3, size: Vector3, color: Color, collision := false) -> void:
    var mesh := MeshInstance3D.new()
    var box := BoxMesh.new()
    box.size = size
    mesh.mesh = box
    mesh.material_override = _mat(color)
    mesh.name = name
    mesh.position = pos
    add_child(mesh)

    if collision:
        var body := StaticBody3D.new()
        var shape_node := CollisionShape3D.new()
        var shape := BoxShape3D.new()
        shape.size = size
        shape_node.shape = shape
        body.position = pos
        body.add_child(shape_node)
        add_child(body)

func _sphere(pos: Vector3, radius: float, scale_value: Vector3, color: Color) -> void:
    var node := MeshInstance3D.new()
    var mesh := SphereMesh.new()
    mesh.radius = radius
    mesh.height = radius * 2.0
    node.mesh = mesh
    node.position = pos
    node.scale = scale_value
    node.material_override = _mat(color)
    add_child(node)

func _build_landing() -> void:
    _box("Zone01Ground", Vector3(0,-0.55,0), Vector3(42,1,38), palette.grass, true)
    _box("LandingPath", Vector3(0,0.02,9), Vector3(6,0.14,16), palette.cream, false)
    _box("HeroLookout", Vector3(0,0.22,-5), Vector3(16,0.45,9), palette.stone, true)

func _build_clouds() -> void:
    for p in [
        Vector3(-12,1.0,-12), Vector3(12,0.8,-13), Vector3(-16,1.4,4),
        Vector3(16,1.2,5), Vector3(-8,1.8,-18), Vector3(9,1.6,-19)
    ]:
        _sphere(p, 2.3, Vector3(1.8,0.55,1.2), palette.cloud)
        _sphere(p + Vector3(1.8,-0.3,0.6), 1.6, Vector3(1.4,0.45,1.0), palette.cloud_shadow)

func _build_sign() -> void:
    var label := Label3D.new()
    label.text = "ZONE 01 · CLOUD WHALE DISTRICT"
    label.font_size = 34
    label.modulate = palette.cream
    label.outline_size = 8
    label.outline_modulate = Color("#39444B")
    label.position = Vector3(0,3.0,13.0)
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(label)

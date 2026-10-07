class_name MiniUtopiaBabyFollowRuntime
extends Node3D

@export var follow_distance := 0.90
@export var side_offset := 1.05
@export var follow_speed := 6.5
@export var recovery_distance := 7.0

var target: Node3D
var baby_payload: Dictionary = {}
var _visual: Node3D
var _elapsed := 0.0


func configure(
    target_node: Node3D,
    payload: Dictionary
) -> void:
    target = target_node
    baby_payload = payload.duplicate(true)
    name = "ActiveBaby_" + String(
        baby_payload.get("baby_id", "UNKNOWN")
    )
    _build_visual()


func _process(delta: float) -> void:
    if target == null or not is_instance_valid(target):
        return

    _elapsed += delta
    var forward := target.global_basis.z.normalized()
    var right := target.global_basis.x.normalized()
    var desired := (
        target.global_position
        - forward * follow_distance
        - right * side_offset
        + Vector3(0.0, 0.12, 0.0)
    )

    if global_position.distance_to(desired) > recovery_distance:
        global_position = desired
    else:
        var weight := 1.0 - exp(-follow_speed * delta)
        global_position = global_position.lerp(desired, weight)

    global_rotation.y = lerp_angle(
        global_rotation.y,
        target.global_rotation.y,
        minf(1.0, delta * 7.0)
    )

    if _visual != null:
        _visual.position.y = (
            0.42
            + sin(_elapsed * 3.2) * 0.055
        )
        _visual.rotation.z = sin(_elapsed * 2.1) * 0.035


func _build_visual() -> void:
    if _visual != null:
        _visual.queue_free()

    _visual = Node3D.new()
    _visual.name = "Visual"
    _visual.scale = Vector3.ONE * 1.22
    add_child(_visual)

    var species := String(baby_payload.get("species_id", "star_baby"))
    var primary := Color("#FFD968")
    var accent := Color("#FFF4BF")

    match species:
        "cloud_baby":
            primary = Color("#F7FBFF")
            accent = Color("#DDEEFF")
        "sheep_baby":
            primary = Color("#F6F1E8")
            accent = Color("#CFA77E")
        "robot_baby":
            primary = Color("#B9DDF4")
            accent = Color("#8EA3B8")
        "forest_baby":
            primary = Color("#B9E7D0")
            accent = Color("#7BAF7A")

    _add_sphere(
        _visual,
        "BabyBody",
        Vector3(0.0, 0.0, 0.0),
        Vector3(0.34, 0.30, 0.32),
        primary
    )
    _add_sphere(
        _visual,
        "BabyHead",
        Vector3(0.0, 0.38, 0.02),
        Vector3(0.29, 0.28, 0.28),
        accent
    )
    _add_sphere(
        _visual,
        "EyeL",
        Vector3(-0.10, 0.40, 0.27),
        Vector3(0.05, 0.065, 0.04),
        Color("#4C4058")
    )
    _add_sphere(
        _visual,
        "EyeR",
        Vector3(0.10, 0.40, 0.27),
        Vector3(0.05, 0.065, 0.04),
        Color("#4C4058")
    )

    var name_label := Label3D.new()
    name_label.name = "BabyName"
    name_label.position = Vector3(0.0, 0.92, 0.0)
    name_label.text = "🐣 " + String(
        baby_payload.get("display_name", "Baby")
    )
    name_label.font_size = 28
    name_label.outline_size = 7
    name_label.modulate = Color("#FFF7D7")
    name_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    _visual.add_child(name_label)

    match species:
        "star_baby":
            _add_box(
                _visual,
                "StarCharm",
                Vector3(-0.34, 0.50, 0.02),
                Vector3(0.16, 0.16, 0.08),
                Color("#FFD968")
            )
        "cloud_baby":
            for x in [-0.20, 0.0, 0.20]:
                _add_sphere(
                    _visual,
                    "CloudPuff",
                    Vector3(x, 0.64, -0.02),
                    Vector3(0.16, 0.13, 0.14),
                    accent
                )
        "sheep_baby":
            _add_sphere(
                _visual,
                "EarL",
                Vector3(-0.28, 0.43, 0.0),
                Vector3(0.13, 0.10, 0.11),
                primary
            )
            _add_sphere(
                _visual,
                "EarR",
                Vector3(0.28, 0.43, 0.0),
                Vector3(0.13, 0.10, 0.11),
                primary
            )
        "robot_baby":
            _add_box(
                _visual,
                "Antenna",
                Vector3(0.0, 0.72, 0.0),
                Vector3(0.045, 0.20, 0.045),
                Color("#7D8C9B")
            )
            _add_sphere(
                _visual,
                "AntennaTip",
                Vector3(0.0, 0.84, 0.0),
                Vector3(0.06, 0.06, 0.06),
                primary
            )
        "forest_baby":
            var leaf := _add_box(
                _visual,
                "Leaf",
                Vector3(0.08, 0.72, 0.0),
                Vector3(0.11, 0.27, 0.07),
                accent
            )
            leaf.rotation_degrees.z = -28.0


func _add_box(
    parent: Node3D,
    node_name: String,
    local_position: Vector3,
    size: Vector3,
    color: Color
) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = local_position
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)
    return node


func _add_sphere(
    parent: Node3D,
    node_name: String,
    local_position: Vector3,
    scale_value: Vector3,
    color: Color
) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = node_name
    node.position = local_position
    node.scale = scale_value
    var mesh := SphereMesh.new()
    mesh.radius = 0.5
    mesh.height = 1.0
    node.mesh = mesh
    node.material_override = _material(color)
    parent.add_child(node)
    return node


func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.82
    return material

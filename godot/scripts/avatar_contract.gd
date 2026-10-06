class_name MiniUtopiaAvatarContract
extends RefCounted

const RIG_FAMILY := "humanoid_kaykit_v1"

const BODY_SLIM := "slim"
const BODY_STANDARD := "standard"
const BODY_CHUBBY := "chubby"
const BODY_TYPES := [BODY_SLIM, BODY_STANDARD, BODY_CHUBBY]

const SOCKET_WEAPON_R := "Socket_Weapon_R"
const SOCKET_WEAPON_L := "Socket_Weapon_L"
const SOCKET_BACKPACK := "Socket_Backpack"
const SOCKET_WINGS := "Socket_Wings"
const SOCKET_ACCESSORY := "Socket_Accessory"

const SOCKET_NAMES := [
    SOCKET_WEAPON_R,
    SOCKET_WEAPON_L,
    SOCKET_BACKPACK,
    SOCKET_WINGS,
    SOCKET_ACCESSORY,
]

const ANIMATION_IDLE := "Idle"
const ANIMATION_WALK := "Walk"
const ANIMATION_RUN := "Run"
const BASE_ANIMATIONS := [
    ANIMATION_IDLE,
    ANIMATION_WALK,
    ANIMATION_RUN,
]


static func body_width_scale(body_type: String) -> float:
    match body_type:
        BODY_SLIM:
            return 0.84
        BODY_CHUBBY:
            return 1.16
        _:
            return 1.0


static func head_width_scale(_body_type: String) -> float:
    # Q-style head silhouette stays stable across body types.
    return 1.0


static func body_label(body_type: String) -> String:
    match body_type:
        BODY_SLIM:
            return "Slim"
        BODY_CHUBBY:
            return "Chubby"
        _:
            return "Standard"


static func ensure_socket_nodes(parent: Node3D) -> Dictionary:
    var sockets := {}
    for socket_name in SOCKET_NAMES:
        var node := parent.get_node_or_null(NodePath(socket_name))
        if node == null:
            node = Node3D.new()
            node.name = socket_name
            parent.add_child(node)
        sockets[socket_name] = node
    return sockets


static func apply_default_socket_positions(
    sockets: Node3D,
    body_type: String
) -> void:
    var width_scale := body_width_scale(body_type)

    var weapon_r := sockets.get_node_or_null(SOCKET_WEAPON_R) as Node3D
    if weapon_r != null:
        weapon_r.position = Vector3(0.67 * width_scale, 0.90, 0.0)

    var weapon_l := sockets.get_node_or_null(SOCKET_WEAPON_L) as Node3D
    if weapon_l != null:
        weapon_l.position = Vector3(-0.67 * width_scale, 0.90, 0.0)

    var backpack := sockets.get_node_or_null(SOCKET_BACKPACK) as Node3D
    if backpack != null:
        backpack.position = Vector3(0.0, 1.12, -0.32)

    var wings := sockets.get_node_or_null(SOCKET_WINGS) as Node3D
    if wings != null:
        wings.position = Vector3(0.0, 1.34, -0.33)

    var accessory := sockets.get_node_or_null(SOCKET_ACCESSORY) as Node3D
    if accessory != null:
        accessory.position = Vector3(0.0, 1.75, 0.0)

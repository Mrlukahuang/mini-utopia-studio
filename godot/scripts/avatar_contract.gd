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

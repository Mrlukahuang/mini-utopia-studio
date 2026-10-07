class_name MiniUtopiaWorldGameplayRuntime
extends Node

var player: Node3D
var layer: Dictionary = {}
var modes: Array[String] = []
var targets_by_id: Dictionary = {}


func configure(
    player_node: Node3D,
    gameplay_payload: Dictionary
) -> void:
    player = player_node
    layer = gameplay_payload.duplicate(true)
    modes.clear()
    targets_by_id.clear()

    var raw_modes = layer.get("modes", [])
    if typeof(raw_modes) == TYPE_ARRAY:
        for raw_mode in raw_modes:
            var mode := _string_or_empty(raw_mode)
            if not mode.is_empty() and mode not in modes:
                modes.append(mode)

    var raw_targets = layer.get("targets", [])
    if typeof(raw_targets) == TYPE_ARRAY:
        for raw_target in raw_targets:
            if typeof(raw_target) != TYPE_DICTIONARY:
                continue
            var target_id := _string_or_empty(
                raw_target.get("target_id", "")
            )
            if not target_id.is_empty():
                targets_by_id[target_id] = raw_target.duplicate(true)

    if player != null:
        player.set_meta(
            "mini_utopia_world_gameplay_id",
            _string_or_empty(layer.get("world_asset_id", ""))
        )
        player.set_meta(
            "mini_utopia_world_modes",
            modes.duplicate()
        )

    print(
        "WORLD-01 gameplay layer: ",
        layer.get("world_asset_id", "WORLD"),
        " · modes=",
        ", ".join(modes),
        " · targets=",
        targets_by_id.size()
    )


func supports_mode(mode: String) -> bool:
    return mode in modes


func target_by_id(target_id: String) -> Dictionary:
    var target = targets_by_id.get(target_id, {})
    return (
        target.duplicate(true)
        if typeof(target) == TYPE_DICTIONARY
        else {}
    )


func quest_ids() -> Array:
    var raw = layer.get("quest_ids", [])
    return raw.duplicate(true) if typeof(raw) == TYPE_ARRAY else []


func story_ids() -> Array:
    var raw = layer.get("story_ids", [])
    return raw.duplicate(true) if typeof(raw) == TYPE_ARRAY else []


static func _string_or_empty(value: Variant) -> String:
    if value == null:
        return ""
    return str(value)

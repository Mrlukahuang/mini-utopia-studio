class_name MiniUtopiaQuestRuntime
extends Node

signal objective_changed(objective_id: String)
signal quest_completed(quest_id: String)

@export var interact_distance := 2.8

var player: Node3D
var quest: Dictionary = {}
var objectives: Array = []
var current_index := 0
var objective_counts: Dictionary = {}
var completed := false

var _hud_label: Label
var _marker: Node3D


func configure(
    player_node: Node3D,
    quest_payload: Dictionary
) -> void:
    player = player_node
    quest = quest_payload.duplicate(true)
    objectives = quest.get("objectives", []).duplicate(true)
    current_index = 0
    objective_counts.clear()
    completed = objectives.is_empty()

    _build_hud()
    _refresh_objective()

    # The PlaySession already selected the Quest's World, so ARRIVE can be
    # represented by the generic go_to_location event at runtime start.
    if not completed:
        var first := current_objective()
        if String(first.get("objective_type", "")) == "go_to_location":
            record_event(
                "go_to_location",
                _string_or_empty(first.get("target_id", "")),
                1
            )


func current_objective() -> Dictionary:
    if completed or current_index >= objectives.size():
        return {}
    var raw = objectives[current_index]
    return raw if typeof(raw) == TYPE_DICTIONARY else {}


func current_objective_id() -> String:
    return String(current_objective().get("objective_id", ""))


func is_complete() -> bool:
    return completed


func record_event(
    event_type: String,
    target_id: String = "",
    amount: int = 1
) -> bool:
    if completed or amount <= 0:
        return false

    var objective := current_objective()
    if objective.is_empty():
        return false

    var objective_type := String(
        objective.get("objective_type", "")
    )
    if objective_type != event_type:
        return false

    var expected_target := _string_or_empty(
        objective.get("target_id", "")
    )
    if (
        not expected_target.is_empty()
        and expected_target != target_id
    ):
        return false

    var objective_id := String(
        objective.get("objective_id", "")
    )
    var required := maxi(
        1,
        int(objective.get("target_count", 1))
    )
    var progress := int(
        objective_counts.get(objective_id, 0)
    ) + amount
    objective_counts[objective_id] = progress

    if progress < required:
        _refresh_hud()
        return true

    current_index += 1
    if current_index >= objectives.size():
        completed = true
        _write_completion_receipt()
        _refresh_objective()
        quest_completed.emit(
            _string_or_empty(quest.get("quest_id", "QUEST"))
        )
        return true

    _refresh_objective()
    objective_changed.emit(current_objective_id())
    return true


func try_interact() -> bool:
    if completed or player == null:
        return false

    var objective := current_objective()
    var objective_type := String(
        objective.get("objective_type", "")
    )
    if objective_type not in [
        "interact",
        "return_to_target",
        "open_portal",
    ]:
        return false

    var metadata = objective.get("metadata", {})
    if typeof(metadata) != TYPE_DICTIONARY:
        return false
    var raw_position = metadata.get("position", [])
    if typeof(raw_position) != TYPE_ARRAY or raw_position.size() < 3:
        return false

    var target_position := Vector3(
        float(raw_position[0]),
        float(raw_position[1]),
        float(raw_position[2])
    )
    if player.global_position.distance_to(target_position) > interact_distance:
        return false

    return record_event(
        objective_type,
        _string_or_empty(objective.get("target_id", "")),
        1
    )


func _refresh_objective() -> void:
    _clear_marker()
    _refresh_hud()

    if completed:
        if player != null and player.has_method("show_reward_feedback"):
            player.show_reward_feedback(
                "🏆 Quest Complete! / 任务完成 · "
                + "Rewards → My Stuff"
            )
        return

    var objective := current_objective()
    var objective_type := String(
        objective.get("objective_type", "")
    )
    if objective_type in [
        "interact",
        "return_to_target",
        "open_portal",
    ]:
        _spawn_marker.call_deferred(
            String(objective.get("objective_id", "")),
            objective.duplicate(true)
        )


func _build_hud() -> void:
    if _hud_label != null:
        return

    var layer := CanvasLayer.new()
    layer.name = "QuestHUDLayer"
    layer.layer = 18
    add_child(layer)

    _hud_label = Label.new()
    _hud_label.name = "QuestHUD"
    _hud_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
    _hud_label.position = Vector2(-500.0, 24.0)
    _hud_label.size = Vector2(470.0, 104.0)
    _hud_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
    _hud_label.vertical_alignment = VERTICAL_ALIGNMENT_TOP
    _hud_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    _hud_label.add_theme_font_size_override("font_size", 20)
    _hud_label.add_theme_color_override(
        "font_color",
        Color("#FFF7D7")
    )
    _hud_label.add_theme_color_override(
        "font_shadow_color",
        Color(0.04, 0.04, 0.08, 0.94)
    )
    _hud_label.add_theme_constant_override("shadow_offset_x", 3)
    _hud_label.add_theme_constant_override("shadow_offset_y", 3)
    layer.add_child(_hud_label)


func _refresh_hud() -> void:
    if _hud_label == null:
        return

    var title := String(quest.get("title", "Quest"))
    if completed:
        _hud_label.text = "🏆 " + title + "\n✅ Quest Complete / 任务完成"
        return

    var objective := current_objective()
    var label := String(objective.get("label", "Continue the adventure"))
    var objective_id := String(objective.get("objective_id", ""))
    var progress := int(objective_counts.get(objective_id, 0))
    var required := maxi(1, int(objective.get("target_count", 1)))
    _hud_label.text = (
        "📜 "
        + title
        + "\n"
        + str(current_index + 1)
        + "/"
        + str(objectives.size())
        + " · "
        + label
        + (
            "  "
            + str(progress)
            + "/"
            + str(required)
            if required > 1
            else ""
        )
    )


func _spawn_marker(
    objective_id: String,
    objective: Dictionary
) -> void:
    if completed or objective_id != current_objective_id():
        return
    if player == null or not is_instance_valid(player):
        return

    var metadata = objective.get("metadata", {})
    if typeof(metadata) != TYPE_DICTIONARY:
        return
    var raw_position = metadata.get("position", [])
    if typeof(raw_position) != TYPE_ARRAY or raw_position.size() < 3:
        return

    var world_parent := player.get_parent()
    if world_parent == null:
        return

    _marker = Node3D.new()
    _marker.name = "QuestMarker_" + objective_id
    world_parent.add_child(_marker)
    _marker.global_position = Vector3(
        float(raw_position[0]),
        float(raw_position[1]),
        float(raw_position[2])
    )

    var glow := MeshInstance3D.new()
    glow.name = "Glow"
    var glow_mesh := SphereMesh.new()
    glow_mesh.radius = 0.28
    glow_mesh.height = 0.56
    glow.mesh = glow_mesh
    var material := StandardMaterial3D.new()
    material.albedo_color = Color("#FFD968")
    material.emission_enabled = true
    material.emission = Color("#FFD968")
    material.emission_energy_multiplier = 1.8
    glow.material_override = material
    _marker.add_child(glow)

    var label := Label3D.new()
    label.name = "Prompt"
    label.position = Vector3(0.0, 0.72, 0.0)
    var prompt := _string_or_empty(metadata.get("prompt", ""))
    if prompt.is_empty():
        prompt = (
            "✨ "
            + _string_or_empty(objective.get("label", "Interact"))
            + " · E"
        )
    label.text = prompt
    label.font_size = 34
    label.outline_size = 8
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    _marker.add_child(label)


func _write_completion_receipt() -> void:
    var quest_id := _string_or_empty(
        quest.get("quest_id", "QUEST")
    )
    var session_id := "NO_SESSION"
    var character_asset_id := ""
    if player != null:
        session_id = _string_or_empty(
            player.get_meta(
                "mini_utopia_session_id",
                "NO_SESSION"
            )
        )
        character_asset_id = _string_or_empty(
            player.get_meta(
                "mini_utopia_character_asset_id",
                ""
            )
        )

    var completion_id := (
        "QUEST_DONE_"
        + session_id
        + "_"
        + quest_id
    )
    MiniUtopiaQuestRewardWriter.write_completion(
        {
            "completion_id": completion_id,
            "quest_id": quest_id,
            "session_id": session_id,
            "character_asset_id": character_asset_id,
            "created_at": str(Time.get_unix_time_from_system()),
        }
    )


func _string_or_empty(value: Variant) -> String:
    if value == null:
        return ""
    return str(value)


func _clear_marker() -> void:
    if _marker != null and is_instance_valid(_marker):
        _marker.queue_free()
    _marker = null

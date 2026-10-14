class_name MiniUtopiaFamilySceneState
extends Node

## Per-run, non-persistent selection between Godot scenes. Stores only the
## canonical Character contract returned by the server (NOT family auth).
## Scene changes reuse the same identity but no private data is written to disk.

var active_character: Dictionary = {}
var active_equipment: Dictionary = {}


func select_character(contract: Dictionary) -> bool:
    var session := MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(contract)
    if session.is_empty():
        return false
    active_character = contract.duplicate(true)
    # Never carry one child's clothes into another child's newly selected Hero.
    active_equipment.clear()
    return true


func select_equipment(runtime: Dictionary) -> bool:
    var character_id := String(active_character.get("character_id", ""))
    if character_id.is_empty() or String(
        runtime.get("character_asset_id", "")
    ) != character_id:
        return false
    if typeof(runtime.get("equipped", null)) != TYPE_DICTIONARY:
        return false
    if typeof(runtime.get("final_stats", null)) != TYPE_DICTIONARY:
        return false
    active_equipment = runtime.duplicate(true)
    return true


func active_play_session() -> Dictionary:
    var play := MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(
        active_character
    )
    if not play.is_empty() and not active_equipment.is_empty():
        play["equipment"] = active_equipment.duplicate(true)
    return play


func clear_selection() -> void:
    active_character.clear()
    active_equipment.clear()

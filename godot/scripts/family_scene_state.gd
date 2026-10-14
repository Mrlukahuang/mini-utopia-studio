class_name MiniUtopiaFamilySceneState
extends Node

## Per-run, non-persistent selection between Godot scenes. Stores only the
## canonical Character contract returned by the server (NOT family auth).
## Scene changes reuse the same identity but no private data is written to disk.

var active_character: Dictionary = {}


func select_character(contract: Dictionary) -> bool:
    var session := MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(contract)
    if session.is_empty():
        return false
    active_character = contract.duplicate(true)
    return true


func active_play_session() -> Dictionary:
    return MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(active_character)


func clear_selection() -> void:
    active_character.clear()

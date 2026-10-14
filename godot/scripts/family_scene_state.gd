class_name MiniUtopiaFamilySceneState
extends Node

## Per-run, non-persistent selection and HTTPS session across Godot scenes.
## Child's bearer token stays ONLY in this memory-resident autoload; never
## export it, log it, persist it or add it to URLs. Parent provisioning remains
## separate from this session transport and character-library user interface.

var active_character: Dictionary = {}
var active_equipment: Dictionary = {}
var second_cast_character: Dictionary = {}
var second_cast_equipment: Dictionary = {}
var second_cast_is_parent_guest := false
var director_shot_choices: Dictionary = {
    "action": "walk", "camera": "follow", "duration_seconds": 15,
    "caption_preset": "none"
}
var pending_character_id := ""
var opened_saved_film: Dictionary = {}
var _family_api_url := ""
var _family_token := ""
var _family_profile_id := ""


func connect_family(api_url: String, token: String, profile_id: String = "") -> bool:
    # Stage credentials in a temporary client to reuse the same HTTPS-only
    # validation as all other Godot Character requests.
    var normalized := MiniUtopiaBridgeEndpointPolicy.normalize(api_url, true)
    if normalized.is_empty():
        return false
    var probe := MiniUtopiaBridgeClient.new()
    probe.base_url = normalized
    if not probe.set_family_session(token):
        probe.clear_family_session()
        probe.free()
        return false
    probe.clear_family_session()
    probe.free()

    # A new parent/child connection must discard old selections first.
    disconnect_family()
    _family_api_url = normalized
    _family_token = token
    _family_profile_id = profile_id if profile_id in ["child_a", "child_b"] else ""
    return true


func bind_family_client(client: MiniUtopiaBridgeClient) -> bool:
    if client == null or _family_api_url.is_empty() or _family_token.is_empty():
        return false
    client.configure(_family_api_url)
    return client.set_family_session(_family_token)


func has_family_connection() -> bool:
    return not _family_api_url.is_empty() and not _family_token.is_empty()


func disconnect_family() -> void:
    clear_selection()
    pending_character_id = ""
    _family_api_url = ""
    _family_token = ""
    _family_profile_id = ""


func current_profile_id() -> String:
    return _family_profile_id


func open_character(character_id: String) -> bool:
    if not has_family_connection() or not character_id.begins_with("CHAR_"):
        return false
    if character_id.contains("/") or character_id.contains("?"):
        return false
    pending_character_id = character_id
    return true


func start_new_character() -> void:
    pending_character_id = ""


func _exit_tree() -> void:
    disconnect_family()


func select_character(contract: Dictionary) -> bool:
    var session := MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(contract)
    if session.is_empty():
        return false
    active_character = contract.duplicate(true)
    opened_saved_film.clear()
    # Never carry one child's clothes into another child's newly selected Hero.
    active_equipment.clear()
    # A new primary Hero may not keep an old or identical supporting actor.
    clear_second_cast()
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


## Called only after a second GET /characters/{id} succeeded under the
## current child's bearer token. The server, not this client, enforces owner.
func select_second_cast_character(contract: Dictionary) -> bool:
    var current := String(active_character.get("character_id", ""))
    var candidate := String(contract.get("character_id", ""))
    if (
        not has_family_connection()
        or current.is_empty()
        or candidate.is_empty()
        or current == candidate
        or MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(contract).is_empty()
    ):
        return false
    second_cast_character = contract.duplicate(true)
    second_cast_equipment.clear()
    second_cast_is_parent_guest = false
    return true


func select_second_cast_equipment(runtime: Dictionary) -> bool:
    if (
        second_cast_character.is_empty()
        or String(runtime.get("character_asset_id", "")) != String(
            second_cast_character.get("character_id", "")
        )
        or typeof(runtime.get("equipped", null)) != TYPE_DICTIONARY
        or typeof(runtime.get("final_stats", null)) != TYPE_DICTIONARY
    ):
        return false
    second_cast_equipment = runtime.duplicate(true)
    return true


func second_cast_play_session() -> Dictionary:
    if second_cast_character.is_empty() or second_cast_equipment.is_empty():
        return {}
    var result := MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(
        second_cast_character
    )
    if not result.is_empty():
        result["equipment"] = second_cast_equipment.duplicate(true)
    return result


func clear_second_cast() -> void:
    second_cast_character.clear()
    second_cast_equipment.clear()
    second_cast_is_parent_guest = false


func active_play_session() -> Dictionary:
    var play := MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(
        active_character
    )
    if not play.is_empty() and not active_equipment.is_empty():
        play["equipment"] = active_equipment.duplicate(true)
    return play


## Only after owner-scoped GET /family/films/{id}, GET /characters/{id},
## and each actor's canonical equipment have all succeeded. Never cache a
## film belonging to a different child, or temporary guest permission.
func restore_owned_film(film: Dictionary) -> bool:
    var film_id := String(film.get("film_id", ""))
    var revision := String(film.get("revision", ""))
    var draft = film.get("draft", {})
    if (
        not has_family_connection()
        or not film_id.begins_with("FILM_")
        or revision.is_empty()
        or typeof(draft) != TYPE_DICTIONARY
        or active_equipment.is_empty()
        or String(draft.get("character_id", "")) != String(
            active_character.get("character_id", "")
        )
    ):
        return false
    var raw_second = draft.get("second_character_id", null)
    var second_id := String(raw_second) if typeof(raw_second) == TYPE_STRING else ""
    if not second_id.is_empty():
        if (
            second_cast_is_parent_guest
            or second_cast_play_session().is_empty()
            or second_id != String(second_cast_character.get("character_id", ""))
        ):
            return false
    elif not second_cast_character.is_empty():
        return false
    var camera := String(draft.get("camera", ""))
    var action := String(draft.get("action", ""))
    var seconds := int(draft.get("duration_seconds", 0))
    if camera not in ["follow", "wide", "close"] or action not in [
        "walk", "run", "celebrate"
    ] or seconds not in [15, 30]:
        return false
    var caption_preset := String(draft.get("caption_preset", "none"))
    if not MiniUtopiaFamilyDirectorSession.CAPTION_PRESETS.has(caption_preset):
        return false
    director_shot_choices = {
        "camera": camera, "action": action, "duration_seconds": seconds,
        "caption_preset": caption_preset
    }
    opened_saved_film = film.duplicate(true)
    return true


func clear_selection() -> void:
    director_shot_choices = {
        "action": "walk", "camera": "follow", "duration_seconds": 15,
        "caption_preset": "none"
    }
    opened_saved_film.clear()
    active_character.clear()
    active_equipment.clear()
    clear_second_cast()

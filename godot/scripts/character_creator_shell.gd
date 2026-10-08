extends Control

const DEFAULT_TITLE := "Make Your Mini Hero ✨"
const DEFAULT_SUBTITLE := "Create, dress, and save your hero in Mini Utopia."

@onready var bridge: MiniUtopiaBridgeClient = $BridgeClient
@onready var status_label: Label = $RootMargin/MainColumn/StatusBar/StatusLabel
@onready var character_label: Label = $RootMargin/MainColumn/HeaderRow/CharacterLabel
@onready var back_button: Button = $RootMargin/MainColumn/FooterRow/BackButton
@onready var save_button: Button = $RootMargin/MainColumn/FooterRow/SaveButton
@onready var avatar_stage: MiniUtopiaCreatorAvatarStage = $RootMargin/MainColumn/CreatorBody/PreviewPanel/AvatarStage

var character_id := ""
var loaded_character: Dictionary = {}
var _return_scene := "res://scenes/main.tscn"


func _ready() -> void:
    back_button.pressed.connect(_on_back_pressed)
    save_button.pressed.connect(_on_save_pressed)
    bridge.request_succeeded.connect(_on_bridge_success)
    bridge.request_failed.connect(_on_bridge_failure)

    _read_user_args()
    _set_status("Connecting to Mini Utopia…", false)

    if character_id.is_empty():
        character_label.text = "New Hero"
        _set_status(
            "Creator shell ready · choose a character to edit next.",
            false
        )
        save_button.disabled = true
        return

    character_label.text = character_id
    save_button.disabled = true
    var error := bridge.get_character(character_id)
    if error != OK:
        _set_status("Could not start Character load.", true)


func _read_user_args() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--character-id="):
            character_id = arg.trim_prefix("--character-id=").strip_edges()
        elif arg.begins_with("--return-scene="):
            var value := arg.trim_prefix("--return-scene=").strip_edges()
            if not value.is_empty():
                _return_scene = value


func _on_bridge_success(kind: String, payload: Dictionary) -> void:
    if kind == "character:get":
        loaded_character = payload.duplicate(true)
        character_id = String(payload.get("character_id", character_id))
        var display_name := String(payload.get("display_name", character_id))
        character_label.text = (
            display_name if not display_name.is_empty() else character_id
        )
        var profile = payload.get("profile", {})
        if typeof(profile) == TYPE_DICTIONARY:
            var appearance = profile.get("avatar", {})
            if typeof(appearance) == TYPE_DICTIONARY:
                avatar_stage.apply_appearance(appearance)
        save_button.disabled = false
        _set_status("Character loaded · ready to create.", false)
        return

    if kind == "character:put":
        loaded_character = payload.duplicate(true)
        save_button.disabled = false
        _set_status("Saved! Your hero is safe in Mini Utopia. 💖", false)


func _on_bridge_failure(
    kind: String,
    status_code: int,
    _error_code: String,
    message: String
) -> void:
    save_button.disabled = true

    if kind == "character:get":
        if status_code == 404:
            _set_status(
                "Character not found. Return and choose another hero.",
                true
            )
        else:
            _set_status(
                message + " Start the Mini Utopia Bridge and try again.",
                true
            )
        return

    if kind == "character:put":
        if status_code == 409:
            _set_status(
                "This hero changed somewhere else. Reopen it before saving.",
                true
            )
        else:
            _set_status("Save failed. " + message, true)


func _on_back_pressed() -> void:
    if ResourceLoader.exists(_return_scene):
        get_tree().change_scene_to_file(_return_scene)
        return
    get_tree().quit()


func _on_save_pressed() -> void:
    if character_id.is_empty() or loaded_character.is_empty():
        _set_status("Nothing to save yet.", true)
        return

    save_button.disabled = true
    _set_status("Saving your hero…", false)

    var payload := {
        "schema_version": String(
            loaded_character.get("schema_version", "1.0")
        ),
        "revision": String(loaded_character.get("revision", "")),
        "display_name": String(
            loaded_character.get("display_name", character_id)
        ),
        "description": String(loaded_character.get("description", "")),
        "profile": loaded_character.get("profile", {}),
    }
    var error := bridge.put_character(character_id, payload)
    if error != OK:
        save_button.disabled = false
        _set_status("Could not start Save. Please try again.", true)


func _set_status(message: String, is_error: bool) -> void:
    status_label.text = message
    status_label.modulate = (
        Color("#B5485D") if is_error else Color("#4F4868")
    )

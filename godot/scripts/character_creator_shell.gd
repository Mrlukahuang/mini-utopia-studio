extends Control

const DEFAULT_TITLE := "Make Your Mini Hero ✨"
const DEFAULT_SUBTITLE := "Create, dress, and save your hero in Mini Utopia."

const BODY_BUTTONS := {
    "SlimButton": "slim",
    "StandardButton": "standard",
    "ChubbyButton": "chubby",
}
const SPECIES_BUTTONS := {
    "HumanButton": "species_head_human_v1",
    "SheepButton": "species_head_sheep_v1",
    "RobotButton": "species_head_robot_v1",
    "CatButton": "species_head_cat_v1",
    "CloudButton": "species_head_cloud_v1",
}
const SURFACE_BUTTONS := {
    "SkinButton": "skin",
    "FurButton": "fur",
    "WoolButton": "wool",
    "MetalButton": "metal",
    "CloudButton": "cloud",
}

@onready var bridge: MiniUtopiaBridgeClient = $BridgeClient
@onready var status_label: Label = $RootMargin/MainColumn/StatusBar/StatusLabel
@onready var character_label: Label = $RootMargin/MainColumn/HeaderRow/CharacterLabel
@onready var back_button: Button = $RootMargin/MainColumn/FooterRow/BackButton
@onready var save_button: Button = $RootMargin/MainColumn/FooterRow/SaveButton
@onready var avatar_stage: MiniUtopiaCreatorAvatarStage = $RootMargin/MainColumn/CreatorBody/PreviewPanel/AvatarStage
@onready var body_row: HBoxContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Content/BodyRow
@onready var species_grid: GridContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Content/SpeciesGrid
@onready var surface_grid: GridContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Content/SurfaceGrid
@onready var zoom_out_button: Button = $RootMargin/MainColumn/CreatorBody/PreviewPanel/ZoomControls/ZoomOutButton
@onready var reset_button: Button = $RootMargin/MainColumn/CreatorBody/PreviewPanel/ZoomControls/ResetButton
@onready var zoom_in_button: Button = $RootMargin/MainColumn/CreatorBody/PreviewPanel/ZoomControls/ZoomInButton

var character_id := ""
var loaded_character: Dictionary = {}
var _draft_appearance: Dictionary = {}
var _return_scene := "res://scenes/main.tscn"


func _ready() -> void:
    back_button.pressed.connect(_on_back_pressed)
    save_button.pressed.connect(_on_save_pressed)
    bridge.request_succeeded.connect(_on_bridge_success)
    bridge.request_failed.connect(_on_bridge_failure)
    _wire_look_controls()

    _draft_appearance = avatar_stage.current_appearance()
    _refresh_look_controls()

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


func _wire_look_controls() -> void:
    for button_name in BODY_BUTTONS:
        var button := body_row.get_node(button_name) as Button
        button.pressed.connect(
            _on_body_selected.bind(String(BODY_BUTTONS[button_name]))
        )

    for button_name in SPECIES_BUTTONS:
        var button := species_grid.get_node(button_name) as Button
        button.pressed.connect(
            _on_species_selected.bind(
                String(SPECIES_BUTTONS[button_name])
            )
        )

    for button_name in SURFACE_BUTTONS:
        var button := surface_grid.get_node(button_name) as Button
        button.pressed.connect(
            _on_surface_selected.bind(
                String(SURFACE_BUTTONS[button_name])
            )
        )

    zoom_in_button.pressed.connect(avatar_stage.zoom_in)
    zoom_out_button.pressed.connect(avatar_stage.zoom_out)
    reset_button.pressed.connect(avatar_stage.reset_camera)


func _on_body_selected(body_type: String) -> void:
    _draft_appearance["body_type"] = body_type
    _commit_live_appearance("Body changed instantly.")


func _on_species_selected(species_head_id: String) -> void:
    _draft_appearance["species_head_id"] = species_head_id

    var allowed_surfaces := (
        MiniUtopiaCreatorAvatarCatalog.allowed_surface_ids(species_head_id)
    )
    var current_surface := String(
        _draft_appearance.get("surface_type", "skin")
    )
    if not allowed_surfaces.has(current_surface):
        _draft_appearance["surface_type"] = (
            MiniUtopiaCreatorAvatarCatalog.species_default_surface(
                species_head_id
            )
        )

    var allowed_eyes := (
        MiniUtopiaCreatorAvatarCatalog.allowed_eye_ids(species_head_id)
    )
    var current_eye := String(
        _draft_appearance.get("eye_style_id", "eyes_round_soft_v1")
    )
    if not allowed_eyes.has(current_eye):
        _draft_appearance["eye_style_id"] = allowed_eyes[0]

    var allowed_hair := (
        MiniUtopiaCreatorAvatarCatalog.allowed_hair_ids(species_head_id)
    )
    var current_hair := String(
        _draft_appearance.get("hair_style_id", "hair_none")
    )
    if not allowed_hair.has(current_hair):
        _draft_appearance["hair_style_id"] = allowed_hair[0]

    _commit_live_appearance("Species changed instantly.")


func _on_surface_selected(surface_type: String) -> void:
    var species_head_id := String(
        _draft_appearance.get(
            "species_head_id",
            "species_head_human_v1"
        )
    )
    var allowed := (
        MiniUtopiaCreatorAvatarCatalog.allowed_surface_ids(species_head_id)
    )
    if not allowed.has(surface_type):
        _refresh_look_controls()
        return

    _draft_appearance["surface_type"] = surface_type
    _commit_live_appearance("Surface changed instantly.")


func _commit_live_appearance(message: String) -> void:
    _draft_appearance["customized"] = true
    avatar_stage.apply_appearance(_draft_appearance)
    _draft_appearance = avatar_stage.current_appearance()
    _sync_loaded_profile_avatar()
    _refresh_look_controls()

    if loaded_character.is_empty():
        _set_status(message + " Preview mode · not saved yet.", false)
    else:
        _set_status(message + " Press Save when ready.", false)


func _sync_loaded_profile_avatar() -> void:
    if loaded_character.is_empty():
        return
    var profile = loaded_character.get("profile", {})
    if typeof(profile) != TYPE_DICTIONARY:
        return
    profile["avatar"] = _draft_appearance.duplicate(true)
    loaded_character["profile"] = profile


func _refresh_look_controls() -> void:
    var body_type := String(
        _draft_appearance.get("body_type", "standard")
    )
    for button_name in BODY_BUTTONS:
        var button := body_row.get_node(button_name) as Button
        button.button_pressed = (
            String(BODY_BUTTONS[button_name]) == body_type
        )

    var species_head_id := String(
        _draft_appearance.get(
            "species_head_id",
            "species_head_human_v1"
        )
    )
    for button_name in SPECIES_BUTTONS:
        var button := species_grid.get_node(button_name) as Button
        button.button_pressed = (
            String(SPECIES_BUTTONS[button_name]) == species_head_id
        )

    var allowed_surfaces := (
        MiniUtopiaCreatorAvatarCatalog.allowed_surface_ids(species_head_id)
    )
    var surface_type := String(
        _draft_appearance.get("surface_type", "skin")
    )
    for button_name in SURFACE_BUTTONS:
        var button := surface_grid.get_node(button_name) as Button
        var option_id := String(SURFACE_BUTTONS[button_name])
        button.disabled = not allowed_surfaces.has(option_id)
        button.button_pressed = option_id == surface_type


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
                _draft_appearance = appearance.duplicate(true)
                avatar_stage.apply_appearance(_draft_appearance)
                _draft_appearance = avatar_stage.current_appearance()
                _refresh_look_controls()
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

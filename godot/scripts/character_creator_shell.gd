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
const ANIMATION_BUTTONS := {
    "IdleButton": "Idle",
    "WalkButton": "Walk",
    "RunButton": "Run",
    "JumpButton": "Jump",
}

const COLOR_BUTTONS := {
    "CreamButton": "#F6F1E8",
    "WarmButton": "#F2C7A5",
    "TanButton": "#C98E68",
    "BrownButton": "#9A7657",
    "DarkButton": "#5B4036",
    "BlackButton": "#393A46",
    "PinkButton": "#F7B7D2",
    "MintButton": "#B9E7D0",
    "LavenderButton": "#D7C2F3",
    "SkyButton": "#BDE3F5",
    "PeachButton": "#F5C1B8",
    "GoldButton": "#F2C75C",
}

@onready var bridge: MiniUtopiaBridgeClient = $BridgeClient
@onready var choice_content: VBoxContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content
@onready var choice_scroll: ScrollContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll
@onready var look_tab: Button = $RootMargin/MainColumn/StepTabs/LookStep
@onready var outfit_tab: Button = $RootMargin/MainColumn/StepTabs/OutfitStep
@onready var status_label: Label = $RootMargin/MainColumn/StatusBar/StatusLabel
@onready var character_label: Label = $RootMargin/MainColumn/HeaderRow/CharacterLabel
@onready var hero_name_input: LineEdit = $RootMargin/MainColumn/HeaderRow/TitleColumn/HeroNameInput
@onready var back_button: Button = $RootMargin/MainColumn/FooterRow/BackButton
@onready var save_button: Button = $RootMargin/MainColumn/FooterRow/SaveButton
@onready var play_button: Button = $RootMargin/MainColumn/FooterRow/PlayButton
@onready var avatar_stage: MiniUtopiaCreatorAvatarStage = $RootMargin/MainColumn/CreatorBody/PreviewPanel/AvatarStage
@onready var body_row: HBoxContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/BodyRow
@onready var species_grid: GridContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/SpeciesGrid
@onready var surface_grid: GridContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/SurfaceGrid
@onready var eye_style_option: OptionButton = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/EyeStyleOption
@onready var hair_style_option: OptionButton = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/HairStyleOption
@onready var color_target_option: OptionButton = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/ColorTargetOption
@onready var color_grid: GridContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/ColorGrid
@onready var animation_controls: HBoxContainer = $RootMargin/MainColumn/CreatorBody/PreviewPanel/AnimationControls
@onready var zoom_out_button: Button = $RootMargin/MainColumn/CreatorBody/PreviewPanel/ZoomControls/ZoomOutButton
@onready var reset_button: Button = $RootMargin/MainColumn/CreatorBody/PreviewPanel/ZoomControls/ResetButton
@onready var zoom_in_button: Button = $RootMargin/MainColumn/CreatorBody/PreviewPanel/ZoomControls/ZoomInButton

var character_id := ""
var loaded_character: Dictionary = {}
var equipment_state: Dictionary = {}
var _appearance_dirty := false
var _outfit_choices: VBoxContainer
var _outfit_mode := false
var _craft_shape := "star"
var _craft_slot := "accessory"
var _craft_color := "#F7B7D2"
var _craft_accent := "#F2C75C"
var _craft_name_input: LineEdit
var _draft_appearance: Dictionary = {}
var _eye_option_ids: Array[String] = []
var _hair_option_ids: Array[String] = []
var _return_scene := "res://scenes/main.tscn"


func _ready() -> void:
    back_button.pressed.connect(_on_back_pressed)
    save_button.pressed.connect(_on_save_pressed)
    play_button.pressed.connect(_on_play_pressed)
    hero_name_input.text_changed.connect(_on_hero_name_changed)
    bridge.request_succeeded.connect(_on_bridge_success)
    bridge.request_failed.connect(_on_bridge_failure)
    _wire_look_controls()
    _wire_animation_controls()
    _wire_outfit_controls()

    _draft_appearance = avatar_stage.current_appearance()
    _refresh_look_controls()

    _read_user_args()
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family != null and family.has_family_connection():
        if character_id.is_empty() and not family.pending_character_id.is_empty():
            character_id = family.pending_character_id
        if not family.bind_family_client(bridge):
            _set_status("Parent session is unavailable. Reopen My Heroes.", true)
            save_button.disabled = true
            return
    _set_status("Connecting to Mini Utopia…", false)

    if character_id.is_empty():
        character_label.text = "New Hero"
        _set_status(
            "Name your hero · parent Family Cloud sign-in required to save.",
            false
        )
        save_button.disabled = true
        return

    character_label.text = character_id
    save_button.disabled = true
    var error := bridge.get_character(character_id)
    if error != OK:
        if error == ERR_UNCONFIGURED and OS.has_feature("web"):
            _set_status("Family Cloud not connected yet · preview only.", true)
        else:
            _set_status("Could not start Character load.", true)


func _wire_outfit_controls() -> void:
    _outfit_choices = VBoxContainer.new()
    _outfit_choices.name = "OutfitChoices"
    _outfit_choices.visible = false
    _outfit_choices.add_theme_constant_override("separation", 8)
    choice_content.add_child(_outfit_choices)
    look_tab.pressed.connect(_select_creator_tab.bind("look"))
    outfit_tab.pressed.connect(_select_creator_tab.bind("outfit"))


func _select_creator_tab(tab: String) -> void:
    _outfit_mode = tab == "outfit"
    if _outfit_choices == null:
        return
    for child in choice_content.get_children():
        if child == _outfit_choices:
            child.visible = _outfit_mode
        elif child.name not in ["Heading", "Hint"]:
            child.visible = not _outfit_mode

    var heading := choice_content.get_node("Heading") as Label
    var hint := choice_content.get_node("Hint") as Label
    if _outfit_mode:
        heading.text = "Dress Your Hero / 我的衣柜"
        hint.text = "Tap a piece to try it on. Every change is saved."
        _refresh_outfit_choices()
    else:
        heading.text = "Build Your Hero"
        hint.text = "Tap a choice. Your 3D hero changes instantly."
    choice_scroll.scroll_vertical = 0


func _refresh_outfit_choices() -> void:
    if _outfit_choices == null:
        return
    for child in _outfit_choices.get_children():
        # Release names immediately; queued nodes otherwise collide with the
        # new choices on rapid iPad Outfit/Look tab switching.
        _outfit_choices.remove_child(child)
        child.queue_free()

    if equipment_state.is_empty():
        var help := Label.new()
        help.text = "Save your Hero to open your private wardrobe."
        help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
        _outfit_choices.add_child(help)
        return

    _build_craft_prop_panel()

    var slots = equipment_state.get("slots", [])
    var items = equipment_state.get("items", [])
    if typeof(slots) != TYPE_ARRAY or typeof(items) != TYPE_ARRAY:
        return

    for raw_slot in slots:
        var slot := String(raw_slot)
        var heading := Label.new()
        heading.name = "Slot_" + slot
        heading.text = slot.replace("_", " ").capitalize()
        heading.add_theme_font_size_override("font_size", 19)
        _outfit_choices.add_child(heading)

        var currently_equipped := false
        for raw_item in items:
            if typeof(raw_item) != TYPE_DICTIONARY:
                continue
            var item: Dictionary = raw_item
            if String(item.get("slot", "")) != slot:
                continue
            var item_id := String(item.get("item_instance_id", ""))
            if item_id.is_empty():
                continue
            var picked := bool(item.get("equipped", false))
            currently_equipped = currently_equipped or picked

            var choice := Button.new()
            choice.name = "Wear_" + slot + "_" + item_id
            choice.custom_minimum_size = Vector2(0.0, 48.0)
            choice.add_theme_font_size_override("font_size", 17)
            choice.text = (
                ("✓ Wearing  " if picked else "＋ Wear  ")
                + String(item.get("display_name", "My Item"))
            )
            choice.disabled = picked
            choice.pressed.connect(
                _on_equipment_choice_pressed.bind(slot, item_id)
            )
            _outfit_choices.add_child(choice)

        if currently_equipped:
            var remove := Button.new()
            remove.name = "Remove_" + slot
            remove.text = "− Take off"
            remove.custom_minimum_size = Vector2(0.0, 42.0)
            remove.pressed.connect(
                _on_equipment_choice_pressed.bind(slot, "")
            )
            _outfit_choices.add_child(remove)


func _build_craft_prop_panel() -> void:
    if character_id.is_empty() or not bridge.has_family_session():
        return
    var section := VBoxContainer.new()
    section.name = "MakeNewPropPanel"
    section.add_theme_constant_override("separation", 8)
    _outfit_choices.add_child(section)

    var heading := Label.new()
    heading.text = "✨ Create My Own Prop / 创造道具"
    heading.add_theme_font_size_override("font_size", 21)
    section.add_child(heading)

    _craft_name_input = LineEdit.new()
    _craft_name_input.name = "MyPropName"
    _craft_name_input.placeholder_text = "Name your creation · 给道具取个名字"
    _craft_name_input.max_length = 32
    _craft_name_input.custom_minimum_size.y = 48
    section.add_child(_craft_name_input)

    var shape_option := OptionButton.new()
    shape_option.name = "PropShape"
    shape_option.custom_minimum_size.y = 48
    for label in ["⭐ Star", "❤️ Heart", "⚪ Ball", "🧊 Box"]:
        shape_option.add_item(label)
    shape_option.selected = ["star", "heart", "sphere", "box"].find(_craft_shape)
    shape_option.item_selected.connect(_on_craft_shape_selected)
    section.add_child(shape_option)

    var color_option := OptionButton.new()
    color_option.name = "PropColor"
    color_option.custom_minimum_size.y = 48
    for label in ["Pink / 粉色", "Mint / 薄荷绿", "Blue / 天蓝", "Gold / 金色", "Purple / 紫色"]:
        color_option.add_item(label)
    var colors := ["#F7B7D2", "#B9E7D0", "#74B9FF", "#F2C75C", "#B79CED"]
    color_option.selected = maxi(0, colors.find(_craft_color))
    color_option.item_selected.connect(_on_craft_color_selected)
    section.add_child(color_option)

    var slot_option := OptionButton.new()
    slot_option.name = "PropSlot"
    slot_option.custom_minimum_size.y = 48
    for label in ["✨ Accessory", "👑 Headwear", "🪄 Hand prop", "🎒 Backpack"]:
        slot_option.add_item(label)
    slot_option.selected = maxi(
        0, ["accessory", "headwear", "weapon_main", "backpack"].find(_craft_slot)
    )
    slot_option.item_selected.connect(_on_craft_slot_selected)
    section.add_child(slot_option)

    var submit := Button.new()
    submit.name = "CreatePropButton"
    submit.text = "✨ Create & Save My Prop"
    submit.custom_minimum_size.y = 58
    submit.add_theme_font_size_override("font_size", 19)
    submit.pressed.connect(_on_create_prop_pressed)
    section.add_child(submit)


func _on_craft_shape_selected(index: int) -> void:
    _craft_shape = ["star", "heart", "sphere", "box"][index]


func _on_craft_color_selected(index: int) -> void:
    _craft_color = [
        "#F7B7D2", "#B9E7D0", "#74B9FF", "#F2C75C", "#B79CED"
    ][index]


func _on_craft_slot_selected(index: int) -> void:
    _craft_slot = [
        "accessory", "headwear", "weapon_main", "backpack"
    ][index]


func _on_create_prop_pressed() -> void:
    if character_id.is_empty() or not bridge.has_family_session() or bridge.is_busy():
        _set_status("Connect and save your Hero before making a prop.", true)
        return
    if _craft_name_input == null:
        return
    var name := _craft_name_input.text.strip_edges()
    if name.is_empty():
        _set_status("Give your own prop a name first!", true)
        return
    var request := {
        "schema_version": "1.0",
        "display_name": name,
        "shape": _craft_shape,
        "slot": _craft_slot,
        "color_hex": _craft_color,
        "accent_color_hex": _craft_accent,
    }
    var error := bridge.craft_family_prop(character_id, request)
    if error == OK:
        _set_status("Saving your original creation in your private wardrobe…", false)
    else:
        _set_status("Could not save your new prop. Try again.", true)


func _on_equipment_choice_pressed(slot: String, item_id: String) -> void:
    if character_id.is_empty() or bridge.is_busy():
        _set_status("Finish the current wardrobe change first.", true)
        return
    var id: Variant = null if item_id.is_empty() else item_id
    var error := bridge.put_equipment_slot(character_id, slot, id)
    if error == OK:
        _set_status("Updating your outfit…", false)
    else:
        _set_status("Could not change your outfit. Please retry.", true)


func activate_family_session(token: String, api_base_url: String) -> bool:
    # Explicit session activation is allowed only in memory; a parent-managed
    # token issuer must replace raw token entry before public deployment.
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null or not family.connect_family(api_base_url, token):
        save_button.disabled = true
        _set_status("Family Cloud sign-in required to save.", true)
        return false
    if not family.bind_family_client(bridge):
        save_button.disabled = true
        _set_status("Family Cloud sign-in required to save.", true)
        return false

    if character_id.is_empty():
        _on_hero_name_changed(hero_name_input.text)
        _set_status("Family Cloud connected · name and save your hero.", false)
    else:
        save_button.disabled = true
        var error := bridge.get_character(character_id)
        if error != OK:
            _set_status("Could not load the Family Cloud hero.", true)
            return false
    return true


func _on_hero_name_changed(_value: String) -> void:
    var has_name := not hero_name_input.text.strip_edges().is_empty()
    if not loaded_character.is_empty():
        play_button.disabled = (
            _appearance_dirty
            or equipment_state.is_empty()
            or hero_name_input.text.strip_edges() != String(
                loaded_character.get("display_name", "")
            )
        )
    if character_id.is_empty():
        save_button.disabled = not (has_name and bridge.has_family_session())
    elif not loaded_character.is_empty():
        save_button.disabled = not has_name


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

    eye_style_option.item_selected.connect(_on_eye_style_selected)
    hair_style_option.item_selected.connect(_on_hair_style_selected)

    color_target_option.clear()
    color_target_option.add_item("Surface / 表面")
    color_target_option.add_item("Eyes / 眼睛")
    color_target_option.add_item("Hair / 头发")
    color_target_option.select(0)
    color_target_option.item_selected.connect(_on_color_target_selected)

    for button_name in COLOR_BUTTONS:
        var button := color_grid.get_node(button_name) as Button
        button.pressed.connect(
            _on_color_selected.bind(String(COLOR_BUTTONS[button_name]))
        )

    zoom_in_button.pressed.connect(avatar_stage.zoom_in)
    zoom_out_button.pressed.connect(avatar_stage.zoom_out)
    reset_button.pressed.connect(avatar_stage.reset_camera)


func _wire_animation_controls() -> void:
    for button_name in ANIMATION_BUTTONS:
        var button := animation_controls.get_node(button_name) as Button
        button.pressed.connect(
            _on_animation_selected.bind(
                String(ANIMATION_BUTTONS[button_name])
            )
        )
    _refresh_animation_buttons()


func _on_animation_selected(animation_name: String) -> void:
    avatar_stage.play_preview_animation(animation_name)
    _refresh_animation_buttons()
    _set_status(animation_name + " preview · instant Godot runtime.", false)


func _refresh_animation_buttons() -> void:
    var current := avatar_stage.current_preview_animation()
    for button_name in ANIMATION_BUTTONS:
        var button := animation_controls.get_node(button_name) as Button
        button.button_pressed = (
            String(ANIMATION_BUTTONS[button_name]) == current
        )


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


func _on_eye_style_selected(index: int) -> void:
    if index < 0 or index >= _eye_option_ids.size():
        return
    _draft_appearance["eye_style_id"] = _eye_option_ids[index]
    _commit_live_appearance("Eyes changed instantly.")


func _on_hair_style_selected(index: int) -> void:
    if index < 0 or index >= _hair_option_ids.size():
        return
    _draft_appearance["hair_style_id"] = _hair_option_ids[index]
    _commit_live_appearance("Hair changed instantly.")


func _on_color_target_selected(_index: int) -> void:
    _refresh_color_buttons()


func _on_color_selected(hex_value: String) -> void:
    _draft_appearance[_active_color_field()] = hex_value
    _commit_live_appearance("Color changed instantly.")


func _active_color_field() -> String:
    match color_target_option.selected:
        1:
            return "eye_color_hex"
        2:
            return "hair_color_hex"
        _:
            return "surface_color_hex"


func _normalize_detail_compatibility() -> void:
    var species_head_id := String(
        _draft_appearance.get(
            "species_head_id",
            "species_head_human_v1"
        )
    )

    var allowed_eyes := (
        MiniUtopiaCreatorAvatarCatalog.allowed_eye_ids(species_head_id)
    )
    var eye_style := String(
        _draft_appearance.get("eye_style_id", "eyes_round_soft_v1")
    )
    if not allowed_eyes.has(eye_style):
        _draft_appearance["eye_style_id"] = allowed_eyes[0]

    var allowed_hair := (
        MiniUtopiaCreatorAvatarCatalog.allowed_hair_ids(species_head_id)
    )
    var hair_style := String(
        _draft_appearance.get("hair_style_id", "hair_none")
    )
    if not allowed_hair.has(hair_style):
        _draft_appearance["hair_style_id"] = allowed_hair[0]


func _commit_live_appearance(message: String) -> void:
    # Play uses the last server-saved Character, never unsaved appearance.
    play_button.disabled = true
    _appearance_dirty = true
    _draft_appearance["customized"] = true
    _normalize_detail_compatibility()
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

    _refresh_detail_controls()


func _refresh_detail_controls() -> void:
    var species_head_id := String(
        _draft_appearance.get(
            "species_head_id",
            "species_head_human_v1"
        )
    )

    _eye_option_ids = (
        MiniUtopiaCreatorAvatarCatalog.allowed_eye_ids(species_head_id)
    )
    eye_style_option.clear()
    for option_id in _eye_option_ids:
        eye_style_option.add_item(
            String(
                MiniUtopiaCreatorAvatarCatalog.EYE_OPTIONS.get(
                    option_id,
                    option_id
                )
            )
        )
    _select_option_by_id(
        eye_style_option,
        _eye_option_ids,
        String(
            _draft_appearance.get(
                "eye_style_id",
                "eyes_round_soft_v1"
            )
        )
    )

    _hair_option_ids = (
        MiniUtopiaCreatorAvatarCatalog.allowed_hair_ids(species_head_id)
    )
    hair_style_option.clear()
    for option_id in _hair_option_ids:
        hair_style_option.add_item(
            String(
                MiniUtopiaCreatorAvatarCatalog.HAIR_OPTIONS.get(
                    option_id,
                    option_id
                )
            )
        )
    _select_option_by_id(
        hair_style_option,
        _hair_option_ids,
        String(
            _draft_appearance.get("hair_style_id", "hair_none")
        )
    )

    _refresh_color_buttons()


func _select_option_by_id(
    option: OptionButton,
    ids: Array[String],
    target_id: String
) -> void:
    var index := ids.find(target_id)
    option.select(index if index >= 0 else 0)


func _refresh_color_buttons() -> void:
    var current_hex := String(
        _draft_appearance.get(_active_color_field(), "")
    )
    for button_name in COLOR_BUTTONS:
        var button := color_grid.get_node(button_name) as Button
        button.button_pressed = (
            String(COLOR_BUTTONS[button_name]) == current_hex
        )


func _on_bridge_success(kind: String, payload: Dictionary) -> void:
    if kind == "prop:craft":
        var crafted = payload.get("crafted", {})
        var owned = payload.get("equipment", {})
        if (
            typeof(crafted) != TYPE_DICTIONARY
            or typeof(owned) != TYPE_DICTIONARY
            or String(crafted.get("character_id", "")) != character_id
            or String(owned.get("character_id", "")) != character_id
        ):
            _set_status("Your new prop could not be verified.", true)
            return
        equipment_state = owned.duplicate(true)
        _refresh_outfit_choices()
        var runtime = equipment_state.get("runtime", {})
        if typeof(runtime) == TYPE_DICTIONARY:
            avatar_stage.apply_equipment_runtime(runtime)
        _set_status("New prop saved! Tap Wear to put it on your Hero.", false)
        return

    if kind == "character:get":
        equipment_state.clear()
        _appearance_dirty = false
        play_button.disabled = true
        loaded_character = payload.duplicate(true)
        character_id = String(payload.get("character_id", character_id))
        var display_name := String(payload.get("display_name", character_id))
        character_label.text = (
            display_name if not display_name.is_empty() else character_id
        )
        hero_name_input.text = display_name
        var profile = payload.get("profile", {})
        if typeof(profile) == TYPE_DICTIONARY:
            var appearance = profile.get("avatar", {})
            if typeof(appearance) == TYPE_DICTIONARY:
                _draft_appearance = appearance.duplicate(true)
                _normalize_detail_compatibility()
                avatar_stage.apply_appearance(_draft_appearance)
                _draft_appearance = avatar_stage.current_appearance()
                _refresh_look_controls()
        save_button.disabled = false
        play_button.disabled = true
        _set_status("Hero loaded · fetching your own clothes and props…", false)
        var equipment_error := bridge.get_equipment(character_id)
        if equipment_error != OK:
            _set_status(
                "Character loaded · My Stuff could not start loading.",
                true
            )
        return

    if kind == "equipment:get" or kind.begins_with("equipment:put:"):
        equipment_state = payload.duplicate(true)
        _refresh_outfit_choices()
        var runtime = payload.get("runtime", {})
        var valid := (
            typeof(runtime) == TYPE_DICTIONARY
            and String(runtime.get("character_asset_id", "")) == character_id
        )
        if valid:
            avatar_stage.apply_equipment_runtime(runtime)
        play_button.disabled = (
            not valid or loaded_character.is_empty() or _appearance_dirty
        )
        _set_status(
            "Hero + your clothes and props loaded."
            if valid else "Clothes could not be verified.",
            not valid
        )
        return

    if kind == "character:post":
        loaded_character = payload.duplicate(true)
        _appearance_dirty = false
        character_id = String(payload.get("character_id", ""))
        character_label.text = String(payload.get("display_name", "New Hero"))
        hero_name_input.text = character_label.text
        save_button.disabled = character_id.is_empty()
        play_button.disabled = true
        equipment_state.clear()
        _set_status("Hero saved · loading your own clothes and props…", false)
        if not character_id.is_empty():
            var equipment_error := bridge.get_equipment(character_id)
            if equipment_error != OK:
                _set_status("Saved, but clothes are not ready yet.", true)
        return

    if kind == "character:put":
        loaded_character = payload.duplicate(true)
        _appearance_dirty = false
        save_button.disabled = false
        play_button.disabled = equipment_state.is_empty()
        _set_status("Saved! Your hero is safe in Mini Utopia. 💖", false)


func _on_bridge_failure(
    kind: String,
    status_code: int,
    _error_code: String,
    message: String
) -> void:
    if kind == "prop:craft":
        _set_status("Could not create your prop. Choose a different name or try again.", true)
        return
    if kind.begins_with("equipment:"):
        play_button.disabled = true
        _set_status("My Stuff could not load. " + message, true)
        return

    save_button.disabled = true

    if kind == "character:get":
        if status_code == 404:
            _set_status(
                "Character not found. Return and choose another hero.",
                true
            )
        else:
            var help := (
                " Family Cloud is unavailable."
                if OS.has_feature("web")
                else " Start the Mini Utopia Bridge and try again."
            )
            _set_status(message + help, true)
        return

    if kind == "character:post":
        save_button.disabled = false
        _set_status("Could not create your hero. " + message, true)
        return

    if kind == "character:put":
        if status_code == 409:
            _set_status(
                "This hero changed somewhere else. Reopen it before saving.",
                true
            )
        else:
            _set_status("Save failed. " + message, true)


func _on_play_pressed() -> void:
    if play_button.disabled or loaded_character.is_empty():
        _set_status("Save your hero before playing.", true)
        return
    var family_state := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family_state == null or not family_state.select_character(loaded_character):
        _set_status("Your saved hero could not enter the village.", true)
        return
    var runtime = equipment_state.get("runtime", {})
    if (
        typeof(runtime) != TYPE_DICTIONARY
        or not family_state.select_equipment(runtime)
    ):
        family_state.clear_selection()
        _set_status("Your own clothes and props must load before playing.", true)
        return
    var target := "res://scenes/main.tscn"
    if not ResourceLoader.exists(target):
        _set_status("Village is not available yet.", true)
        return
    get_tree().change_scene_to_file(target)


func _on_back_pressed() -> void:
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if (
        family != null
        and family.has_family_connection()
        and _return_scene == "res://scenes/main.tscn"
    ):
        get_tree().change_scene_to_file("res://scenes/family_hero_library.tscn")
        return
    if ResourceLoader.exists(_return_scene):
        get_tree().change_scene_to_file(_return_scene)
        return
    get_tree().quit()


func _on_save_pressed() -> void:
    var name := hero_name_input.text.strip_edges()
    if name.is_empty():
        _set_status("Please give your hero a name first.", true)
        return

    if character_id.is_empty():
        if not bridge.has_family_session():
            _set_status("Parent Cloud sign-in is required to save.", true)
            return
        save_button.disabled = true
        _set_status("Creating your hero…", false)
        var create_error := bridge.create_character({
            "schema_version": "1.0",
            "display_name": name,
            "description": "",
            "profile": {"avatar": _draft_appearance.duplicate(true)},
        })
        if create_error != OK:
            save_button.disabled = false
            _set_status("Could not begin creating your hero.", true)
        return

    if loaded_character.is_empty():
        _set_status("Please load your hero before saving changes.", true)
        return

    save_button.disabled = true
    _set_status("Saving your hero…", false)

    var payload := {
        "schema_version": String(
            loaded_character.get("schema_version", "1.0")
        ),
        "revision": String(loaded_character.get("revision", "")),
        "display_name": name,
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

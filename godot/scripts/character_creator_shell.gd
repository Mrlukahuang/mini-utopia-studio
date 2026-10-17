extends Control

const DEFAULT_TITLE := "做一个你的小英雄！"
const DEFAULT_SUBTITLE := "给英雄起名字、选造型，再去村子玩！"

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

const EYE_LABELS := {
    "eyes_round_soft_v1": "圆眼睛",
    "eyes_sparkle_v1": "亮晶晶",
    "eyes_sleepy_v1": "眯眯眼",
    "eyes_robot_v1": "机器人眼",
    "eyes_cat_v1": "猫眼睛",
}
const HAIR_LABELS := {
    "hair_none": "没有头发",
    "hair_short_v1": "短发",
    "hair_bob_v1": "齐耳短发",
    "hair_long_wavy_v1": "长卷发",
    "hair_ponytail_v1": "马尾",
    "hair_fluffy_v1": "蓬蓬头",
}
const ANIMATION_LABELS := {
    "Idle": "站立",
    "Walk": "走路",
    "Run": "跑步",
    "Jump": "跳跃",
}
const SLOT_LABELS := {
    "headwear": "头饰",
    "top": "上衣",
    "bottom": "裤子",
    "shoes": "鞋子",
    "gloves": "手套",
    "accessory": "小饰品",
    "backpack": "背包",
    "weapon_main": "手持道具",
    "weapon_offhand": "副手道具",
}

const FRIENDLY_NAMES := [
    "小星星 Star", "露露 Lulu", "彩虹 Rainbow",
    "米米 Mimi", "泡泡 Bubbles", "豆豆 Dodo",
    "闪闪 Sparkle", "诺诺 Nono",
]
const HAND_STYLES := {
    "SwordStyleButton": "sword_1handed",
    "ShieldStyleButton": "shield_round",
    "StaffStyleButton": "staff",
    "WandStyleButton": "wand",
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
    "PearlButton": "#E8ECEF",
    "RobotBlueButton": "#A9CFE8",
}

@onready var bridge: MiniUtopiaBridgeClient = $BridgeClient
@onready var choice_content: VBoxContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content
@onready var choice_scroll: ScrollContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll
@onready var look_tab: Button = $RootMargin/MainColumn/StepTabs/LookStep
@onready var outfit_tab: Button = $RootMargin/MainColumn/StepTabs/OutfitStep
@onready var status_label: Label = $RootMargin/MainColumn/StatusBar/StatusLabel
@onready var character_label: Label = $RootMargin/MainColumn/HeaderRow/CharacterLabel
@onready var hero_name_input: LineEdit = $RootMargin/MainColumn/HeaderRow/TitleColumn/HeroNameInput
@onready var help_name_button: Button = $RootMargin/MainColumn/HeaderRow/HelpNameButton
@onready var random_look_button: Button = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/RandomLookButton
@onready var hand_style_grid: GridContainer = $RootMargin/MainColumn/CreatorBody/ChoicePanel/Margin/Scroll/Content/HandStyleGrid
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
@onready var reset_button: Button = $RootMargin/MainColumn/CreatorBody/PreviewPanel/AnimationControls/ResetButton
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
var _save_stars: Label
var _saved_celebration := false


func _ready() -> void:
    back_button.pressed.connect(_on_back_pressed)
    save_button.pressed.connect(_on_save_pressed)
    play_button.pressed.connect(_on_play_pressed)
    hero_name_input.text_changed.connect(_on_hero_name_changed)
    help_name_button.pressed.connect(_on_help_name_pressed)
    random_look_button.pressed.connect(_on_random_look_pressed)
    for button_name in HAND_STYLES:
        var button := hand_style_grid.get_node(button_name) as Button
        button.pressed.connect(_on_hand_style_pressed.bind(String(HAND_STYLES[button_name])))
    bridge.request_succeeded.connect(_on_bridge_success)
    bridge.request_failed.connect(_on_bridge_failure)
    _wire_look_controls()
    _wire_animation_controls()
    _wire_outfit_controls()
    _build_save_celebration()

    _draft_appearance = avatar_stage.current_appearance()
    _refresh_look_controls()

    _read_user_args()
    # The browser origin includes the family's custom HTTPS port.
    var browser_origin := ""
    if OS.has_feature("web"):
        browser_origin = MiniUtopiaBridgeEndpointPolicy.normalize(
            String(JavaScriptBridge.eval("window.location.origin", true)), true
        )
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family != null and family.has_family_connection():
        if character_id.is_empty() and not family.pending_character_id.is_empty():
            character_id = family.pending_character_id
        if not family.bind_family_client(bridge):
            _set_status("请家长到「我的角色」帮忙解锁。", true)
            save_button.disabled = true
            return
        if not browser_origin.is_empty() and bridge.base_url != browser_origin:
            # Never send the child session to a different browser origin.
            bridge.clear_family_session()
            _set_status("请家长从当前家庭页面重新解锁。", true)
            save_button.disabled = true
            return
    _set_status("准备好了，开始做你的小英雄吧！", false)

    if character_id.is_empty():
        character_label.text = "新英雄"
        _set_status(
            "给英雄起个名字，就可以保存！"
            if bridge.has_family_session()
            else "请家长先帮你解锁，才能保存英雄。",
            false
        )
        save_button.disabled = not (
            bridge.has_family_session()
            and not hero_name_input.text.strip_edges().is_empty()
        )
        return

    character_label.text = "正在打开角色…"
    save_button.disabled = true
    var error := bridge.get_character(character_id)
    if error != OK:
        if error == ERR_UNCONFIGURED and OS.has_feature("web"):
            _set_status("请家长先帮你解锁，暂时只能预览。", true)
        else:
            _set_status("英雄暂时打不开，请再试一次。", true)


# Visual-only celebration; Play still requires the same server-verified
# owner-scoped outfit runtime as before.
func _build_save_celebration() -> void:
    var preview := avatar_stage.get_parent() as Control
    _save_stars = Label.new()
    _save_stars.name = "SavedStars"
    _save_stars.text = "✨ ⭐ 🌟 ✨\n🎉 保存成功啦！ 🎉"
    _save_stars.set_anchors_preset(Control.PRESET_TOP_WIDE)
    _save_stars.offset_left = 15
    _save_stars.offset_right = -15
    _save_stars.offset_top = 24
    _save_stars.offset_bottom = 124
    _save_stars.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    _save_stars.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
    _save_stars.mouse_filter = Control.MOUSE_FILTER_IGNORE
    preview.add_child(_save_stars)
    _save_stars.hide()


func _celebrate_saved_hero() -> void:
    _saved_celebration = true
    _save_stars.show()
    _save_stars.pivot_offset = _save_stars.size / 2.0
    _save_stars.scale = Vector2(0.65, 0.65)
    avatar_stage.play_preview_animation("Jump")
    var tween := create_tween()
    tween.tween_property(_save_stars, "scale", Vector2(1.14, 1.14), 0.35)
    tween.tween_property(_save_stars, "scale", Vector2.ONE, 0.25)
    tween.tween_interval(0.55)
    tween.tween_callback(func() -> void:
        if is_instance_valid(avatar_stage):
            avatar_stage.play_preview_animation("Idle")
    )
    _show_saved_village_button()


func _show_saved_village_button() -> void:
    if not _saved_celebration:
        return
    play_button.text = "🌳 去村子玩！"
    play_button.custom_minimum_size = Vector2(275, 72)
    play_button.show()


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
        heading.text = "给英雄换装"
        hint.text = "选一件试穿，喜欢就保存！"
        _refresh_outfit_choices()
    else:
        heading.text = "创建小英雄"
        hint.text = "眼睛、发型等暂未开放"
        _hide_unavailable_knight_choices()
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
        help.text = "先保存英雄，就能打开你的衣柜啦！"
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
        heading.text = String(SLOT_LABELS.get(slot, "其他装备"))
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
                ("已穿上 · " if picked else "穿上 · ")
                + String(item.get("display_name", "我的装备"))
            )
            choice.disabled = picked
            choice.pressed.connect(
                _on_equipment_choice_pressed.bind(slot, item_id)
            )
            _outfit_choices.add_child(choice)

        if currently_equipped:
            var remove := Button.new()
            remove.name = "Remove_" + slot
            remove.text = "脱下"
            remove.custom_minimum_size = Vector2(0.0, 48.0)
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
    heading.text = "制作我的道具"
    heading.add_theme_font_size_override("font_size", 21)
    section.add_child(heading)

    _craft_name_input = LineEdit.new()
    _craft_name_input.name = "MyPropName"
    _craft_name_input.placeholder_text = "给道具起个名字"
    _craft_name_input.max_length = 32
    _craft_name_input.custom_minimum_size.y = 48
    section.add_child(_craft_name_input)

    var shape_option := OptionButton.new()
    shape_option.name = "PropShape"
    shape_option.custom_minimum_size.y = 48
    for label in ["星星", "爱心", "圆球", "方块"]:
        shape_option.add_item(label)
    shape_option.selected = ["star", "heart", "sphere", "box"].find(_craft_shape)
    shape_option.item_selected.connect(_on_craft_shape_selected)
    section.add_child(shape_option)

    var color_option := OptionButton.new()
    color_option.name = "PropColor"
    color_option.custom_minimum_size.y = 48
    for label in ["粉色", "薄荷绿", "天蓝", "金色", "紫色"]:
        color_option.add_item(label)
    var colors := ["#F7B7D2", "#B9E7D0", "#74B9FF", "#F2C75C", "#B79CED"]
    color_option.selected = maxi(0, colors.find(_craft_color))
    color_option.item_selected.connect(_on_craft_color_selected)
    section.add_child(color_option)

    var slot_option := OptionButton.new()
    slot_option.name = "PropSlot"
    slot_option.custom_minimum_size.y = 48
    for label in ["小饰品", "头饰", "手持道具", "背包"]:
        slot_option.add_item(label)
    slot_option.selected = maxi(
        0, ["accessory", "headwear", "weapon_main", "backpack"].find(_craft_slot)
    )
    slot_option.item_selected.connect(_on_craft_slot_selected)
    section.add_child(slot_option)

    var submit := Button.new()
    submit.name = "CreatePropButton"
    submit.text = "保存我的道具"
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
        _set_status("先请家长解锁并保存英雄，才能做道具。", true)
        return
    if _craft_name_input == null:
        return
    var name := _craft_name_input.text.strip_edges()
    if name.is_empty():
        _set_status("先给道具起个名字吧！", true)
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
        _set_status("正在保存你的道具…", false)
    else:
        _set_status("道具没保存成功，再试一次吧。", true)


func _on_equipment_choice_pressed(slot: String, item_id: String) -> void:
    if character_id.is_empty() or bridge.is_busy():
        _set_status("先完成这次换装吧！", true)
        return
    var id: Variant = null if item_id.is_empty() else item_id
    var error := bridge.put_equipment_slot(character_id, slot, id)
    if error == OK:
        _set_status("正在换装…", false)
    else:
        _set_status("换装没成功，再试一次吧。", true)


func activate_family_session(token: String, api_base_url: String) -> bool:
    # Explicit session activation is allowed only in memory; a parent-managed
    # token issuer must replace raw token entry before public deployment.
    var family := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null or not family.connect_family(api_base_url, token):
        save_button.disabled = true
        _set_status("请家长先帮你解锁，才能保存英雄。", true)
        return false
    if not family.bind_family_client(bridge):
        save_button.disabled = true
        _set_status("请家长先帮你解锁，才能保存英雄。", true)
        return false

    if character_id.is_empty():
        _on_hero_name_changed(hero_name_input.text)
        _set_status("已解锁！给英雄起名，然后点保存。", false)
    else:
        save_button.disabled = true
        var error := bridge.get_character(character_id)
        if error != OK:
            _set_status("英雄暂时打不开，请再试一次。", true)
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
        if not has_name:
            _set_status("先给英雄起个名字吧！", false)
        elif not bridge.has_family_session():
            _set_status("名字起好了！请家长帮你解锁。", false)
        else:
            _set_status("名字起好了！点「保存英雄」吧。", false)
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
    color_target_option.add_item("外观颜色")
    color_target_option.add_item("眼睛颜色")
    color_target_option.add_item("头发颜色")
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
    _set_status("看！英雄正在" + String(ANIMATION_LABELS.get(animation_name, animation_name)) + "！", false)


func _refresh_animation_buttons() -> void:
    var current := avatar_stage.current_preview_animation()
    for button_name in ANIMATION_BUTTONS:
        var button := animation_controls.get_node(button_name) as Button
        button.button_pressed = (
            String(ANIMATION_BUTTONS[button_name]) == current
        )


func _on_help_name_pressed() -> void:
    hero_name_input.text = String(FRIENDLY_NAMES.pick_random())
    _on_hero_name_changed(hero_name_input.text)


func _on_random_look_pressed() -> void:
    # The official Knight has no interchangeable species/head/eyes/hair meshes.
    # Randomize only a body width the child can actually see, and always choose
    # a different width. Preserve legacy saved identity and all other IDs.
    var choices := MiniUtopiaCreatorAvatarCatalog.BODY_OPTIONS.keys()
    choices.erase(String(_draft_appearance.get("body_type", "standard")))
    _draft_appearance["body_type"] = String(choices.pick_random())
    _commit_live_appearance("🎲 体型换好啦！喜欢就保存吧。")


func _on_hand_style_pressed(style: String) -> void:
    if not MiniUtopiaKaykitAvatarV1.WEAPONS.has(style):
        return
    var slot := "weapon_offhand" if style == "shield_round" else "weapon_main"
    var items = equipment_state.get("items", [])
    if typeof(items) != TYPE_ARRAY or character_id.is_empty() or bridge.is_busy():
        _set_status("先保存你的英雄，再来选手持道具吧！", false)
        return
    # Four CC0 models, but never invent inventory: staff/wand are skins
    # of the child's genuinely owned starter main-hand weapon.
    for raw in items:
        if typeof(raw) != TYPE_DICTIONARY:
            continue
        var item: Dictionary = raw
        if String(item.get("slot", "")) != slot:
            continue
        var item_id := String(item.get("item_instance_id", ""))
        if item_id.is_empty():
            continue
        var tags: Array = _draft_appearance.get("compatible_tags", ["humanoid"])
        tags = tags.filter(func(tag): return not String(tag).begins_with("kaykit_style_"))
        tags.append("kaykit_style_" + style)
        _draft_appearance["compatible_tags"] = tags
        _commit_live_appearance("✨ 装备外观已选择，记得保存！")
        _on_equipment_choice_pressed(slot, item_id)
        return
    _set_status("这件道具还不在你的衣柜里。", true)


func _on_body_selected(body_type: String) -> void:
    _draft_appearance["body_type"] = body_type
    _commit_live_appearance("体型换好啦！")


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

    _commit_live_appearance("造型换好啦！")


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
    _commit_live_appearance("质感换好啦！")


func _on_eye_style_selected(index: int) -> void:
    if index < 0 or index >= _eye_option_ids.size():
        return
    _draft_appearance["eye_style_id"] = _eye_option_ids[index]
    _commit_live_appearance("眼睛换好啦！")


func _on_hair_style_selected(index: int) -> void:
    if index < 0 or index >= _hair_option_ids.size():
        return
    _draft_appearance["hair_style_id"] = _hair_option_ids[index]
    _commit_live_appearance("发型换好啦！")


func _on_color_target_selected(_index: int) -> void:
    _refresh_color_buttons()


func _on_color_selected(hex_value: String) -> void:
    _draft_appearance[_active_color_field()] = hex_value
    _commit_live_appearance("颜色换好啦！")


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
        _set_status(message + " 还没保存哦。", false)
    else:
        _set_status(message + " 喜欢就点「保存英雄」吧。", false)


func _sync_loaded_profile_avatar() -> void:
    if loaded_character.is_empty():
        return
    var profile = loaded_character.get("profile", {})
    if typeof(profile) != TYPE_DICTIONARY:
        return
    profile["avatar"] = _draft_appearance.duplicate(true)
    loaded_character["profile"] = profile


# Only the official Knight is packaged. The legacy eye/hair/surface
# meshes live beneath Visual, which KaykitAvatarV1 hides in favor of the
# original rig. Do not let children tap a control that has no visible result.
# Keep all canonical IDs and old saved appearances unchanged.
func _hide_unavailable_knight_choices() -> void:
    for node_name in [
        "SurfaceLabel", "SurfaceGrid",
        "EyeLabel", "EyeStyleOption", "HairLabel", "HairStyleOption",
        "ColorLabel", "ColorTargetOption", "ColorGrid",
    ]:
        var control := choice_content.get_node_or_null(node_name) as Control
        if control != null:
            control.visible = false


func _refresh_look_controls() -> void:
    _hide_unavailable_knight_choices()
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
        # Only the bundled official Knight has a matching full head mesh.
        # Keep older choices in the canonical data contract for existing
        # saves, but don't present unsupported species as playable models.
        button.visible = String(SPECIES_BUTTONS[button_name]) == "species_head_human_v1"
        button.button_pressed = button.visible

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
        eye_style_option.add_item(String(EYE_LABELS.get(option_id, "眼睛")))
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
        hair_style_option.add_item(String(HAIR_LABELS.get(option_id, "发型")))
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
            _set_status("道具还没准备好，请再试一次。", true)
            return
        equipment_state = owned.duplicate(true)
        _refresh_outfit_choices()
        var runtime = equipment_state.get("runtime", {})
        if typeof(runtime) == TYPE_DICTIONARY:
            avatar_stage.apply_equipment_runtime(runtime)
        _set_status("道具保存成功！点「穿上」试试吧。", false)
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
        _set_status("英雄回来啦，正在打开衣柜…", false)
        var equipment_error := bridge.get_equipment(character_id)
        if equipment_error != OK:
            _set_status(
                "衣柜暂时打不开，请再试一次。",
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
            "英雄和衣柜都准备好啦！"
            if valid else "衣柜还没准备好，请再试一次。",
            not valid
        )
        _show_saved_village_button()
        return

    if kind == "character:post":
        loaded_character = payload.duplicate(true)
        _appearance_dirty = false
        character_id = String(payload.get("character_id", ""))
        character_label.text = String(payload.get("display_name", "新英雄"))
        hero_name_input.text = character_label.text
        save_button.disabled = character_id.is_empty()
        play_button.disabled = true
        equipment_state.clear()
        _celebrate_saved_hero()
        _set_status("英雄保存成功！正在准备衣柜…", false)
        if not character_id.is_empty():
            var equipment_error := bridge.get_equipment(character_id)
            if equipment_error != OK:
                _set_status("英雄已保存，衣柜还没准备好。", true)
        return

    if kind == "character:put":
        loaded_character = payload.duplicate(true)
        _appearance_dirty = false
        save_button.disabled = false
        # The previous gate only checked whether the equipment dict was
        # non-empty. A stale/foreign child's cached wardrobe could therefore
        # enable Play even though select_equipment() would reject it. Require
        # the *same* verified owner-scoped runtime as equipment:get.
        var saved_runtime = equipment_state.get("runtime", {})
        var owned_equipment := (
            typeof(saved_runtime) == TYPE_DICTIONARY
            and String(saved_runtime.get("character_asset_id", "")) == character_id
            and typeof(saved_runtime.get("equipped", null)) == TYPE_DICTIONARY
            and typeof(saved_runtime.get("final_stats", null)) == TYPE_DICTIONARY
        )
        play_button.disabled = not owned_equipment
        _celebrate_saved_hero()
        _set_status(
            "保存成功啦！去村子玩吧！"
            if owned_equipment
            else "英雄已保存，请先打开衣柜再去玩。",
            false
        )


func _on_bridge_failure(
    kind: String,
    status_code: int,
    _error_code: String,
    _message: String
) -> void:
    # Only request category and HTTP status are logged; never print secrets,
    # URLs, child names or request payloads.
    push_warning("Creator request failed: %s (HTTP %d)" % [kind, status_code])
    if kind == "prop:craft":
        _set_status("道具没做好，换个名字再试试吧。", true)
        return
    if kind.begins_with("equipment:"):
        play_button.disabled = true
        _set_status("装扮暂时没打开，请稍后重试。", true)
        return

    save_button.disabled = true

    if kind == "character:get":
        if status_code == 404:
            _set_status(
                "找不到这个英雄啦，返回再选一个吧。",
                true
            )
        else:
            var help := (
                " Family Cloud is unavailable."
                if OS.has_feature("web")
                else " Start the Mini Utopia Bridge and try again."
            )
            _set_status("角色暂时没打开，请返回重试。", true)
        return

    if kind == "character:post":
        save_button.disabled = false
        _set_status("角色还没保存成功，请重试。", true)
        return

    if kind == "character:put":
        if status_code == 409:
            _set_status(
                "英雄刚刚有了新变化，请重新打开再保存。",
                true
            )
        else:
            _set_status("保存没有成功，请再试一次。", true)


func _on_play_pressed() -> void:
    if play_button.disabled or loaded_character.is_empty():
        _set_status("先保存英雄，再去村子玩吧！", true)
        return
    var family_state := get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState
    if family_state == null or not family_state.select_character(loaded_character):
        _set_status("英雄暂时进不了村子，请再试一次。", true)
        return
    var runtime = equipment_state.get("runtime", {})
    if (
        typeof(runtime) != TYPE_DICTIONARY
        or not family_state.select_equipment(runtime)
    ):
        family_state.clear_selection()
        _set_status("衣服和道具还没准备好，请稍后再试。", true)
        return
    var target := "res://scenes/main.tscn"
    if not ResourceLoader.exists(target):
        _set_status("村子暂时打不开，请稍后再试。", true)
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
        _set_status("先给英雄起个名字吧！", true)
        return

    if character_id.is_empty():
        if not bridge.has_family_session():
            _set_status("请家长先帮你解锁，才能保存。", true)
            return
        save_button.disabled = true
        _set_status("正在创建小英雄…", false)
        var create_error := bridge.create_character({
            "schema_version": "1.0",
            "display_name": name,
            "description": "",
            "profile": {"avatar": _draft_appearance.duplicate(true)},
        })
        if create_error != OK:
            save_button.disabled = false
            _set_status("创建没成功，再试一次吧。", true)
        return

    if loaded_character.is_empty():
        _set_status("请先打开英雄，再保存修改。", true)
        return

    save_button.disabled = true
    _set_status("正在保存英雄…", false)

    var error := bridge.put_character(
        character_id, _character_update_payload(name)
    )
    if error != OK:
        save_button.disabled = false
        _set_status("保存没开始成功，请再试一次。", true)

## Keep the server-owned Character identity and revision, but persist the
## child's CURRENT avatar choices rather than resending the old profile.
func _character_update_payload(name: String) -> Dictionary:
    var profile: Dictionary = loaded_character.get("profile", {}).duplicate(true)
    profile["avatar"] = _draft_appearance.duplicate(true)
    return {
        "schema_version": String(loaded_character.get("schema_version", "1.0")),
        "revision": String(loaded_character.get("revision", "")),
        "display_name": name,
        "description": String(loaded_character.get("description", "")),
        "profile": profile,
    }


func _set_status(message: String, is_error: bool) -> void:
    # All Creator messages are child-facing; never render backend details or
    # a raw failed-request body (which could include technical identifiers).
    var safe_message := message
    var lower := message.to_lower()
    for hidden_word in [
        "url", "token", "secret", "session", "bridge",
        "family cloud", "https://", "http://", "localhost", "backend", "server",
    ]:
        if lower.contains(hidden_word):
            safe_message = (
                "暂时没成功，再试一次吧。"
                if bridge.has_family_session()
                else "请家长打开「我的角色」里的「家长入口」帮忙。"
            )
            break
    status_label.text = ("💡 " if is_error else "") + safe_message

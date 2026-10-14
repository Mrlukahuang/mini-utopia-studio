class_name MiniUtopiaFamilyHeroLibrary
extends Control

## My Heroes / 我的角色 — accessible in-game on Mac and iPad.
## A parent may supply a private HTTPS endpoint + scoped token in this session
## only. No child name, token, or credentials are written to local storage.
## The production parent sign-in/short-lived token issuer is a separate step.

var bridge: MiniUtopiaBridgeClient
var status_label: Label
var hero_list: VBoxContainer
var connection_panel: VBoxContainer
var api_input: LineEdit
var token_input: LineEdit
var profile_choice: OptionButton
var _pending_profile_id := ""
var connect_button: Button
var new_button: Button
var refresh_button: Button
var logout_button: Button


func _ready() -> void:
    bridge = MiniUtopiaBridgeClient.new()
    bridge.name = "FamilyBridgeClient"
    add_child(bridge)
    bridge.request_succeeded.connect(_on_bridge_success)
    bridge.request_failed.connect(_on_bridge_failure)

    _build_ui()
    var family := _family_state()
    if family != null and family.bind_family_client(bridge):
        _set_connected(true)
        _refresh_characters()
    else:
        _set_connected(false)
        _set_status("Parent: connect your private Family Cloud to load saved Heroes.", false)


func _family_state() -> MiniUtopiaFamilySceneState:
    return get_node_or_null("/root/FamilySceneState") as MiniUtopiaFamilySceneState


func _build_ui() -> void:
    var background := ColorRect.new()
    background.name = "Background"
    background.color = Color("#F8F2FC")
    background.set_anchors_preset(Control.PRESET_FULL_RECT)
    add_child(background)

    var margin := MarginContainer.new()
    margin.name = "Margin"
    margin.set_anchors_preset(Control.PRESET_FULL_RECT)
    for side in ["left", "top", "right", "bottom"]:
        margin.add_theme_constant_override("margin_" + side, 24)
    add_child(margin)

    var column := VBoxContainer.new()
    column.name = "Column"
    column.add_theme_constant_override("separation", 12)
    margin.add_child(column)

    var title := Label.new()
    title.text = "✨ My Heroes / 我的角色"
    title.add_theme_font_size_override("font_size", 30)
    column.add_child(title)

    var subtitle := Label.new()
    subtitle.text = "Choose one to dress, play, or film. Every hero stays yours."
    subtitle.add_theme_font_size_override("font_size", 17)
    column.add_child(subtitle)

    var toolbar := HBoxContainer.new()
    toolbar.name = "Toolbar"
    toolbar.add_theme_constant_override("separation", 10)
    column.add_child(toolbar)

    new_button = Button.new()
    new_button.name = "NewHeroButton"
    new_button.text = "＋ New Hero"
    new_button.custom_minimum_size = Vector2(170, 52)
    new_button.pressed.connect(_on_new_pressed)
    toolbar.add_child(new_button)

    refresh_button = Button.new()
    refresh_button.name = "RefreshButton"
    refresh_button.text = "↻ Refresh"
    refresh_button.custom_minimum_size = Vector2(150, 52)
    refresh_button.pressed.connect(_refresh_characters)
    toolbar.add_child(refresh_button)

    var back := Button.new()
    back.name = "BackButton"
    back.text = "← Village"
    back.custom_minimum_size = Vector2(158, 52)
    back.pressed.connect(_on_back_pressed)
    toolbar.add_child(back)

    logout_button = Button.new()
    logout_button.name = "DisconnectButton"
    logout_button.text = "Parent: Disconnect"
    logout_button.custom_minimum_size = Vector2(210, 52)
    logout_button.pressed.connect(_on_disconnect_pressed)
    toolbar.add_child(logout_button)

    connection_panel = VBoxContainer.new()
    connection_panel.name = "ParentConnection"
    connection_panel.add_theme_constant_override("separation", 8)
    column.add_child(connection_panel)

    var hint := Label.new()
    hint.text = "Parent unlock · Private HTTPS Family Cloud (30-minute session)"
    connection_panel.add_child(hint)

    profile_choice = OptionButton.new()
    profile_choice.name = "ChildProfile"
    profile_choice.custom_minimum_size.y = 48
    profile_choice.add_item("Child A / 大宝", 0)
    profile_choice.add_item("Child B / 二宝", 1)
    connection_panel.add_child(profile_choice)

    api_input = LineEdit.new()
    api_input.name = "ApiUrl"
    api_input.placeholder_text = "https://your-private-family-api.example"
    api_input.custom_minimum_size.y = 48
    api_input.max_length = 256
    connection_panel.add_child(api_input)

    token_input = LineEdit.new()
    token_input.name = "SecretToken"
    token_input.placeholder_text = "Parent-only unlock secret (not the child's token)"
    token_input.secret = true
    token_input.custom_minimum_size.y = 48
    token_input.max_length = 256
    connection_panel.add_child(token_input)

    connect_button = Button.new()
    connect_button.name = "ConnectButton"
    connect_button.text = "Parent: Unlock a 30-minute child session"
    connect_button.custom_minimum_size.y = 52
    connect_button.pressed.connect(_on_connect_pressed)
    connection_panel.add_child(connect_button)

    status_label = Label.new()
    status_label.name = "LibraryStatus"
    status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    status_label.add_theme_font_size_override("font_size", 17)
    column.add_child(status_label)

    var scroll := ScrollContainer.new()
    scroll.name = "HeroScroll"
    scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
    column.add_child(scroll)

    hero_list = VBoxContainer.new()
    hero_list.name = "HeroList"
    hero_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    hero_list.add_theme_constant_override("separation", 12)
    scroll.add_child(hero_list)


func _set_connected(connected: bool) -> void:
    connection_panel.visible = not connected
    logout_button.disabled = not connected
    refresh_button.disabled = not connected
    new_button.disabled = not connected


func _on_connect_pressed() -> void:
    if bridge.is_busy():
        _set_status("A Hero request is still loading. Please retry.", true)
        return
    var family := _family_state()
    if family == null:
        _set_status("Family session is not available.", true)
        return
    var url := api_input.text.strip_edges()
    var parent_secret := token_input.text.strip_edges()
    # Erase masked widget text immediately, even if the network fails.
    token_input.clear()
    bridge.configure(url)
    if not bridge.base_url.begins_with("https://"):
        _set_status("A private HTTPS Family Cloud URL is required.", true)
        return

    _pending_profile_id = (
        "child_b" if profile_choice.get_selected_id() == 1 else "child_a"
    )
    var error := bridge.request_parent_approved_session(
        _pending_profile_id, parent_secret
    )
    # The parent secret goes only to this one HTTPS request and never to the
    # persistent in-memory FamilySceneState, project files, logs or URLs.
    parent_secret = ""
    if error != OK:
        _pending_profile_id = ""
        _set_status("Parent unlock could not start. Check URL and secret.", true)
        return
    connect_button.disabled = true
    _set_status("Parent approval requested securely…", false)


func _refresh_characters() -> void:
    if not bridge.has_family_session():
        _set_connected(false)
        _set_status("Parent connection required to see saved Heroes.", true)
        return
    if bridge.is_busy():
        return
    _set_status("Loading your saved Heroes…", false)
    var error := bridge.list_characters()
    if error != OK:
        _set_status("Could not start loading Heroes.", true)


func _on_bridge_success(kind: String, payload: Dictionary) -> void:
    if kind == "family:session":
        connect_button.disabled = false
        var family := _family_state()
        var issued_token := String(payload.get("access_token", ""))
        var expires := int(payload.get("expires_in_seconds", 0))
        var profile := String(payload.get("profile_id", ""))
        var valid := (
            family != null
            and String(payload.get("schema_version", "")) == "1.0"
            and profile == _pending_profile_id
            and expires > 0
            and expires <= 1800
            and family.connect_family(bridge.base_url, issued_token)
        )
        issued_token = ""
        _pending_profile_id = ""
        if not valid or not family.bind_family_client(bridge):
            if family != null:
                family.disconnect_family()
            bridge.clear_family_session()
            _set_connected(false)
            _set_status("Parent approval failed. Please try again.", true)
            return
        api_input.clear()
        _set_connected(true)
        _refresh_characters()
        return

    if kind != "characters:list" or not bridge.has_family_session():
        return
    var raw = payload.get("characters", [])
    if String(payload.get("schema_version", "")) != "1.0" or typeof(raw) != TYPE_ARRAY:
        _set_status("Family Cloud returned an unsupported Hero list.", true)
        return

    _clear_hero_list()
    var heroes: Array[Dictionary] = []
    for entry in raw:
        if typeof(entry) != TYPE_DICTIONARY:
            continue
        var character: Dictionary = entry
        var id := String(character.get("character_id", ""))
        if not id.begins_with("CHAR_"):
            continue
        heroes.append(character)
    heroes.sort_custom(func(a, b):
        return String(a.get("display_name", "")).nocasecmp_to(
            String(b.get("display_name", ""))
        ) < 0
    )
    for hero in heroes:
        var character_id := String(hero.get("character_id", ""))
        var name := String(hero.get("display_name", "My Hero"))
        var button := Button.new()
        button.name = "Hero_" + character_id
        button.text = "✦ " + name + "     ✎ Edit / Dress"
        button.custom_minimum_size.y = 64
        button.add_theme_font_size_override("font_size", 21)
        button.pressed.connect(_on_hero_pressed.bind(character_id))
        hero_list.add_child(button)

    var message := (
        "No saved Heroes yet. Tap ＋ New Hero to create one!"
        if heroes.is_empty()
        else str(heroes.size()) + " saved Hero(es) · tap one to edit."
    )
    _set_status(message, false)


func _clear_hero_list() -> void:
    for child in hero_list.get_children():
        hero_list.remove_child(child)
        child.queue_free()


func _on_bridge_failure(kind: String, status_code: int, _code: String, _message: String) -> void:
    if kind == "family:session":
        connect_button.disabled = false
        _pending_profile_id = ""
        _set_connected(false)
        _set_status(
            "Parent unlock temporarily limited. Try again later."
            if status_code == 429
            else "Parent unlock denied. Check the private URL and secret.",
            true
        )
        return

    if kind != "characters:list":
        return
    if status_code in [401, 403]:
        var family := _family_state()
        if family != null:
            family.disconnect_family()
        bridge.clear_family_session()
        _clear_hero_list()
        _set_connected(false)
        _set_status("Parent: this session is not authorized. Please reconnect.", true)
        return
    _set_status("Could not load your Heroes. Check the private connection.", true)


func _on_hero_pressed(character_id: String) -> void:
    var family := _family_state()
    if family == null or not family.open_character(character_id):
        _set_status("Parent connection required before opening your Hero.", true)
        return
    get_tree().change_scene_to_file("res://scenes/character_creator.tscn")


func _on_new_pressed() -> void:
    var family := _family_state()
    if family == null or not family.has_family_connection():
        _set_status("Parent connection required before creating a Hero.", true)
        return
    family.start_new_character()
    get_tree().change_scene_to_file("res://scenes/character_creator.tscn")


func _on_disconnect_pressed() -> void:
    # Proactively revoke the short-lived server token when safe to do so;
    # local disconnect ALWAYS clears memory even if offline or busy.
    if bridge.has_family_session() and not bridge.is_busy():
        bridge.revoke_family_session()
    var family := _family_state()
    if family != null:
        family.disconnect_family()
    bridge.clear_family_session()
    _clear_hero_list()
    _set_connected(false)
    _set_status("Disconnected · your Heroes remain safe in your private account.", false)


func _on_back_pressed() -> void:
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    get_tree().change_scene_to_file("res://scenes/main.tscn")


func _set_status(message: String, error: bool) -> void:
    status_label.text = message
    status_label.modulate = Color("#B5485D") if error else Color("#4F4868")

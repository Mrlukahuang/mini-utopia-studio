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
var shoot_button: Button
var _pending_cast_character_id := ""
var _pending_guest_grant_id := ""
var _share_character_id := ""
var _active_grant_id := ""
var _last_shared_character_id := ""
var adult_share_panel: VBoxContainer
var share_secret_input: LineEdit
var share_submit: Button
var share_revoke: Button
var guests_refresh_button: Button
var movies_button: Button
var movie_list: VBoxContainer
var _movie_restore: Dictionary = {}
var _movie_phase := ""
var _movie_cast_id := ""


func _ready() -> void:
    bridge = MiniUtopiaBridgeClient.new()
    bridge.name = "FamilyBridgeClient"
    add_child(bridge)
    bridge.request_succeeded.connect(_on_bridge_success)
    bridge.request_failed.connect(_on_bridge_failure)

    _build_ui()
    if OS.has_feature("web"):
        # On the approved single-origin family host, no child/parent should
        # have to manually type a backend address. The URL is taken only from
        # the browser's own origin and still passes HTTPS-only validation.
        var browser_origin := String(JavaScriptBridge.eval(
            "window.location.origin", true
        ))
        var safe_origin := MiniUtopiaBridgeEndpointPolicy.normalize(
            browser_origin, true
        )
        if not safe_origin.is_empty():
            api_input.text = safe_origin
            api_input.editable = false
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

    guests_refresh_button = Button.new()
    guests_refresh_button.name = "RefreshParentApprovedGuests"
    guests_refresh_button.text = "🎬 Find parent-approved guest actors"
    guests_refresh_button.custom_minimum_size.y = 52
    guests_refresh_button.disabled = true
    guests_refresh_button.pressed.connect(_refresh_approved_guests)
    column.add_child(guests_refresh_button)

    new_button = Button.new()
    new_button.name = "NewHeroButton"
    new_button.text = "＋ New Hero"
    new_button.custom_minimum_size = Vector2(170, 52)
    new_button.pressed.connect(_on_new_pressed)
    toolbar.add_child(new_button)

    shoot_button = Button.new()
    shoot_button.name = "ShootWithCastButton"
    shoot_button.text = "🎬 Film Together"
    shoot_button.custom_minimum_size = Vector2(200, 52)
    shoot_button.disabled = true
    shoot_button.pressed.connect(_on_shoot_together_pressed)
    toolbar.add_child(shoot_button)

    refresh_button = Button.new()
    refresh_button.name = "RefreshButton"
    refresh_button.text = "↻ Refresh"
    refresh_button.custom_minimum_size = Vector2(150, 52)
    refresh_button.pressed.connect(_refresh_characters)
    toolbar.add_child(refresh_button)

    movies_button = Button.new()
    movies_button.name = "MyMoviesButton"
    movies_button.text = "🎞 My Movies / 我的电影"
    movies_button.custom_minimum_size = Vector2(190, 52)
    movies_button.pressed.connect(_refresh_films)
    toolbar.add_child(movies_button)

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

    adult_share_panel = VBoxContainer.new()
    adult_share_panel.name = "ParentFilmConsent"
    adult_share_panel.visible = false
    adult_share_panel.add_theme_constant_override("separation", 8)
    column.add_child(adult_share_panel)

    var consent_text := Label.new()
    consent_text.name = "ConsentMessage"
    consent_text.text = "Parent approval · share this actor with sibling for 15 minutes"
    consent_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    adult_share_panel.add_child(consent_text)

    share_secret_input = LineEdit.new()
    share_secret_input.name = "ParentConsentSecret"
    share_secret_input.secret = true
    share_secret_input.max_length = 256
    share_secret_input.custom_minimum_size.y = 48
    share_secret_input.placeholder_text = "Parent-only unlock (one time)"
    adult_share_panel.add_child(share_secret_input)

    share_submit = Button.new()
    share_submit.name = "ApproveShareButton"
    share_submit.text = "Parent: Approve 15-minute guest role"
    share_submit.custom_minimum_size.y = 52
    share_submit.pressed.connect(_on_parent_share_submit)
    adult_share_panel.add_child(share_submit)

    share_revoke = Button.new()
    share_revoke.name = "RevokeShareButton"
    share_revoke.text = "Parent: Revoke this guest permission"
    share_revoke.custom_minimum_size.y = 52
    share_revoke.visible = false
    share_revoke.pressed.connect(_on_parent_revoke_submit)
    adult_share_panel.add_child(share_revoke)

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
    var list_stack := VBoxContainer.new()
    list_stack.name = "LibraryListStack"
    list_stack.add_theme_constant_override("separation", 16)
    scroll.add_child(list_stack)
    list_stack.add_child(hero_list)

    movie_list = VBoxContainer.new()
    movie_list.name = "MovieList"
    movie_list.add_theme_constant_override("separation", 10)
    list_stack.add_child(movie_list)


func _set_connected(connected: bool) -> void:
    connection_panel.visible = not connected
    logout_button.disabled = not connected
    refresh_button.disabled = not connected
    new_button.disabled = not connected
    guests_refresh_button.disabled = not connected
    movies_button.disabled = not connected
    if not connected:
        _cancel_movie_restore()
        _clear_movie_list()
        shoot_button.disabled = true
        adult_share_panel.visible = false
        share_secret_input.clear()
        _share_character_id = ""
        _active_grant_id = ""
        _last_shared_character_id = ""
        _pending_guest_grant_id = ""
        _pending_cast_character_id = ""
    else:
        _refresh_cast_button()


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


func _clear_movie_list() -> void:
    if movie_list == null:
        return
    for child in movie_list.get_children():
        movie_list.remove_child(child)
        child.queue_free()


func _cancel_movie_restore() -> void:
    _movie_restore.clear()
    _movie_phase = ""
    _movie_cast_id = ""


func _refresh_films() -> void:
    if not bridge.has_family_session() or bridge.is_busy():
        _set_status("Unlock your private account to see My Movies.", true)
        return
    if not _movie_phase.is_empty():
        return
    var error := bridge.list_family_films()
    if error != OK:
        _set_status("My Movies could not be loaded.", true)
    else:
        _set_status("Finding your private saved movies…", false)


func _on_saved_movie_pressed(film_id: String) -> void:
    if (
        not bridge.has_family_session()
        or bridge.is_busy()
        or not _movie_phase.is_empty()
        or not film_id.begins_with("FILM_")
        or film_id.contains("/")
    ):
        _set_status("Finish the current request before reopening a movie.", true)
        return
    _cancel_movie_restore()
    _movie_restore["requested_id"] = film_id
    _movie_phase = "film"
    var error := bridge.get_family_film(film_id)
    if error != OK:
        _movie_restore_failed("Could not reopen this private movie.")
        return
    _set_status("Checking saved film and fetching its original cast…", false)


func _movie_restore_failed(message: String) -> void:
    _cancel_movie_restore()
    var family := _family_state()
    if family != null:
        family.clear_selection()
    _refresh_cast_button()
    _set_status(message, true)


func _request_movie_cast(character_id: String, stage: String) -> void:
    if not character_id.begins_with("CHAR_") or "/" in character_id:
        _movie_restore_failed("Saved movie has an invalid actor.")
        return
    _movie_cast_id = character_id
    _movie_phase = stage + "_character"
    if bridge.get_character(character_id) != OK:
        _movie_restore_failed("Could not verify saved film actor.")


func _request_movie_gear(stage: String) -> void:
    _movie_phase = stage + "_equipment"
    if bridge.get_equipment(_movie_cast_id) != OK:
        _movie_restore_failed("Could not fetch actor's own wardrobe.")


func _finish_movie_restore() -> void:
    var family := _family_state()
    if family == null or not family.restore_owned_film(
        _movie_restore.get("record", {})
    ):
        _movie_restore_failed("This saved film no longer has an authorized cast.")
        return
    _cancel_movie_restore()
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    get_tree().change_scene_to_file("res://scenes/director_stage.tscn")


func _consume_movie_restore(kind: String, payload: Dictionary) -> bool:
    if _movie_phase.is_empty():
        return false
    var family := _family_state()
    if family == null or not bridge.has_family_session():
        _movie_restore_failed("Unlock your private child account again.")
        return true

    if _movie_phase == "film" and kind == "films:get":
        var draft = payload.get("draft", {})
        if (
            String(payload.get("film_id", "")) != String(
                _movie_restore.get("requested_id", "")
            )
            or String(payload.get("revision", "")).is_empty()
            or typeof(draft) != TYPE_DICTIONARY
            or not String(draft.get("character_id", "")).begins_with("CHAR_")
        ):
            _movie_restore_failed("Private movie data was not verified.")
            return true
        _movie_restore["record"] = payload.duplicate(true)
        family.clear_selection()
        _request_movie_cast(String(draft["character_id"]), "primary")
        return true

    if kind == "character:get" and _movie_phase in [
        "primary_character", "second_character"
    ]:
        if (
            String(payload.get("character_id", "")) != _movie_cast_id
            or not (
                family.select_character(payload)
                if _movie_phase == "primary_character"
                else family.select_second_cast_character(payload)
            )
        ):
            _movie_restore_failed("Saved actor is missing or not privately owned.")
            return true
        var which := "primary" if _movie_phase == "primary_character" else "second"
        _request_movie_gear(which)
        return true

    if kind == "equipment:get" and _movie_phase in [
        "primary_equipment", "second_equipment"
    ]:
        var gear = payload.get("runtime", {})
        if (
            typeof(gear) != TYPE_DICTIONARY
            or String(gear.get("character_asset_id", "")) != _movie_cast_id
            or not (
                family.select_equipment(gear)
                if _movie_phase == "primary_equipment"
                else family.select_second_cast_equipment(gear)
            )
        ):
            _movie_restore_failed("Actor clothes or props could not be verified.")
            return true
        if _movie_phase == "primary_equipment":
            var draft: Dictionary = _movie_restore["record"]["draft"]
            var raw_second = draft.get("second_character_id", null)
            var second := String(raw_second) if typeof(raw_second) == TYPE_STRING else ""
            if not second.is_empty():
                if second == _movie_cast_id:
                    _movie_restore_failed("Film cannot cast the same actor twice.")
                    return true
                _request_movie_cast(second, "second")
                return true
        _finish_movie_restore()
        return true

    return false


func _on_bridge_success(kind: String, payload: Dictionary) -> void:
    if kind == "films:list":
        _clear_movie_list()
        var films = payload.get("films", [])
        if (
            not bridge.has_family_session()
            or String(payload.get("schema_version", "")) != "1.0"
            or typeof(films) != TYPE_ARRAY
        ):
            _set_status("Private movie list could not be verified.", true)
            return
        var heading := Label.new()
        heading.text = "🎞 My Movies / 我的电影"
        heading.add_theme_font_size_override("font_size", 23)
        movie_list.add_child(heading)
        for entry in films:
            if typeof(entry) != TYPE_DICTIONARY:
                continue
            var id := String(entry.get("film_id", ""))
            var draft = entry.get("draft", {})
            if not id.begins_with("FILM_") or typeof(draft) != TYPE_DICTIONARY:
                continue
            var button := Button.new()
            button.name = "Film_" + id
            button.text = "🎬 " + String(draft.get("display_name", "My Film")) + " · Continue"
            button.custom_minimum_size.y = 62
            button.add_theme_font_size_override("font_size", 18)
            button.pressed.connect(_on_saved_movie_pressed.bind(id))
            movie_list.add_child(button)
        _set_status(str(films.size()) + " private movie(s) saved.", false)
        return
    if _consume_movie_restore(kind, payload):
        return
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
            and family.connect_family(bridge.base_url, issued_token, profile)
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

    if kind in ["family:cast-approve", "family:cast-revoke"]:
        share_submit.disabled = false
        share_revoke.disabled = false
        if kind == "family:cast-approve":
            var grant := String(payload.get("grant_id", ""))
            if not grant.begins_with("CAST_"):
                _set_status("Parent approval response was not valid.", true)
                return
            _active_grant_id = grant
            _last_shared_character_id = _share_character_id
            share_revoke.visible = true
            _set_status("Parent approved this Hero for sibling's film (15 min).", false)
        else:
            _active_grant_id = ""
            _last_shared_character_id = ""
            share_revoke.visible = false
            _set_status("Parent revoked guest filming permission.", false)
        return

    if kind == "castguests:list":
        if not bridge.has_family_session():
            return
        var approved = payload.get("guests", [])
        if typeof(approved) != TYPE_ARRAY:
            _set_status("Approved guest list could not be read.", true)
            return
        for old_button in hero_list.get_children():
            if String(old_button.name).begins_with("Guest_"):
                hero_list.remove_child(old_button)
                old_button.queue_free()
        for raw_guest in approved:
            if typeof(raw_guest) != TYPE_DICTIONARY:
                continue
            var grant_id := String(raw_guest.get("grant_id", ""))
            if not grant_id.begins_with("CAST_"):
                continue
            var guest := Button.new()
            guest.name = "Guest_" + grant_id
            guest.text = (
                "🎬 Parent-approved guest: "
                + String(raw_guest.get("display_name", "Guest Hero"))
            )
            guest.custom_minimum_size.y = 58
            guest.pressed.connect(_on_guest_pressed.bind(grant_id))
            hero_list.add_child(guest)
        _set_status(
            str(approved.size()) + " guest actor permission(s) available.",
            false
        )
        return

    if kind == "castguests:get":
        var family := _family_state()
        if (
            family == null
            or not bridge.has_family_session()
            or _pending_guest_grant_id.is_empty()
            or String(payload.get("grant_id", "")) != _pending_guest_grant_id
        ):
            _pending_guest_grant_id = ""
            return
        _pending_guest_grant_id = ""
        var character = payload.get("character", {})
        var runtime = payload.get("equipment_runtime", {})
        var accepted := (
            typeof(character) == TYPE_DICTIONARY
            and typeof(runtime) == TYPE_DICTIONARY
        )
        if accepted:
            accepted = family.select_second_cast_character(character)
        if accepted:
            accepted = family.select_second_cast_equipment(runtime)
        if not accepted:
            family.clear_second_cast()
            _set_status("Parent guest actor could not be verified.", true)
        else:
            family.second_cast_is_parent_guest = true
            _set_status("Approved guest is ready. Tap Film Together!", false)
        _refresh_cast_button()
        return

    if kind == "character:get" and not _pending_cast_character_id.is_empty():
        var family := _family_state()
        if (
            family == null
            or not bridge.has_family_session()
            or String(payload.get("character_id", "")) != _pending_cast_character_id
            or not family.select_second_cast_character(payload)
        ):
            _reset_cast_request()
            _set_status("That actor isn't available in your private Heroes.", true)
            return
        var equipment_error := bridge.get_equipment(_pending_cast_character_id)
        if equipment_error != OK:
            _reset_cast_request()
            family.clear_second_cast()
            _set_status("Could not load your actor's wardrobe.", true)
        return

    if kind == "equipment:get" and not _pending_cast_character_id.is_empty():
        var family := _family_state()
        var runtime = payload.get("runtime", {})
        if (
            family == null
            or typeof(runtime) != TYPE_DICTIONARY
            or String(runtime.get("character_asset_id", "")) != _pending_cast_character_id
            or not family.select_second_cast_equipment(runtime)
        ):
            if family != null:
                family.clear_second_cast()
            _set_status("Second actor's clothes could not be verified.", true)
        else:
            _set_status("Two saved Heroes are ready. Tap 🎬 Film Together!", false)
        _reset_cast_request()
        _refresh_cast_button()
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

        var family := _family_state()
        if (
            family != null
            and family.has_family_connection()
            and not family.current_profile_id().is_empty()
        ):
            var share := Button.new()
            share.name = "Share_" + character_id
            share.text = "👨‍👩‍👧 Parent: allow " + name + " in sibling's film"
            share.custom_minimum_size.y = 52
            share.pressed.connect(_on_share_candidate.bind(character_id))
            hero_list.add_child(share)

        var primary := (
            String(family.active_character.get("character_id", ""))
            if family != null else ""
        )
        if not primary.is_empty() and character_id != primary:
            var cast_button := Button.new()
            cast_button.name = "Cast_" + character_id
            cast_button.text = "🎬 Invite " + name + " into my film"
            cast_button.custom_minimum_size.y = 58
            cast_button.add_theme_font_size_override("font_size", 18)
            cast_button.pressed.connect(_on_cast_pressed.bind(character_id))
            hero_list.add_child(cast_button)

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
    if kind == "films:list":
        _clear_movie_list()
        _set_status("Your private movies could not be loaded.", true)
        return
    if not _movie_phase.is_empty() and kind in [
        "films:get", "character:get", "equipment:get"
    ]:
        _movie_restore_failed("Saved movie or private actor cannot be reopened.")
        return
    if kind in ["family:cast-approve", "family:cast-revoke"]:
        share_submit.disabled = false
        share_revoke.disabled = false
        _set_status(
            "Parent consent was not accepted. Check approval and retry.",
            true
        )
        return

    if kind == "castguests:get":
        _pending_guest_grant_id = ""
        var family := _family_state()
        if family != null:
            family.clear_second_cast()
        _refresh_cast_button()
        _set_status("Guest approval expired or was revoked by parent.", true)
        return

    if kind == "castguests:list":
        _set_status("Could not refresh parent-approved guest actors.", true)
        return

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

    if kind in ["character:get", "equipment:get"] and not _pending_cast_character_id.is_empty():
        var family := _family_state()
        if family != null:
            family.clear_second_cast()
        _reset_cast_request()
        _refresh_cast_button()
        _set_status("The second actor could not be loaded from your account.", true)
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


## Each candidate must be fetched again through the current child's
## server-scoped GET; never cast directly from a name in a client list.
func _on_cast_pressed(character_id: String) -> void:
    var family := _family_state()
    if (
        family == null
        or not family.has_family_connection()
        or not bridge.has_family_session()
        or family.active_play_session().is_empty()
        or character_id == String(family.active_character.get("character_id", ""))
        or bridge.is_busy()
    ):
        _set_status("Select your main saved Hero before adding another actor.", true)
        return
    family.clear_second_cast()
    _refresh_cast_button()
    _pending_cast_character_id = character_id
    var error := bridge.get_character(character_id)
    if error != OK:
        _reset_cast_request()
        _set_status("Could not request your second actor.", true)
        return
    _set_status("Checking actor and wardrobe in your private account…", false)


func _reset_cast_request() -> void:
    _pending_cast_character_id = ""


func _refresh_cast_button() -> void:
    var family := _family_state()
    shoot_button.disabled = (
        family == null
        or not family.has_family_connection()
        or family.active_play_session().is_empty()
        or family.second_cast_play_session().is_empty()
    )


func _on_shoot_together_pressed() -> void:
    _refresh_cast_button()
    if shoot_button.disabled:
        _set_status("Choose another saved Hero from your account first.", true)
        return
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    get_tree().change_scene_to_file("res://scenes/director_stage.tscn")


func _on_share_candidate(character_id: String) -> void:
    var family := _family_state()
    if (
        family == null
        or family.current_profile_id().is_empty()
        or not family.has_family_connection()
    ):
        return
    _share_character_id = character_id
    adult_share_panel.visible = true
    share_revoke.visible = (
        not _active_grant_id.is_empty()
        and _last_shared_character_id == character_id
    )
    share_secret_input.clear()
    _set_status("Parent: approve this Hero acting in sibling's film for 15 min.", false)


func _submit_parent_share(revoke: bool) -> void:
    var family := _family_state()
    if (
        family == null
        or not family.has_family_connection()
        or family.current_profile_id().is_empty()
        or _share_character_id.is_empty()
        or bridge.is_busy()
    ):
        _set_status("Reopen your private Hero library before approving.", true)
        return
    var parent_secret := share_secret_input.text.strip_edges()
    share_secret_input.clear()
    var source := family.current_profile_id()
    var viewer := "child_b" if source == "child_a" else "child_a"
    var grant := _active_grant_id if revoke else ""
    var error := bridge.parent_cast_consent(
        parent_secret, source, viewer, _share_character_id, grant
    )
    parent_secret = ""
    if error != OK:
        _set_status("Parent approval could not start securely.", true)
        return
    share_submit.disabled = true
    share_revoke.disabled = true
    _set_status("Checking parent approval with private server…", false)


func _on_parent_share_submit() -> void:
    _submit_parent_share(false)


func _on_parent_revoke_submit() -> void:
    if _active_grant_id.is_empty():
        return
    _submit_parent_share(true)


func _refresh_approved_guests() -> void:
    if bridge.is_busy():
        return
    var error := bridge.list_approved_cast_guests()
    if error != OK:
        _set_status("Could not check approved guest actors.", true)


func _on_guest_pressed(grant_id: String) -> void:
    var family := _family_state()
    if (
        family == null
        or family.active_play_session().is_empty()
        or bridge.is_busy()
    ):
        _set_status("First select your own saved Hero to direct the movie.", true)
        return
    family.clear_second_cast()
    _refresh_cast_button()
    _pending_guest_grant_id = grant_id
    var error := bridge.get_approved_cast_guest(grant_id)
    if error != OK:
        _pending_guest_grant_id = ""
        _set_status("Could not load approved guest actor.", true)
    else:
        _set_status("Checking parent's film guest approval…", false)


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
    _cancel_movie_restore()
    _reset_cast_request()
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

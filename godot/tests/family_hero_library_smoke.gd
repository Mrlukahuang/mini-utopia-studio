extends SceneTree

## Parent-scoped HTTPS connection remains RAM-only. A child sees only what
## the authenticated server returned, may reopen a stable-ID Hero, and may
## safely disconnect before a pending response arrives.

const TEST_TOKEN_A := "synthetic_parent_only_test_token_child_a_0123456789"
const TEST_TOKEN_B := "synthetic_parent_only_test_token_child_b_0123456789"

func _initialize() -> void:
    var family := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null:
        _fail("FamilySceneState autoload missing")
        return
    family.disconnect_family()

    # One origin + child A. No hard-coded network credentials in game.
    if family.connect_family("http://192.168.1.42:8766", TEST_TOKEN_A):
        _fail("a non-HTTPS family endpoint was accepted")
        return
    if family.has_family_connection():
        _fail("rejected connection retained credentials")
        return
    if not family.connect_family("https://family.example/", TEST_TOKEN_A):
        _fail("valid HTTPS scoped family session rejected")
        return

    var packed := load("res://scenes/family_hero_library.tscn") as PackedScene
    if packed == null:
        _fail("My Heroes scene missing")
        return

    # Render the library without real network I/O. Synthetic server responses
    # are injected after disabling an in-flight request if necessary.
    family.disconnect_family()
    var library := packed.instantiate() as MiniUtopiaFamilyHeroLibrary
    root.add_child(library)
    await process_frame
    if library.connection_panel == null or not library.connection_panel.visible:
        _fail("parent connection controls missing")
        return
    if not library.token_input.secret:
        _fail("token field is not obscured")
        return
    if not library.new_button.disabled or not library.refresh_button.disabled:
        _fail("unconnected child can request private data")
        return

    library.api_input.text = "https://family.example"
    library.token_input.text = TEST_TOKEN_A
    if not family.connect_family(
        library.api_input.text,
        library.token_input.text
    ):
        _fail("parent login failed to establish in-memory connection")
        return
    library.token_input.clear()
    if not family.bind_family_client(library.bridge):
        _fail("session was not bound to scoped Godot HTTP client")
        return
    library._set_connected(true)
    library._on_bridge_success("characters:list", {
        "schema_version": "1.0",
        "characters": [
            {
                "character_id": "CHAR_LILY_001",
                "display_name": "Lily Sheep",
                "profile": {"avatar": {}}
            },
            {
                "character_id": "CHAR_CAT_002",
                "display_name": "Blue Cat",
                "profile": {"avatar": {}}
            }
        ]
    })
    await process_frame

    var hero_list := library.hero_list
    if hero_list.get_child_count() != 2:
        _fail("saved Hero list did not show the two server-owned records")
        return
    var lily := hero_list.get_node_or_null("Hero_CHAR_LILY_001") as Button
    if lily == null or lily.custom_minimum_size.y < 48:
        _fail("saved Hero reopen button is missing or too small for iPad")
        return
    if lily.pressed.get_connections().is_empty():
        _fail("saved Hero button has no editor navigation action")
        return
    if not family.open_character("CHAR_LILY_001"):
        _fail("stable Character ID could not be selected")
        return
    if family.pending_character_id != "CHAR_LILY_001":
        _fail("selected Character ID changed before loading Creator")
        return
    if family.open_character("../CHAR_SIBLING"):
        _fail("invalid Character ID was accepted")
        return

    # Switching to the other profile clears selection and does not restore A.
    family.select_character({
        "schema_version": "1.0",
        "character_id": "CHAR_LILY_001",
        "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY
        }}
    })
    if not family.connect_family("https://family.example", TEST_TOKEN_B):
        _fail("child B family session could not begin")
        return
    if family.pending_character_id != "" or not family.active_character.is_empty():
        _fail("switching child profiles kept the previous child's Hero")
        return

    # A former HTTP response must not repopulate the screen after disconnect.
    library._on_disconnect_pressed()
    library._on_bridge_success("characters:list", {
        "schema_version": "1.0",
        "characters": [
            {"character_id": "CHAR_LILY_001", "display_name": "Secret old child Hero"}
        ]
    })
    if hero_list.get_child_count() != 0:
        _fail("stale response revealed a disconnected child's private heroes")
        return
    if family.has_family_connection() or library.bridge.has_family_session():
        _fail("disconnect did not clear both in-memory access tokens")
        return
    if not library.new_button.disabled:
        _fail("disconnected child can create a remote Hero")
        return

    print("family_hero_library_smoke: PASS · private list/edit/new/logout; no leaks")
    quit(0)


func _fail(message: String) -> void:
    push_error("family_hero_library_smoke: FAIL · " + message)
    quit(1)

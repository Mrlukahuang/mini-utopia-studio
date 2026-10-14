extends SceneTree

## No real parent credentials, hosting or child's media used in this smoke.
## Verify one-time parent approval flow accepts only HTTPS, clears secret UI
## and forwards a short-lived, profile-scoped child token to scene memory.

const PARENT_TEST_SECRET := "synthetic_only_parent_unlock_secret_very_long_123456"
const CHILD_TEST_TOKEN := "synthetic_only_issued_child_session_token_0123456789"

func _initialize() -> void:
    var family := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    if family == null:
        _fail("FamilySceneState missing")
        return
    family.disconnect_family()
    var library := load("res://scenes/family_hero_library.tscn").instantiate() as MiniUtopiaFamilyHeroLibrary
    root.add_child(library)
    await process_frame

    if library.profile_choice.item_count != 2:
        _fail("parent must choose between exactly two child profiles")
        return
    if not library.token_input.secret:
        _fail("parent secret field is not masked")
        return

    # Never allow a long-lived parent secret to travel over LAN HTTP.
    library.api_input.text = "http://192.168.1.45:8766"
    library.token_input.text = PARENT_TEST_SECRET
    library._on_connect_pressed()
    if not library.token_input.text.is_empty():
        _fail("parent secret remains in visible UI after rejected connection")
        return
    if family.has_family_connection():
        _fail("insecure URL authorized a child")
        return

    # Adult-only 8-character secret is allowed, but child bearer sessions
    # still require their original 32+ characters.
    if not MiniUtopiaBridgeClient.valid_parent_secret("Ab3dE5fG"):
        _fail("8-character adult unlock must be accepted")
        return
    if MiniUtopiaBridgeClient.valid_parent_secret("Ab3dE5f"):
        _fail("7-character adult unlock must remain invalid")
        return
    if MiniUtopiaBridgeClient.valid_parent_secret("Ab3dE5f!"):
        _fail("unsafe parent unlock alphabet was accepted")
        return
    if library.bridge.set_family_session("Ab3dE5fG"):
        _fail("8-character child bearer token was accepted")
        return

    # Validation for parent->short child exchange uses a different method
    # from regular child-only bearer requests.
    library.bridge.configure("https://family.example")
    if library.bridge.request_parent_approved_session("child_a", "short") != ERR_INVALID_PARAMETER:
        _fail("short or weak parent token allowed")
        return
    if library.bridge.request_parent_approved_session("invalid_child", PARENT_TEST_SECRET) != ERR_INVALID_PARAMETER:
        _fail("unknown child profile allowed")
        return

    # A synthetic successful server response is accepted only for the child
    # that the parent selected; no static parent credential is stored.
    library._pending_profile_id = "child_b"
    library._on_bridge_success("family:session", {
        "schema_version": "1.0",
        "access_token": CHILD_TEST_TOKEN,
        "token_type": "Bearer",
        "expires_in_seconds": 1800,
        "profile_id": "child_a"
    })
    if family.has_family_connection():
        _fail("server response issued for wrong child was accepted")
        return

    library._pending_profile_id = "child_b"
    library._on_bridge_success("family:session", {
        "schema_version": "1.0",
        "access_token": CHILD_TEST_TOKEN,
        "token_type": "Bearer",
        "expires_in_seconds": 1800,
        "profile_id": "child_b"
    })
    if not family.has_family_connection():
        _fail("correct server-issued short child token was rejected")
        return
    if not library.bridge.has_family_session():
        _fail("short child token was not sent to scoped HTTP client")
        return
    if library.connection_panel.visible:
        _fail("parent-only secret entry remained open after authorization")
        return

    library._on_disconnect_pressed()
    if family.has_family_connection() or library.bridge.has_family_session():
        _fail("disconnection kept the child session token")
        return

    print("family_parent_short_session_smoke: PASS · HTTPS, short-lived, child-scoped")
    quit(0)


func _fail(message: String) -> void:
    push_error("family_parent_short_session_smoke: FAIL · " + message)
    quit(1)

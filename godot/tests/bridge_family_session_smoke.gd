extends SceneTree

## Verify that a child bearer token is only ever attached to HTTPS requests,
## remains in memory, and is cleared when the endpoint changes.

func _initialize() -> void:
    var client := MiniUtopiaBridgeClient.new()
    root.add_child(client)
    await process_frame

    client.configure("https://family.example")
    if not client.is_configured():
        _fail("HTTPS family URL should be configured")
        return
    if client.has_family_session():
        _fail("a child token must never be baked into Web exports")
        return

    if client.list_characters() != ERR_UNCONFIGURED:
        _fail("remote calls without a session must fail closed")
        return

    var fake_token := "abcdefABCDEF1234567890_private_token_for_test"
    if client.set_family_session("short"):
        _fail("short bearer tokens should be rejected")
        return
    if client.set_family_session(fake_token + "\nInjected: header"):
        _fail("header injection should be rejected")
        return
    if not client.set_family_session(fake_token):
        _fail("valid HTTPS session rejected")
        return

    var headers: PackedStringArray = client._request_headers()
    if not headers.has("Authorization: Bearer " + fake_token):
        _fail("scoped bearer header missing from family request")
        return

    client.configure("https://another.example")
    if client.has_family_session():
        _fail("reconfigured origin retained another child's token")
        return
    if client._request_headers().has("Authorization: Bearer " + fake_token):
        _fail("old authorization header leaked across origins")
        return

    client.configure("http://127.0.0.1:8765")
    if client.set_family_session(fake_token):
        _fail("local HTTP may never receive bearer credentials")
        return
    if client._request_headers().has("Authorization: Bearer " + fake_token):
        _fail("desktop Bridge gained unauthorized bearer header")
        return

    client.queue_free()
    await process_frame
    print("bridge_family_session_smoke: PASS · HTTPS bearer, fail-closed and clear")
    quit(0)


func _fail(message: String) -> void:
    push_error("bridge_family_session_smoke: FAIL · " + message)
    quit(1)

extends SceneTree

var _request: HTTPRequest
var _character_id := "CHAR_BRIDGE_EXAMPLE"


func _initialize() -> void:
    call_deferred("_start_request")


func _start_request() -> void:
    var source := FileAccess.get_file_as_string(
        "res://config/runtime/bridge_character_example.json"
    )
    var contract = JSON.parse_string(source)
    if typeof(contract) != TYPE_DICTIONARY:
        _fail("Character read fixture is invalid")
        return

    var profile = JSON.parse_string(
        JSON.stringify(contract.get("profile", {}))
    )
    if typeof(profile) != TYPE_DICTIONARY:
        _fail("profile is missing")
        return
    var avatar = profile.get("avatar")
    if typeof(avatar) != TYPE_DICTIONARY:
        _fail("profile.avatar is missing")
        return
    avatar["hair_style_id"] = "hair_bob_v1"
    profile["avatar"] = avatar

    var payload := {
        "schema_version": "1.0",
        "revision": contract.get("revision"),
        "display_name": contract.get("display_name"),
        "description": contract.get("description", ""),
        "profile": profile,
    }
    if payload.has("character_id"):
        _fail("Character ID must remain path-owned")
        return

    _request = HTTPRequest.new()
    _request.timeout = 5.0
    root.add_child(_request)
    _request.request_completed.connect(_on_request_completed)

    var headers := PackedStringArray(["Content-Type: application/json"])
    var error := _request.request(
        "http://127.0.0.1:8765/characters/%s" % _character_id,
        headers,
        HTTPClient.METHOD_PUT,
        JSON.stringify(payload)
    )
    if error != OK:
        _fail("PUT request start failed: %s" % error)


func _on_request_completed(
    result: int,
    response_code: int,
    _headers: PackedStringArray,
    body: PackedByteArray,
) -> void:
    if result != HTTPRequest.RESULT_SUCCESS:
        _fail("HTTP request failed: %s" % result)
        return
    if response_code != 200:
        _fail("unexpected HTTP status: %s" % response_code)
        return

    var response = JSON.parse_string(body.get_string_from_utf8())
    if typeof(response) != TYPE_DICTIONARY:
        _fail("Character write response is not a JSON object")
        return
    if response.get("character_id") != _character_id:
        _fail("Character ID changed during Save")
        return
    if response.get("revision") != "WRITE_SMOKE_R2":
        _fail("updated revision missing")
        return

    var profile = response.get("profile")
    if typeof(profile) != TYPE_DICTIONARY:
        _fail("updated profile missing")
        return
    var avatar = profile.get("avatar")
    if typeof(avatar) != TYPE_DICTIONARY:
        _fail("updated avatar missing")
        return
    if avatar.get("hair_style_id") != "hair_bob_v1":
        _fail("updated Hair did not round-trip")
        return

    print("bridge_character_write_smoke: PASS · Godot PUT kept ID and updated Hair")
    quit(0)


func _fail(message: String) -> void:
    push_error("bridge_character_write_smoke: FAIL · %s" % message)
    quit(1)

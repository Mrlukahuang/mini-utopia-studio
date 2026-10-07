extends SceneTree

var _request: HTTPRequest


func _initialize() -> void:
    # SceneTree._initialize runs before child Nodes are fully inside the tree.
    # Defer one tick so HTTPRequest is configured after entering SceneTree.
    call_deferred("_start_request")


func _start_request() -> void:
    _request = HTTPRequest.new()
    _request.timeout = 5.0
    root.add_child(_request)
    _request.request_completed.connect(_on_request_completed)

    var error := _request.request("http://127.0.0.1:8765/health")
    if error != OK:
        _fail("request start failed: %s" % error)


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

    var parsed = JSON.parse_string(body.get_string_from_utf8())
    if typeof(parsed) != TYPE_DICTIONARY:
        _fail("Bridge health response is not a JSON object")
        return
    if parsed.get("ok") != true:
        _fail("Bridge health response did not report ok=true")
        return
    if parsed.get("service") != "mini-utopia-bridge":
        _fail("unexpected Bridge service name")
        return
    if parsed.get("canonical_metadata_owner") != "python_core_repository":
        _fail("Bridge source-of-truth contract mismatch")
        return
    if parsed.get("godot_mutation_policy") != "bridge_only":
        _fail("Godot mutation policy mismatch")
        return

    print("bridge_health_smoke: PASS · Godot reached Python Bridge")
    quit(0)


func _fail(message: String) -> void:
    push_error("bridge_health_smoke: FAIL · %s" % message)
    quit(1)

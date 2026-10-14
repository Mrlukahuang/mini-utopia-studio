class_name MiniUtopiaBridgeClient
extends Node

signal request_succeeded(kind: String, payload: Dictionary)
signal request_failed(
    kind: String,
    status_code: int,
    error_code: String,
    message: String
)

const DEFAULT_BASE_URL := "http://127.0.0.1:8765"

var base_url := DEFAULT_BASE_URL
var _request: HTTPRequest
var _active_kind := ""
var _family_token := ""
const TOKEN_ALPHABET := "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"


func _ready() -> void:
    # Desktop development may reach the local Bridge. A browser must never
    # attempt to connect to the viewer's 127.0.0.1; remote family service
    # provisioning is intentionally a separate authenticated step.
    if OS.has_feature("web"):
        configure(String(ProjectSettings.get_setting(
            "mini_utopia/family_api_base_url", ""
        )))
    _request = HTTPRequest.new()
    _request.name = "HTTPRequest"
    _request.timeout = 5.0
    add_child(_request)
    _request.request_completed.connect(_on_request_completed)


func configure(url: String) -> void:
    var normalized := MiniUtopiaBridgeEndpointPolicy.normalize(
        url, OS.has_feature("web")
    )
    # Do not send an existing child token to a different origin on reconfigure.
    if normalized != base_url:
        clear_family_session()
    base_url = normalized


func is_configured() -> bool:
    return MiniUtopiaBridgeEndpointPolicy.is_configured(base_url)


func set_family_session(token: String) -> bool:
    # Parent provisioning supplies an opaque base64url token at runtime only.
    # Never write it into ProjectSettings, user://, console, a URL or a scene.
    clear_family_session()
    if token.length() < 32 or token.length() > 256:
        return false
    for char in token:
        if not TOKEN_ALPHABET.contains(char):
            return false
    if not base_url.begins_with("https://"):
        return false
    _family_token = token
    return true


func clear_family_session() -> void:
    _family_token = ""


func has_family_session() -> bool:
    return not _family_token.is_empty() and base_url.begins_with("https://")


func _request_headers() -> PackedStringArray:
    var headers := PackedStringArray([
        "Accept: application/json",
        "Content-Type: application/json",
    ])
    if has_family_session():
        headers.append("Authorization: Bearer " + _family_token)
    return headers


func is_busy() -> bool:
    return not _active_kind.is_empty()


func get_health() -> int:
    return _start_request(
        "health",
        "/health",
        HTTPClient.METHOD_GET
    )


func request_parent_approved_session(
    profile_id: String,
    parent_token: String
) -> int:
    # The long-lived parent credential is used ONCE over HTTPS for an
    # explicit, short-lived child session. Never store it in this client.
    if _request == null or not base_url.begins_with("https://"):
        return ERR_UNCONFIGURED
    if is_busy():
        return ERR_BUSY
    if not profile_id in ["child_a", "child_b"]:
        return ERR_INVALID_PARAMETER
    if parent_token.length() < 32 or parent_token.length() > 256:
        return ERR_INVALID_PARAMETER
    for char in parent_token:
        if not TOKEN_ALPHABET.contains(char):
            return ERR_INVALID_PARAMETER

    var headers := PackedStringArray([
        "Accept: application/json",
        "Content-Type: application/json",
        "Authorization: Bearer " + parent_token
    ])
    _active_kind = "family:session"
    var error := _request.request(
        base_url + "/family/sessions",
        headers,
        HTTPClient.METHOD_POST,
        JSON.stringify({"profile_id": profile_id})
    )
    if error != OK:
        _active_kind = ""
    return error


func revoke_family_session() -> int:
    if not has_family_session():
        return ERR_UNCONFIGURED
    return _start_request(
        "family:revoke",
        "/family/sessions/current",
        HTTPClient.METHOD_DELETE
    )


func list_characters() -> int:
    return _start_request(
        "characters:list",
        "/characters",
        HTTPClient.METHOD_GET
    )


func create_character(payload: Dictionary) -> int:
    return _start_request(
        "character:post",
        "/characters",
        HTTPClient.METHOD_POST,
        payload
    )


func get_character(character_id: String) -> int:
    return _start_request(
        "character:get",
        "/characters/" + character_id.uri_encode(),
        HTTPClient.METHOD_GET
    )


func put_character(
    character_id: String,
    payload: Dictionary
) -> int:
    return _start_request(
        "character:put",
        "/characters/" + character_id.uri_encode(),
        HTTPClient.METHOD_PUT,
        payload
    )


func get_equipment(character_id: String) -> int:
    return _start_request(
        "equipment:get",
        "/characters/%s/equipment" % character_id.uri_encode(),
        HTTPClient.METHOD_GET
    )


func put_equipment_slot(
    character_id: String,
    slot: String,
    item_instance_id: Variant
) -> int:
    return _start_request(
        "equipment:put:" + slot,
        "/characters/%s/equipment/%s"
        % [character_id.uri_encode(), slot.uri_encode()],
        HTTPClient.METHOD_PUT,
        {"item_instance_id": item_instance_id}
    )


func _start_request(
    kind: String,
    path: String,
    method: HTTPClient.Method,
    payload: Dictionary = {}
) -> int:
    if _request == null or not is_configured():
        return ERR_UNCONFIGURED
    # Secure remote service requires session credentials. Desktop loopback
    # preserves the current unauthenticated Godot development workflow.
    if base_url.begins_with("https://") and not has_family_session():
        return ERR_UNCONFIGURED
    if is_busy():
        return ERR_BUSY

    var headers := _request_headers()
    var request_data := ""
    if method != HTTPClient.METHOD_GET:
        request_data = JSON.stringify(payload)

    _active_kind = kind
    var error := _request.request(
        base_url + path,
        headers,
        method,
        request_data
    )
    if error != OK:
        _active_kind = ""
    return error


func _exit_tree() -> void:
    clear_family_session()


func _on_request_completed(
    result: int,
    response_code: int,
    _headers: PackedStringArray,
    body: PackedByteArray
) -> void:
    var kind := _active_kind
    _active_kind = ""

    if result != HTTPRequest.RESULT_SUCCESS:
        request_failed.emit(
            kind,
            0,
            "network_error",
            "Mini Utopia Family Cloud is unavailable." if OS.has_feature("web") else "Mini Utopia Bridge is not reachable."
        )
        return

    var text := body.get_string_from_utf8()
    var parsed = JSON.parse_string(text) if not text.is_empty() else {}
    var payload: Dictionary = (
        parsed if typeof(parsed) == TYPE_DICTIONARY else {}
    )

    if response_code >= 200 and response_code < 300:
        request_succeeded.emit(kind, payload)
        return

    request_failed.emit(
        kind,
        response_code,
        String(payload.get("error", "bridge_error")),
        String(payload.get("message", "Bridge request failed."))
    )

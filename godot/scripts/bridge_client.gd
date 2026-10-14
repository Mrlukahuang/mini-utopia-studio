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
    base_url = MiniUtopiaBridgeEndpointPolicy.normalize(
        url, OS.has_feature("web")
    )


func is_configured() -> bool:
    return MiniUtopiaBridgeEndpointPolicy.is_configured(base_url)


func is_busy() -> bool:
    return not _active_kind.is_empty()


func get_health() -> int:
    return _start_request(
        "health",
        "/health",
        HTTPClient.METHOD_GET
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
    if is_busy():
        return ERR_BUSY

    var headers := PackedStringArray([
        "Accept: application/json",
        "Content-Type: application/json",
    ])
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
            "Mini Utopia Bridge is not reachable."
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

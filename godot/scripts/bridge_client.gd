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
const PARENT_SECRET_MIN_LENGTH := 8
const MAX_PRIVATE_MP4_BYTES := 32 * 1024 * 1024
var _prepared_movie_bytes: PackedByteArray = PackedByteArray()
var _prepared_movie_id := ""


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


static func valid_parent_secret(value: String) -> bool:
    # Adult unlock may be 8+ characters; child session tokens remain 32+.
    if value.length() < PARENT_SECRET_MIN_LENGTH or value.length() > 256:
        return false
    for ch in value:
        if not TOKEN_ALPHABET.contains(ch):
            return false
    return true


func clear_family_session() -> void:
    _family_token = ""
    _prepared_movie_bytes.clear()
    _prepared_movie_id = ""


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
    if not valid_parent_secret(parent_token):
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


func list_approved_cast_guests() -> int:
    return _start_request(
        "castguests:list", "/family/cast-guests", HTTPClient.METHOD_GET
    )


func get_approved_cast_guest(grant_id: String) -> int:
    if not grant_id.begins_with("CAST_") or "/" in grant_id:
        return ERR_INVALID_PARAMETER
    return _start_request(
        "castguests:get", "/family/cast-guests/" + grant_id.uri_encode(),
        HTTPClient.METHOD_GET
    )


func parent_cast_consent(
    parent_token: String,
    source_profile_id: String,
    viewer_profile_id: String,
    character_id: String,
    revoke_grant_id: String = ""
) -> int:
    if _request == null or not base_url.begins_with("https://") or is_busy():
        return ERR_UNCONFIGURED if _request == null else ERR_BUSY
    if (
        source_profile_id not in ["child_a", "child_b"]
        or viewer_profile_id not in ["child_a", "child_b"]
        or source_profile_id == viewer_profile_id
        or not character_id.begins_with("CHAR_")
    ):
        return ERR_INVALID_PARAMETER
    if not valid_parent_secret(parent_token):
        return ERR_INVALID_PARAMETER
    if not revoke_grant_id.is_empty() and not revoke_grant_id.begins_with("CAST_"):
        return ERR_INVALID_PARAMETER
    var headers := PackedStringArray([
        "Accept: application/json",
        "Content-Type: application/json",
        "Authorization: Bearer " + parent_token
    ])
    var method := (
        HTTPClient.METHOD_DELETE if not revoke_grant_id.is_empty()
        else HTTPClient.METHOD_POST
    )
    var path := (
        "/family/cast-grants/" + revoke_grant_id.uri_encode()
        if not revoke_grant_id.is_empty()
        else "/family/cast-grants"
    )
    var request_data := ""
    if method == HTTPClient.METHOD_POST:
        request_data = JSON.stringify({
            "viewer_profile_id": viewer_profile_id,
            "source_profile_id": source_profile_id,
            "character_id": character_id
        })
    _active_kind = (
        "family:cast-revoke" if method == HTTPClient.METHOD_DELETE
        else "family:cast-approve"
    )
    var error := _request.request(base_url + path, headers, method, request_data)
    if error != OK:
        _active_kind = ""
    return error


func parent_review_film(
    parent_token: String, profile_id: String,
    film_id: String, revision: String, decision: String
) -> int:
    if _request == null or not base_url.begins_with("https://"):
        return ERR_UNCONFIGURED
    if is_busy():
        return ERR_BUSY
    if (
        profile_id not in ["child_a", "child_b"]
        or not film_id.begins_with("FILM_")
        or "/" in film_id
        or not revision.is_valid_int()
        or int(revision) < 1
        or decision not in ["approve", "revoke"]
    ):
        return ERR_INVALID_PARAMETER
    if not valid_parent_secret(parent_token):
        return ERR_INVALID_PARAMETER
    var headers := PackedStringArray([
        "Accept: application/json",
        "Content-Type: application/json",
        "Authorization: Bearer " + parent_token
    ])
    _active_kind = "family:film-review:" + decision
    var error := _request.request(
        base_url + "/family/film-reviews", headers,
        HTTPClient.METHOD_POST, JSON.stringify({
            "profile_id": profile_id,
            "film_id": film_id,
            "revision": revision,
            "decision": decision
        })
    )
    if error != OK:
        _active_kind = ""
    return error


func parent_release_finished_movie(
    parent_token: String, profile_id: String,
    film_id: String, revision: String, decision: String
) -> int:
    # Separate adult decision AFTER reviewing the actual encoded file.
    # Rendering approval never automatically allows MP4 downloads.
    if _request == null or not base_url.begins_with("https://"):
        return ERR_UNCONFIGURED
    if is_busy():
        return ERR_BUSY
    if (
        profile_id not in ["child_a", "child_b"]
        or not film_id.begins_with("FILM_")
        or "/" in film_id
        or not revision.is_valid_int()
        or int(revision) < 1
        or decision not in ["release", "revoke"]
        or not valid_parent_secret(parent_token)
    ):
        return ERR_INVALID_PARAMETER
    var headers := PackedStringArray([
        "Accept: application/json",
        "Content-Type: application/json",
        "Authorization: Bearer " + parent_token
    ])
    _active_kind = "family:movie-release:" + decision
    var error := _request.request(
        base_url + "/family/movie-releases", headers,
        HTTPClient.METHOD_POST, JSON.stringify({
            "profile_id": profile_id,
            "film_id": film_id,
            "revision": revision,
            "decision": decision
        })
    )
    if error != OK:
        _active_kind = ""
    return error


func get_family_film_review(film_id: String) -> int:
    if not film_id.begins_with("FILM_") or "/" in film_id:
        return ERR_INVALID_PARAMETER
    return _start_request(
        "films:review", "/family/films/" + film_id.uri_encode() + "/review",
        HTTPClient.METHOD_GET
    )


func prepare_private_movie_download(film_id: String) -> int:
    if not film_id.begins_with("FILM_") or "/" in film_id:
        return ERR_INVALID_PARAMETER
    if not has_family_session() or _request == null:
        return ERR_UNCONFIGURED
    if is_busy():
        return ERR_BUSY
    _prepared_movie_id = ""
    _prepared_movie_bytes.clear()
    _request.timeout = 60.0
    _request.body_size_limit = MAX_PRIVATE_MP4_BYTES + 1
    var error := _start_request(
        "films:download:" + film_id,
        "/family/films/" + film_id.uri_encode() + "/download",
        HTTPClient.METHOD_GET
    )
    if error != OK:
        _request.timeout = 5.0
        _request.body_size_limit = -1
    return error


func has_prepared_private_movie(film_id: String) -> bool:
    return (
        has_family_session()
        and film_id == _prepared_movie_id
        and _prepared_movie_bytes.size() > 256
    )


func save_prepared_private_movie(film_id: String) -> int:
    # Called synchronously from the child's SECOND direct button click:
    # Safari blocks programmatic downloads triggered in HTTP callbacks.
    if not has_prepared_private_movie(film_id):
        return ERR_UNCONFIGURED
    if not OS.has_feature("web"):
        return ERR_UNAVAILABLE
    JavaScriptBridge.download_buffer(
        _prepared_movie_bytes,
        "mini-utopia-" + film_id + ".mp4",
        "video/mp4"
    )
    _prepared_movie_bytes.clear()
    _prepared_movie_id = ""
    return OK


func upload_private_film_voice(
    film_id: String, voice: PackedByteArray, media_type: String,
    expected_revision: String = ""
) -> int:
    if (
        not has_family_session() or is_busy()
        or not film_id.begins_with("FILM_") or "/" in film_id
        or media_type not in ["audio/mp4", "audio/webm", "audio/wav"]
        or voice.is_empty() or voice.size() > 1500000
    ):
        return ERR_INVALID_PARAMETER
    if not expected_revision.is_empty():
        if (
            not expected_revision.is_valid_int()
            or int(expected_revision) < 1
            or expected_revision.length() > 10
        ):
            return ERR_INVALID_PARAMETER
    var headers := _request_headers()
    headers[1] = "Content-Type: " + media_type
    _active_kind = "films:voice:0"
    _request.timeout = 20.0
    var path := "/family/films/" + film_id.uri_encode() + "/voices/0"
    if not expected_revision.is_empty():
        path += "?revision=" + expected_revision.uri_encode()
    var error := _request.request_raw(
        base_url + path, headers, HTTPClient.METHOD_POST, voice
    )
    if error != OK:
        _active_kind = ""
        _request.timeout = 5.0
    return error


func list_family_films() -> int:
    return _start_request("films:list", "/family/films", HTTPClient.METHOD_GET)


func create_family_film(draft: Dictionary) -> int:
    return _start_request(
        "films:post", "/family/films", HTTPClient.METHOD_POST, draft
    )


func get_family_film(film_id: String) -> int:
    if not film_id.begins_with("FILM_") or "/" in film_id:
        return ERR_INVALID_PARAMETER
    return _start_request(
        "films:get", "/family/films/" + film_id.uri_encode(),
        HTTPClient.METHOD_GET
    )


func update_family_film(
    film_id: String, revision: String, draft: Dictionary
) -> int:
    if not film_id.begins_with("FILM_") or "/" in film_id:
        return ERR_INVALID_PARAMETER
    return _start_request(
        "films:put", "/family/films/" + film_id.uri_encode(),
        HTTPClient.METHOD_PUT,
        {"revision": revision, "draft": draft}
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


func craft_family_prop(character_id: String, recipe: Dictionary) -> int:
    if not has_family_session() or not character_id.begins_with("CHAR_"):
        return ERR_UNCONFIGURED
    return _start_request(
        "prop:craft",
        "/characters/" + character_id.uri_encode() + "/crafted-props",
        HTTPClient.METHOD_POST,
        recipe
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
    if kind == "films:voice:0":
        _request.timeout = 5.0

    if kind.begins_with("films:download:"):
        _request.timeout = 5.0
        _request.body_size_limit = -1
        var film_id := kind.trim_prefix("films:download:")
        if (
            result != HTTPRequest.RESULT_SUCCESS
            or response_code != HTTPClient.RESPONSE_OK
        ):
            request_failed.emit(
                "films:download", response_code,
                "private_mp4_unavailable",
                "Parent has not released an MP4 to this child."
            )
            return
        if (
            body.size() <= 256
            or body.size() > MAX_PRIVATE_MP4_BYTES
            or body[4] != 102 or body[5] != 116
            or body[6] != 121 or body[7] != 112
        ):
            request_failed.emit(
                "films:download", 0, "invalid_mp4",
                "Private movie download was not a safe MP4."
            )
            return
        _prepared_movie_bytes = body.duplicate()
        _prepared_movie_id = film_id
        request_succeeded.emit(
            "films:download-ready",
            {"film_id": film_id, "bytes": _prepared_movie_bytes.size()}
        )
        return

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

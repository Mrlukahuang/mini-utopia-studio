extends SceneTree

## No real MP4, child data or internet: verify the exact Web-facing
## two-click Save MP4 interaction and RAM-only session-bound binary.

const FILM := "FILM_MY_PRIVATE_RELEASED_MOVIE"
const SESSION := "synthetic_test_child_download_0123456789abcdef"

func _initialize() -> void:
    var family := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    family.disconnect_family()
    var library := (
        load("res://scenes/family_hero_library.tscn") as PackedScene
    ).instantiate() as MiniUtopiaFamilyHeroLibrary
    root.add_child(library)
    await process_frame

    if not family.connect_family("https://family.example", SESSION, "child_a"):
        _fail("test scoped private account not configured")
        return
    if not family.bind_family_client(library.bridge):
        _fail("child bearer not bound")
        return
    library._set_connected(true)

    library._on_bridge_success("films:list", {
        "schema_version": "1.0",
        "films": [{
            "film_id": FILM, "revision": "1",
            "draft": {
                "schema_version": "1.0", "display_name": "Little Cloud",
                "character_id": "CHAR_SYNTHETIC_LILY",
                "camera": "wide", "action": "walk",
                "duration_seconds": 15
            }
        }]
    })
    var button := library.movie_list.get_node_or_null("Download_" + FILM) as Button
    if button == null or button.custom_minimum_size.y < 48:
        _fail("iPad MP4 button missing / undersized")
        return
    if button.pressed.get_connections().is_empty():
        _fail("Save MP4 control isn't connected")
        return
    if library.bridge.has_prepared_private_movie(FILM):
        _fail("unreleased movie was preloaded without child consent")
        return

    # Mimic the response to GET /family/films/{id}/download with the
    # synthetic data; no actual child works or private MP4 leave this job.
    var fake: PackedByteArray = PackedByteArray(
        [0, 0, 0, 24, 102, 116, 121, 112, 105, 115, 111, 109]
    )
    fake.resize(400)
    library.bridge._active_kind = "films:download:" + FILM
    library.bridge._on_request_completed(
        HTTPRequest.RESULT_SUCCESS, 200, PackedStringArray([
            "Content-Type: video/mp4"
        ]), fake
    )
    if not library.bridge.has_prepared_private_movie(FILM):
        _fail("child's authorized MP4 did not enter temporary RAM buffer")
        return
    if button.disabled or not button.text.contains("Save MP4"):
        _fail("first tap did not prepare a second user-gesture Save MP4 button")
        return
    if library.bridge.has_prepared_private_movie("FILM_OTHER_SIBLING"):
        _fail("another film could consume the temporary MP4 bytes")
        return

    # Headless cannot use the Web JavaScriptBridge. The browser's second
    # DIRECT user tap is required in actual Mac/iPad Safari tests.
    if library.bridge.save_prepared_private_movie(FILM) != ERR_UNAVAILABLE:
        _fail("headless renderer attempted a Web download")
        return
    library.bridge.clear_family_session()
    if library.bridge.has_prepared_private_movie(FILM):
        _fail("switching child profile retained private MP4 bytes")
        return

    # Parent has not released this movie: HTTP 404 means no playable file,
    # and UI must never falsely show Save MP4.
    if not library.bridge.set_family_session(SESSION):
        _fail("synthetic private session could not be re-bound")
        return
    library.bridge._active_kind = "films:download:" + FILM
    library.bridge._on_request_completed(
        HTTPRequest.RESULT_SUCCESS, 404, PackedStringArray(),
        '{"error":"not_found"}'.to_utf8_buffer()
    )
    if not button.text.contains("parent release required") or button.disabled:
        _fail("unreleased video should fail closed and permit retry")
        return
    library._on_disconnect_pressed()
    print("family_private_movie_download_smoke: PASS · two taps, RAM-only, owner")
    quit(0)


func _fail(message: String) -> void:
    push_error("family_private_movie_download_smoke: FAIL " + message)
    quit(1)

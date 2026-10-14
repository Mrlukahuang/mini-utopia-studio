extends SceneTree

const FILM := "FILM_MY_SAVED_ADVENTURE"
const SESSION := "synthetic-child-session-0123456789abcdefgh"

func _initialize() -> void:
    var family := root.get_node_or_null(
        "FamilySceneState"
    ) as MiniUtopiaFamilySceneState
    family.disconnect_family()
    var library := (
        load("res://scenes/family_hero_library.tscn") as PackedScene
    ).instantiate() as MiniUtopiaFamilyHeroLibrary
    root.add_child(library)
    await process_frame

    var old := library.bridge
    library.remove_child(old)
    old.free()
    var stub = (load("res://tests/film_parent_review_stub.gd") as GDScript).new()
    library.add_child(stub)
    library.bridge = stub

    if not family.connect_family(
        "https://family.example", SESSION, "child_a"
    ) or not family.bind_family_client(stub):
        _fail("private child context cannot be set")
        return
    library._set_connected(true)

    var draft := {
        "schema_version": "1.0", "display_name": "Cloud Adventure",
        "character_id": "CHAR_MY_LILY", "second_character_id": null,
        "camera": "close", "action": "celebrate", "duration_seconds": 30,
        "private_story_note": "A private sheep-cloud ending"
    }
    var saved := {
        "schema_version": "1.0", "film_id": FILM,
        "revision": "3", "draft": draft
    }
    library._on_bridge_success("films:list", {
        "schema_version": "1.0", "films": [saved]
    })
    var button := library.movie_list.get_node_or_null(
        "Review_" + FILM
    ) as Button
    if button == null or button.custom_minimum_size.y < 48:
        _fail("parent review needs a large iPad touch target")
        return
    if button.pressed.get_connections().is_empty():
        _fail("parent review button not connected")
        return
    library._on_parent_review_movie_pressed(FILM)
    if stub.calls.back().get("kind") != "films:get":
        _fail("review must fetch latest film, not trust cached listing")
        return
    if library.parent_movie_panel.visible:
        _fail("parent review was shown without verifying latest film")
        return

    library._on_bridge_success("films:get", saved)
    if not library.parent_movie_panel.visible:
        _fail("parent review panel missing")
        return
    if not library.parent_movie_secret.secret:
        _fail("parent unlock must be masked")
        return
    if not library.parent_movie_summary.text.contains("A private sheep-cloud ending"):
        _fail("parent cannot inspect child's story before reviewing")
        return
    if not library.parent_movie_summary.text.contains("Length: 30s"):
        _fail("parent cannot inspect actual film duration")
        return
    if library.parent_movie_approve.pressed.get_connections().is_empty():
        _fail("approval not bound to a real action")
        return
    library.parent_movie_secret.text = (
        "synthetic_parent_approval_secret_0123456789_long"
    )
    library._on_parent_film_approve_pressed()
    var request: Dictionary = stub.calls.back()
    if request.get("kind") != "family:film-review":
        _fail("parent approval request was not sent")
        return
    if request.get("profile_id") != "child_a" or request.get("film_id") != FILM:
        _fail("review target/profile changed")
        return
    if request.get("revision") != "3" or request.get("decision") != "approve":
        _fail("review was not locked to the exact saved revision")
        return
    if not library.parent_movie_secret.text.is_empty():
        _fail("parent secret remained in input after one-time request")
        return
    if not library.parent_movie_approve.disabled:
        _fail("approval was not locked while request is pending")
        return
    library._on_bridge_success("family:film-review:approve", {
        "film_id": FILM, "revision": "3",
        "approved_for_private_render": true
    })
    if library.parent_movie_approve.disabled:
        _fail("approved film panel was not restored")
        return

    library.parent_movie_secret.text = (
        "synthetic_parent_approval_secret_0123456789_long"
    )
    library._on_parent_film_revoke_pressed()
    var revoked: Dictionary = stub.calls.back()
    if revoked.get("decision") != "revoke" or revoked.get("revision") != "3":
        _fail("parent revoke did not target exact saved film")
        return
    library._on_bridge_success("family:film-review:revoke", {
        "film_id": FILM, "revision": "3",
        "approved_for_private_render": false
    })
    if not library.status_label.text.contains("revoked"):
        _fail("child did not see that render approval was revoked")
        return

    if (
        library.parent_movie_release == null
        or library.parent_movie_download_revoke == null
        or library.parent_movie_release.custom_minimum_size.y < 48
        or library.parent_movie_release.pressed.get_connections().is_empty()
    ):
        _fail("final film release touch control missing")
        return

    library.parent_movie_secret.text = "synthetic_parent_release_secret_0123456789"
    library._on_parent_film_release_pressed()
    var release: Dictionary = stub.calls.back()
    if (
        release.get("kind") != "family:movie-release"
        or release.get("profile_id") != "child_a"
        or release.get("film_id") != FILM
        or release.get("revision") != "3"
        or release.get("decision") != "release"
    ):
        _fail("final MP4 release did not require exact owner/movie revision")
        return
    if not library.parent_movie_secret.text.is_empty():
        _fail("parent release secret was kept in input")
        return
    if not library.parent_movie_release.disabled:
        _fail("final MP4 release button not locked during request")
        return
    library._on_bridge_failure(
        "family:movie-release:release", 409, "private_movie_not_ready", ""
    )
    if not library.status_label.text.contains("not ready"):
        _fail("missing encoded MP4 did not fail closed")
        return
    library.parent_movie_secret.text = "synthetic_parent_release_secret_0123456789"
    library._on_parent_film_release_pressed()
    library._on_bridge_success("family:movie-release:release", {
        "film_id": FILM, "revision": "3", "released_to_child": true,
        "bytes": 2048
    })
    if not library.status_label.text.contains("released"):
        _fail("confirmed private MP4 release not visible")
        return
    library.parent_movie_secret.text = "synthetic_parent_release_secret_0123456789"
    library._on_parent_film_download_revoke_pressed()
    if stub.calls.back().get("decision") != "revoke":
        _fail("parent cannot revoke private MP4 download")
        return
    library._on_bridge_success("family:movie-release:revoke", {
        "film_id": FILM, "revision": "3", "released_to_child": false,
        "bytes": 0
    })
    if not library.status_label.text.contains("stopped"):
        _fail("parent revoke did not stop download")
        return

    library.parent_movie_secret.text = "synthetic-secret-left-in-a-field"
    library._on_disconnect_pressed()
    if library.parent_movie_panel.visible or not library.parent_movie_secret.text.is_empty():
        _fail("parent review or unlock remained visible after logout")
        return
    if not library._review_film.is_empty() or not library._pending_review_film_id.is_empty():
        _fail("review was retained across child profile switch")
        return
    print("family_parent_movie_review_smoke: PASS · consent, revision, masked input")
    quit(0)


func _fail(message: String) -> void:
    push_error("family_parent_movie_review_smoke: FAIL " + message)
    quit(1)

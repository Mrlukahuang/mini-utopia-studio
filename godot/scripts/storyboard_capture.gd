extends SceneTree

const REQUEST_PATH := "res://runtime_state/storyboard_capture_request.json"


func _initialize() -> void:
    _run.call_deferred()


func _run() -> void:
    var request := _load_json(REQUEST_PATH)
    if request.is_empty():
        push_error("MEDIA-01: Storyboard capture request is missing.")
        quit(1)
        return

    var raw_session = request.get("director_session", {})
    if typeof(raw_session) != TYPE_DICTIONARY:
        push_error("MEDIA-01: director_session must be a Dictionary.")
        quit(1)
        return

    var output_path := String(request.get("output_path", "")).strip_edges()
    if output_path.is_empty():
        push_error("MEDIA-01: output_path is required.")
        quit(1)
        return

    var capture_time := maxf(
        0.0,
        float(request.get("capture_time_seconds", 0.0))
    )

    root.size = Vector2i(960, 540)

    var runtime := MiniUtopiaDirectorShotRuntime.new()
    runtime.name = "StoryboardDirectorRuntime"
    root.add_child(runtime)
    runtime.configure(raw_session)

    await process_frame
    await process_frame
    await process_frame

    runtime.reset_shot()
    if capture_time > 0.0:
        runtime.advance_shot(capture_time)

    await process_frame
    await process_frame
    await process_frame

    var image := root.get_texture().get_image()
    if image == null or image.is_empty():
        push_error("MEDIA-01: viewport capture returned an empty image.")
        quit(1)
        return

    var global_output := ProjectSettings.globalize_path(output_path)
    var output_dir := global_output.get_base_dir()
    var mkdir_error := DirAccess.make_dir_recursive_absolute(output_dir)
    if mkdir_error != OK and mkdir_error != ERR_ALREADY_EXISTS:
        push_error(
            "MEDIA-01: unable to create Storyboard directory: "
            + str(mkdir_error)
        )
        quit(1)
        return

    var save_error := image.save_png(global_output)
    if save_error != OK:
        push_error(
            "MEDIA-01: unable to save Storyboard PNG: "
            + str(save_error)
        )
        quit(1)
        return

    print(
        "MEDIA-01 Storyboard capture: PASS · ",
        request.get("director_session", {}).get("shot_id", "—"),
        " · ",
        capture_time,
        "s · ",
        output_path
    )
    quit(0)


func _load_json(path: String) -> Dictionary:
    if not FileAccess.file_exists(path):
        return {}
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return {}
    var parsed = JSON.parse_string(file.get_as_text())
    return parsed if typeof(parsed) == TYPE_DICTIONARY else {}

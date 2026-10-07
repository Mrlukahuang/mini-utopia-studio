extends SceneTree

const REQUEST_PATH := "res://runtime_state/shot_capture_request.json"


func _initialize() -> void:
    _run.call_deferred()


func _run() -> void:
    var request := _load_json(REQUEST_PATH)
    if request.is_empty():
        push_error("MEDIA-02A: Shot capture request is missing.")
        quit(1)
        return

    var raw_session = request.get("director_session", {})
    if typeof(raw_session) != TYPE_DICTIONARY:
        push_error("MEDIA-02A: director_session must be a Dictionary.")
        quit(1)
        return

    var output_dir := String(request.get("output_dir", "")).strip_edges()
    var fps := maxi(1, int(request.get("fps", 24)))
    var frame_count := maxi(1, int(request.get("frame_count", 1)))
    var width := maxi(160, int(request.get("width", 960)))
    var height := maxi(90, int(request.get("height", 540)))
    if output_dir.is_empty():
        push_error("MEDIA-02A: output_dir is required.")
        quit(1)
        return

    root.size = Vector2i(width, height)

    var runtime := MiniUtopiaDirectorShotRuntime.new()
    runtime.name = "ShotCaptureDirectorRuntime"
    root.add_child(runtime)
    runtime.configure(raw_session)
    runtime.set_process(false)

    await process_frame
    await process_frame
    await process_frame

    runtime.reset_shot()
    var global_dir := ProjectSettings.globalize_path(output_dir)
    var mkdir_error := DirAccess.make_dir_recursive_absolute(global_dir)
    if mkdir_error != OK and mkdir_error != ERR_ALREADY_EXISTS:
        push_error(
            "MEDIA-02A: unable to create Shot frame directory: "
            + str(mkdir_error)
        )
        quit(1)
        return

    var frame_delta := 1.0 / float(fps)
    for frame_index in range(frame_count):
        if frame_index > 0:
            runtime.advance_shot(frame_delta)

        await process_frame

        var image := root.get_texture().get_image()
        if image == null or image.is_empty():
            push_error(
                "MEDIA-02A: viewport returned an empty frame at "
                + str(frame_index)
            )
            quit(1)
            return

        var frame_path := (
            global_dir
            + "/frame_%05d.png" % frame_index
        )
        var save_error := image.save_png(frame_path)
        if save_error != OK:
            push_error(
                "MEDIA-02A: unable to save frame "
                + str(frame_index)
                + ": "
                + str(save_error)
            )
            quit(1)
            return

    print(
        "MEDIA-02A Shot capture: PASS · ",
        raw_session.get("shot_id", "—"),
        " · ",
        frame_count,
        " frames @ ",
        fps,
        "fps · ",
        output_dir
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

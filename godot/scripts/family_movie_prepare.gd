extends SceneTree

## Converts a *private worker-provided* canonical Character + EquipmentRuntime
## into the existing Godot ShotCaptureRequest. Production worker authorization
## is a separate responsibility; never expose this file via a public upload API.

const REQUEST_PATH := "res://runtime_state/family_movie_export_request.json"
const CAPTURE_PATH := "res://runtime_state/shot_capture_request.json"
const OUTPUT_DIR := "res://runtime_state/family_movie_frames/EP_FAMILY_PREVIEW"


func _initialize() -> void:
    var request := _read_dict(REQUEST_PATH)
    var contract = request.get("character", {})
    if typeof(contract) != TYPE_DICTIONARY:
        _fail("canonical Character contract must be an object")
        return

    var play := MiniUtopiaFamilyCharacterPlayAdapter.play_session_for(contract)
    if play.is_empty():
        _fail("cannot render without a canonical saved Character")
        return

    var equipped = request.get("equipment_runtime", {})
    if typeof(equipped) == TYPE_DICTIONARY and not equipped.is_empty():
        if String(equipped.get("character_asset_id", "")) != String(
            play.get("character_asset_id", "")
        ):
            _fail("refusing equipment from a different Character")
            return
        if (
            typeof(equipped.get("equipped", null)) != TYPE_DICTIONARY
            or typeof(equipped.get("final_stats", null)) != TYPE_DICTIONARY
        ):
            _fail("invalid canonical EquipmentRuntimeSpec")
            return
        play["equipment"] = equipped.duplicate(true)

    var director := MiniUtopiaFamilyDirectorSession.from_play_session(play)
    if director.is_empty():
        _fail("unable to construct shared Director session")
        return

    # CI uses low FPS to keep the full 15-second timeline inexpensive.
    # Production render workers can select higher FPS within these bounds.
    var fps := clampi(int(request.get("fps", 2)), 1, 24)
    var width := clampi(int(request.get("width", 480)), 160, 1280)
    var height := clampi(int(request.get("height", 270)), 90, 720)
    var frame_count := int(MiniUtopiaFamilyDirectorSession.DURATION_SECONDS) * fps
    var target := {
        "schema_version": "1.0",
        "output_dir": OUTPUT_DIR,
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "director_session": director,
    }

    var global_path := ProjectSettings.globalize_path(CAPTURE_PATH)
    var mkdir_error := DirAccess.make_dir_recursive_absolute(
        global_path.get_base_dir()
    )
    if mkdir_error != OK and mkdir_error != ERR_ALREADY_EXISTS:
        _fail("unable to create private capture directory")
        return
    var file := FileAccess.open(CAPTURE_PATH, FileAccess.WRITE)
    if file == null:
        _fail("unable to write canonical ShotCaptureRequest")
        return
    file.store_string(JSON.stringify(target, "  "))
    file.close()

    print(
        "family_movie_prepare: PASS · ",
        String(play.get("character_asset_id", "")),
        " · ",
        frame_count,
        " frames / 15s"
    )
    quit(0)


func _read_dict(path: String) -> Dictionary:
    var text := FileAccess.get_file_as_string(path)
    if text.is_empty():
        return {}
    var parsed = JSON.parse_string(text)
    return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


func _fail(message: String) -> void:
    push_error("family_movie_prepare: FAIL · " + message)
    quit(1)

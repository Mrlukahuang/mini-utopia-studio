class_name MiniUtopiaRuntimeDropWriter
extends RefCounted

const INBOX_PATH := "res://runtime_state/combat_drop_inbox.json"
const SCHEMA_VERSION := "1.0"


static func write_drop(receipt: Dictionary) -> bool:
    if receipt.is_empty():
        return false

    var inbox := _load_inbox()
    var drops: Array = inbox.get("drops", [])
    var drop_id := String(receipt.get("drop_id", ""))
    if drop_id.is_empty():
        return false

    for existing in drops:
        if (
            typeof(existing) == TYPE_DICTIONARY
            and String(existing.get("drop_id", "")) == drop_id
        ):
            return true

    drops.append(receipt)
    inbox["schema_version"] = SCHEMA_VERSION
    inbox["drops"] = drops

    var absolute_dir := ProjectSettings.globalize_path(
        "res://runtime_state"
    )
    var dir_error := DirAccess.make_dir_recursive_absolute(absolute_dir)
    if dir_error != OK and dir_error != ERR_ALREADY_EXISTS:
        push_error("PLAY-03: could not create runtime_state directory.")
        return false

    var file := FileAccess.open(INBOX_PATH, FileAccess.WRITE)
    if file == null:
        push_error("PLAY-03: could not open combat drop inbox.")
        return false

    file.store_string(JSON.stringify(inbox, "  "))
    file.close()
    print(
        "PLAY-03 drop receipt: ",
        receipt.get("definition_slug", "unknown"),
        " · ",
        drop_id
    )
    return true


static func _load_inbox() -> Dictionary:
    if not FileAccess.file_exists(INBOX_PATH):
        return {
            "schema_version": SCHEMA_VERSION,
            "drops": [],
        }

    var file := FileAccess.open(INBOX_PATH, FileAccess.READ)
    if file == null:
        return {
            "schema_version": SCHEMA_VERSION,
            "drops": [],
        }

    var parsed = JSON.parse_string(file.get_as_text())
    if typeof(parsed) != TYPE_DICTIONARY:
        return {
            "schema_version": SCHEMA_VERSION,
            "drops": [],
        }
    return parsed

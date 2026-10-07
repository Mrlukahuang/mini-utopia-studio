class_name MiniUtopiaQuestRewardWriter
extends RefCounted

const INBOX_PATH := "res://runtime_state/quest_reward_inbox.json"
const SCHEMA_VERSION := "1.0"


static func write_completion(receipt: Dictionary) -> bool:
    if receipt.is_empty():
        return false

    var completion_id := _string_or_empty(
        receipt.get("completion_id", "")
    )
    var quest_id := _string_or_empty(receipt.get("quest_id", ""))
    if completion_id.is_empty() or quest_id.is_empty():
        return false

    var inbox := _load_inbox()
    var completions: Array = inbox.get("completions", [])
    for existing in completions:
        if (
            typeof(existing) == TYPE_DICTIONARY
            and _string_or_empty(
                existing.get("completion_id", "")
            ) == completion_id
        ):
            return true

    completions.append(receipt)
    inbox["schema_version"] = SCHEMA_VERSION
    inbox["completions"] = completions

    var absolute_dir := ProjectSettings.globalize_path(
        "res://runtime_state"
    )
    var dir_error := DirAccess.make_dir_recursive_absolute(absolute_dir)
    if dir_error != OK and dir_error != ERR_ALREADY_EXISTS:
        push_error("GP-05: could not create runtime_state directory.")
        return false

    var file := FileAccess.open(INBOX_PATH, FileAccess.WRITE)
    if file == null:
        push_error("GP-05: could not open Quest reward inbox.")
        return false

    file.store_string(JSON.stringify(inbox, "  "))
    file.close()
    print(
        "GP-05 Quest completion receipt: ",
        quest_id,
        " · ",
        completion_id
    )
    return true


static func _load_inbox() -> Dictionary:
    if not FileAccess.file_exists(INBOX_PATH):
        return {
            "schema_version": SCHEMA_VERSION,
            "completions": [],
        }

    var file := FileAccess.open(INBOX_PATH, FileAccess.READ)
    if file == null:
        return {
            "schema_version": SCHEMA_VERSION,
            "completions": [],
        }

    var parsed = JSON.parse_string(file.get_as_text())
    if typeof(parsed) != TYPE_DICTIONARY:
        return {
            "schema_version": SCHEMA_VERSION,
            "completions": [],
        }
    return parsed


static func _string_or_empty(value: Variant) -> String:
    if value == null:
        return ""
    return str(value)

class_name MiniUtopiaFamilyDirectorSession
extends RefCounted

## First child-facing 15-second film template: reuses the selected Hero,
## clothes/props when available, and the exact playable village scene.
## No regenerated characters or stale, hard-coded demo Character IDs.

const DURATION_SECONDS := 15.0


static func from_play_session(play_session: Dictionary) -> Dictionary:
    var character_id := String(play_session.get("character_asset_id", ""))
    if not character_id.begins_with("CHAR_"):
        return {}
    if typeof(play_session.get("character", null)) != TYPE_DICTIONARY:
        return {}

    var play := play_session.duplicate(true)
    # The shot stage loads exactly the playable village as its background;
    # scene sanitisers disable World gameplay and its original camera.
    play["world_runtime"] = {
        "scene_path": "res://scenes/main.tscn",
    }
    var shot_id := "SHOT_FAMILY_01"
    return {
        "schema_version": "1.0",
        "director_session_id": "DIR_FAMILY_" + character_id,
        "episode_id": "EP_FAMILY_PREVIEW",
        "scene_id": "SCENE_FAMILY_VILLAGE",
        "shot_id": shot_id,
        "story_id": "STORY_FAMILY_PREVIEW",
        "world_asset_id": "LOC_NEWBIE_VILLAGE",
        "character_asset_id": character_id,
        "duration_seconds": DURATION_SECONDS,
        "animation_intent": "walk",
        "camera": {
            "position": [0.0, 3.8, 9.0],
            "look_at": [0.0, 1.1, 0.0],
            "end_position": [1.6, 3.0, 6.0],
            "end_look_at": [0.0, 1.1, -1.0],
            "fov": 48.0,
            "end_fov": 42.0,
            "movement": "Gentle camera move",
            "movement_mode": "push_in",
            "easing": "smooth",
        },
        "shot": {
            "shot_id": shot_id,
            "scene_id": "SCENE_FAMILY_VILLAGE",
            "duration_seconds": DURATION_SECONDS,
            "asset_ids": [character_id, "LOC_NEWBIE_VILLAGE"],
            "blocking": {
                "actor_start": {"x": 0.0, "y": 0.0, "z": 2.0},
                "actor_end": {"x": 0.0, "y": 0.0, "z": -2.0},
                "facing_degrees": 180.0,
                "movement_style": "walk",
            },
            "performance_cues": [
                {
                    "cue_id": "CUE_WAVE",
                    "cue_type": "celebrate",
                    "start_seconds": 4.0,
                    "duration_seconds": 1.5,
                    "intensity": 1.0
                },
                {
                    "cue_id": "CUE_SURPRISE",
                    "cue_type": "reaction",
                    "start_seconds": 8.0,
                    "duration_seconds": 1.0,
                    "intensity": 0.8
                },
                {
                    "cue_id": "CUE_FINAL",
                    "cue_type": "celebrate",
                    "start_seconds": 12.0,
                    "duration_seconds": 2.0,
                    "intensity": 1.0
                },
            ],
        },
        "play_session": play,
    }


## Two distinct, already-authorized Character contracts may be staged together.
## The caller MUST obtain both from the SAME child-scoped Family API session.
## No sibling private records can be discovered through this movie API. The
## parent-approved cross-child casting flow will be a separate server route.
static func from_two_play_sessions(
    first_play: Dictionary,
    second_play: Dictionary
) -> Dictionary:
    var first := String(first_play.get("character_asset_id", ""))
    var second := String(second_play.get("character_asset_id", ""))
    if (
        first.is_empty()
        or second.is_empty()
        or first == second
        or not first.begins_with("CHAR_")
        or not second.begins_with("CHAR_")
        or String(first_play.get("source", "")) != "family_character"
        or String(second_play.get("source", "")) != "family_character"
        or typeof(first_play.get("character", null)) != TYPE_DICTIONARY
        or typeof(second_play.get("character", null)) != TYPE_DICTIONARY
    ):
        return {}
    for session in [first_play, second_play]:
        var equipment = session.get("equipment", {})
        if typeof(equipment) != TYPE_DICTIONARY:
            return {}
        if (
            typeof(equipment.get("equipped", null)) != TYPE_DICTIONARY
            or typeof(equipment.get("final_stats", null)) != TYPE_DICTIONARY
        ):
            return {}

    var result := from_play_session(first_play)
    if result.is_empty():
        return {}
    result["second_play_session"] = second_play.duplicate(true)
    result["director_session_id"] = "DIR_FAMILY_PAIR_" + first + "_" + second
    var shot: Dictionary = result["shot"]
    var blocking: Dictionary = shot["blocking"]
    blocking["actor_start"] = {"x": -1.5, "y": 0.0, "z": 2.0}
    blocking["actor_end"] = {"x": -1.0, "y": 0.0, "z": -1.0}
    shot["second_blocking"] = {
        "actor_start": {"x": 1.5, "y": 0.0, "z": 2.0},
        "actor_end": {"x": 1.0, "y": 0.0, "z": -1.0},
        "facing_degrees": 180.0,
        "movement_style": "walk",
    }
    shot["asset_ids"] = [first, second, "LOC_NEWBIE_VILLAGE"]
    result["second_character_asset_id"] = second
    return result

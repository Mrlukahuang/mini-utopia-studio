class_name MiniUtopiaFamilyDirectorSession
extends RefCounted

## First child-facing 15-second film template: reuses the selected Hero,
## clothes/props when available, and the exact playable village scene.
## No regenerated characters or stale, hard-coded demo Character IDs.

const DURATION_SECONDS := 15.0

# Immutable kid-safe captions. No raw story notes, uploaded text or commands
# cross the rendering boundary. Live Director and captured MP4 share this map.
const CAPTION_PRESETS := {
    "none": "",
    "hello": "Hello, friend!",
    "adventure": "Let's explore together!",
    "hooray": "We did it!",
}


static func caption_text(preset_id: String) -> String:
    return String(CAPTION_PRESETS.get(preset_id, ""))




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


## Child's directorial choices change shot staging but NEVER change either
## canonical Character ID, appearance or equipment payload.
static func with_child_choices(
    session: Dictionary, choices: Dictionary
) -> Dictionary:
    if session.is_empty():
        return {}
    var result := session.duplicate(true)
    var action := String(choices.get("action", "walk"))
    if action not in ["walk", "run", "celebrate"]:
        action = "walk"
    var lens := String(choices.get("camera", "follow"))
    if lens not in ["follow", "wide", "close"]:
        lens = "follow"
    var seconds := int(choices.get("duration_seconds", 15))
    if seconds not in [15, 30]:
        seconds = 15
    var caption_preset := String(choices.get("caption_preset", "none"))
    if not CAPTION_PRESETS.has(caption_preset):
        caption_preset = "none"
    var shot: Dictionary = result.get("shot", {})
    var blocking: Dictionary = shot.get("blocking", {})
    var second: Dictionary = shot.get("second_blocking", {})
    var movement := "hold" if action == "celebrate" else action
    blocking["movement_style"] = movement
    if not second.is_empty():
        second["movement_style"] = movement
        shot["second_blocking"] = second
    shot["blocking"] = blocking
    result["animation_intent"] = "idle" if action == "celebrate" else action
    result["duration_seconds"] = float(seconds)
    shot["duration_seconds"] = float(seconds)
    var factor := float(seconds) / DURATION_SECONDS
    var raw_cues = shot.get("performance_cues", [])
    if typeof(raw_cues) == TYPE_ARRAY:
        for cue in raw_cues:
            if typeof(cue) == TYPE_DICTIONARY:
                cue["start_seconds"] = float(cue.get("start_seconds", 0)) * factor
    result["shot"] = shot

    var camera: Dictionary = result.get("camera", {})
    match lens:
        "wide":
            camera["position"] = [0.0, 5.0, 13.0]
            camera["end_position"] = [0.0, 4.5, 11.0]
            camera["look_at"] = [0.0, 1.1, 0.0]
            camera["end_look_at"] = [0.0, 1.1, -1.0]
            camera["fov"] = 58.0
            camera["end_fov"] = 54.0
            camera["movement"] = "Wide village shot"
        "close":
            camera["position"] = [0.0, 2.4, 5.5]
            camera["end_position"] = [0.6, 2.1, 4.3]
            camera["look_at"] = [0.0, 1.35, 0.0]
            camera["end_look_at"] = [0.0, 1.35, -0.5]
            camera["fov"] = 39.0
            camera["end_fov"] = 35.0
            camera["movement"] = "Close-up on my Heroes"
        _:
            camera["movement"] = "Follow my Heroes"
    result["camera"] = camera
    result["child_director_choices"] = {
        "action": action, "camera": lens, "duration_seconds": seconds,
        "caption_preset": caption_preset
    }
    return result

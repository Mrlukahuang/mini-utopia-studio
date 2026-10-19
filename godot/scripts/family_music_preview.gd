class_name MiniUtopiaFamilyMusicPreview
extends AudioStreamPlayer

## W2-03a: reusable, strictly user-tapped preview of the three bundled CC0
## WAVs. No autoplay; actual Director UI integration waits for W2-01b.
## Audio never touches child microphone, voice storage or filesystem paths.
const MUSIC_STREAMS := {
    "sunny_meadow": "res://assets/audio/cc0_music/sunny_meadow.wav",
    "cloud_parade": "res://assets/audio/cc0_music/cloud_parade.wav",
    "moonlit_garden": "res://assets/audio/cc0_music/moonlit_garden.wav",
}


func _ready() -> void:
    autoplay = false
    volume_db = -12.0


func choose_on_user_tap(music_id: String) -> bool:
    # Call ONLY from a UI pressed signal. Web/iPad Safari needs a real gesture
    # to unlock audio. This function is deliberately never invoked in _ready.
    stop()
    stream = null
    if music_id == "none":
        return true
    if not MUSIC_STREAMS.has(music_id):
        return false
    var selected := load(String(MUSIC_STREAMS[music_id])) as AudioStream
    if selected == null:
        return false
    stream = selected
    volume_db = -12.0
    play()
    return true


func clear_preview() -> void:
    stop()
    stream = null


func _exit_tree() -> void:
    clear_preview()

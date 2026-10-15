extends Control
# Home → Who Is Playing. Leave family authorization and private data to Lane C.
const WHO_IS_PLAYING := "res://scenes/family_hero_library.tscn"

func _ready() -> void:
    $Center/HomeCard/Margins/Content/StartButton.pressed.connect(_on_start)


func _on_start() -> void:
    get_tree().change_scene_to_file(WHO_IS_PLAYING)

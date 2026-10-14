extends SceneTree

## End-to-end in-engine contract: server-saved Character -> village + Director.
## No child info, network or credentials are needed; fixtures are synthetic.

func _initialize() -> void:
    var selection := root.get_node_or_null("FamilySceneState") as MiniUtopiaFamilySceneState
    if selection == null:
        _fail("ephemeral family scene state autoload missing")
        return
    selection.clear_selection()

    var contract := {
        "schema_version": "1.0",
        "character_id": "CHAR_TEST_SHEEP",
        "display_name": "Lily Sheep",
        "profile": {"avatar": {
            "rig_family": MiniUtopiaAvatarContract.RIG_FAMILY,
            "body_type": "chubby",
            "species_head_id": "species_head_sheep_v1",
            "surface_type": "wool",
            "surface_color_hex": "#F7B7D2",
            "eye_style_id": "eyes_round_soft_v1",
            "eye_color_hex": "#BDE3F5",
            "hair_style_id": "hair_bob_v1",
            "hair_color_hex": "#5B4036"
        }}
    }
    if selection.select_character({"character_id": "INVALID"}):
        _fail("invalid contract was selectable")
        return
    if not selection.select_character(contract):
        _fail("canonical saved character was rejected")
        return

    var play := selection.active_play_session()
    if play.get("character_asset_id") != "CHAR_TEST_SHEEP":
        _fail("play payload changed the canonical Character ID")
        return
    if play.get("character", {}).get("species_head_id") != "species_head_sheep_v1":
        _fail("species lost between Creator and Play")
        return

    # Loading this exact Player scene is what the village does. Its _ready
    # selects the family contract before the checked-in demo session.
    var game := load("res://scenes/player.tscn") as PackedScene
    if game == null:
        _fail("game player scene is missing")
        return
    var player := game.instantiate() as CharacterBody3D
    root.add_child(player)
    await process_frame

    if player.get_meta("mini_utopia_character_asset_id", "") != "CHAR_TEST_SHEEP":
        _fail("game loaded fixture instead of selected saved Hero")
        return
    var body := player.get_node("Visual/Body") as MeshInstance3D
    if not is_equal_approx(body.scale.x, 1.16):
        _fail("game did not retain chubby body type")
        return
    var head := player.get_node("Visual/Head") as MeshInstance3D
    var head_mat := head.material_override as StandardMaterial3D
    if head_mat == null or head_mat.albedo_color.to_html(false) != "f7b7d2":
        _fail("game did not retain pink wool color")
        return
    var ear := player.get_node_or_null("Visual/EarL") as MeshInstance3D
    if ear == null or not ear.visible:
        _fail("sheep ears were not rendered in the playable world")
        return

    # Movie scenes consume exactly the same runtime payload. Do not
    # regenerate a fake lookalike or mint a new Character ID.
    var director := MiniUtopiaDirectorShotRuntime.new()
    root.add_child(director)
    director.configure({
        "director_session_id": "DIR_FAMILY_SMOKE",
        "episode_id": "EP_SMOKE",
        "scene_id": "SCENE_SMOKE",
        "shot_id": "SHOT_SMOKE",
        "world_asset_id": "LOC_NEWBIE_VILLAGE",
        "duration_seconds": 1.0,
        "animation_intent": "idle",
        "play_session": play,
        "shot": {},
        "camera": {
            "position": [0.0, 4.2, 7.8],
            "look_at": [0.0, 1.1, 0.0],
            "fov": 52.0
        },
    })
    await process_frame

    if director.actor == null:
        _fail("Director actor was not created")
        return
    if director.actor.get_meta("mini_utopia_character_asset_id", "") != "CHAR_TEST_SHEEP":
        _fail("Director lost the shared saved Character ID")
        return
    var film_head := director.actor.get_node("Visual/Head") as MeshInstance3D
    var film_mat := film_head.material_override as StandardMaterial3D
    if film_mat == null or film_mat.albedo_color.to_html(false) != "f7b7d2":
        _fail("Director lost the canonical pink surface color")
        return

    selection.clear_selection()
    if not selection.active_play_session().is_empty():
        _fail("logout/reset did not clear in-memory Character selection")
        return

    print("family_saved_hero_game_director_smoke: PASS · one saved Hero, game + film")
    quit(0)


func _fail(message: String) -> void:
    push_error("family_saved_hero_game_director_smoke: FAIL · " + message)
    quit(1)

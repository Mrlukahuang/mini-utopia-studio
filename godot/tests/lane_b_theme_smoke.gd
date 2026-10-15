extends SceneTree

# Lane B: verify the real global Theme, branding and Director UI nodes.
func _initialize() -> void:
    var theme := load("res://ui/theme/mini_utopia_theme.tres") as Theme
    if theme == null:
        _fail("global Theme could not load")
        return
    if ProjectSettings.get_setting("gui/theme/custom") != "res://ui/theme/mini_utopia_theme.tres":
        _fail("project default Theme is not the toy Theme")
        return
    var normal := theme.get_stylebox("normal", "Button") as StyleBoxFlat
    var card := theme.get_stylebox("panel", "PanelContainer") as StyleBoxFlat
    if normal == null or normal.corner_radius_top_left < 16 or card == null:
        _fail("rounded button or card StyleBox missing")
        return
    if theme.get_font("font", "Button") == null:
        _fail("Fredoka button face missing")
        return
    var home := load("res://scenes/main.tscn") as PackedScene
    if home == null:
        _fail("Home scene failed to load")
        return
    var world := home.instantiate()
    root.add_child(world)
    await process_frame
    var badge := world.get_node_or_null("HUD/Panel/LogoBadge") as TextureRect
    var wordmark := world.get_node_or_null("HUD/Panel/LogoWordmark") as TextureRect
    if badge == null or badge.texture == null or wordmark == null or wordmark.texture == null:
        _fail("Home logo missing")
        return
    var hero := world.get_node_or_null("HUD/OpenCreatorButton") as Button
    if hero == null or hero.text != "🎨 Create a Hero":
        _fail("Home Creator entrypoint changed")
        return
    world.queue_free()
    await process_frame
    var stage_scene := load("res://scenes/director_stage.tscn") as PackedScene
    if stage_scene == null:
        _fail("Director scene failed to load")
        return
    var stage := stage_scene.instantiate()
    root.add_child(stage)
    await process_frame
    if stage.get_node_or_null("DirectorStageOverlay/KidDirectorCard") == null:
        _fail("Director toy card missing")
        return
    if stage.get_node_or_null("DirectorStageOverlay/StatusPanel/StatusMargin/StatusLabel") == null:
        _fail("Director status UI missing")
        return
    print("lane_b_theme_smoke: PASS - default Theme, Home Logo, Director")
    quit(0)


func _fail(message: String) -> void:
    push_error("lane_b_theme_smoke: " + message)
    quit(1)

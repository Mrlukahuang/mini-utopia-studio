extends CanvasLayer

# W1.5 Lane B: translate child-visible HUD labels without changing the
# original Button.text identifiers used by existing village smoke tests.
var _zh_ui: Translation

func _enter_tree() -> void:
    _zh_ui = Translation.new()
    _zh_ui.locale = "zh_CN"
    _zh_ui.add_message("Create a Hero", "创建英雄")
    _zh_ui.add_message("Shoot a Scene", "拍小电影")
    _zh_ui.add_message("Dream it. Play it.", "做梦也能玩！")
    _zh_ui.add_message("Create  •  Explore  •  Make a movie", "建英雄 · 逛村子 · 拍电影")
    TranslationServer.add_translation(_zh_ui)
    TranslationServer.set_locale("zh_CN")

func _exit_tree() -> void:
    if _zh_ui != null:
        TranslationServer.remove_translation(_zh_ui)

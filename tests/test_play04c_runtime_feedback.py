from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_skeleton_reward_has_visible_player_feedback():
    skeleton = (
        ROOT / "godot" / "scripts" / "skeleton_enemy.gd"
    ).read_text(encoding="utf-8")
    player = (
        ROOT / "godot" / "scripts" / "player.gd"
    ).read_text(encoding="utf-8")

    assert "var drop_written := MiniUtopiaRuntimeDropWriter.write_drop" in skeleton
    assert 'target.has_method("show_reward_feedback")' in skeleton
    assert "Skeleton defeated!" in skeleton
    assert "Bone Buckler dropped" in skeleton
    assert "func show_reward_feedback(message: String)" in player
    assert "RewardBanner" in player


def test_active_baby_spawn_is_deferred_and_visible():
    runtime = (
        ROOT / "godot" / "scripts" / "creator_play_runtime.gd"
    ).read_text(encoding="utf-8")
    baby = (
        ROOT / "godot" / "scripts" / "baby_follow_runtime.gd"
    ).read_text(encoding="utf-8")

    assert "world_parent.add_child.call_deferred(_baby)" in runtime
    assert "_finish_spawn_baby.call_deferred" in runtime
    assert "PLAY-02 Active Baby ready" in runtime
    assert 'name_label.name = "BabyName"' in baby
    assert "_visual.scale = Vector3.ONE * 1.22" in baby
    assert "@export var side_offset := 1.05" in baby

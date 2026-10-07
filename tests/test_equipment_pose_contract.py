from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_godot_jump_pose_keeps_hand_equipment_clear_of_torso():
    runtime = (
        ROOT / "godot" / "scripts" / "creator_play_runtime.gd"
    ).read_text(encoding="utf-8")
    equipment = (
        ROOT / "godot" / "scripts" / "equipment_runtime.gd"
    ).read_text(encoding="utf-8")

    assert "_arm_l.rotation.x = -0.46" in runtime
    assert "_arm_l.rotation.z = 0.28" in runtime
    assert "_arm_r.rotation.x = -0.62" in runtime
    assert "_arm_r.rotation.z = -0.28" in runtime

    assert "Vector3(45.0, 0.0, -8.0)" in equipment
    assert "Vector3(0.0, -55.0, 6.0)" in equipment
    assert "Vector3(-0.14, 0.0, 0.02)" in equipment

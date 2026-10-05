from pathlib import Path


def test_unified_hero_runtime_uses_mesh_collision_before_box_fallback():
    root = Path(__file__).resolve().parents[1]
    source = (
        root / "godot" / "scripts" / "hero_runtime_loader.gd"
    ).read_text(encoding="utf-8")

    assert 'render_strategy == "unified_glb"' in source
    assert "_add_mesh_collisions(generated as Node3D)" in source
    assert "mesh.create_trimesh_shape()" in source
    assert 'body.name = "HeroMeshCollisionBody"' in source
    assert "if mesh_collision_count == 0:" in source
    assert "_add_collision_proxy(wrapper, target)" in source

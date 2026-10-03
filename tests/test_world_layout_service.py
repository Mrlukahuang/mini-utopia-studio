from studio.models.world import GridSpec, WorldProfile, WorldVisualAnchor
from studio.services.world_layout_service import WorldLayoutService


def _element(plan, kind):
    return next(element for element in plan.elements if element.kind == kind)


def test_layout_compiler_maps_front_and_behind_relations():
    anchor = WorldVisualAnchor(
        must_preserve=[
            "Star Arch / 星星拱门",
            "Moon Castle / 月亮城堡",
            "Central Lake / 中央湖",
        ],
        composition_notes=["Star Arch centered in midground"],
        spatial_relations=[
            "Star Arch in front of lake",
            "castle behind portal",
        ],
    )
    profile = WorldProfile(
        world_name="Pastel Star Garden",
        portal_form="Star Arch / 星星拱门",
    )

    plan = WorldLayoutService().compile(
        profile=profile,
        anchor=anchor,
        grid=GridSpec(),
    )

    portal = _element(plan, "portal")
    water = _element(plan, "water")
    castle = next(element for element in plan.elements if "Castle" in element.name)

    assert portal.position.x == water.position.x
    assert portal.position.z > water.position.z
    assert castle.position.x == portal.position.x
    assert castle.position.z < portal.position.z


def test_layout_compiler_maps_left_right_and_near_relations():
    anchor = WorldVisualAnchor(
        must_preserve=[
            "Star Arch / 星星拱门",
            "Central Lake / 中央湖",
            "Ribbon Bridge / 丝带桥",
            "Moon Castle / 月亮城堡",
        ],
        spatial_relations=[
            "bridge right of lake",
            "castle near bridge",
        ],
    )

    plan = WorldLayoutService().compile(
        profile=WorldProfile(portal_form="Star Arch / 星星拱门"),
        anchor=anchor,
        grid=GridSpec(),
    )

    lake = _element(plan, "water")
    bridge = _element(plan, "bridge")
    castle = next(element for element in plan.elements if "Castle" in element.name)

    assert bridge.position.x > lake.position.x
    assert abs(castle.position.x - bridge.position.x) < 10
    assert abs(castle.position.z - bridge.position.z) < 10


def test_layout_compiler_uses_composition_regions():
    anchor = WorldVisualAnchor(
        must_preserve=[
            "Star Arch / 星星拱门",
            "Moon Castle / 月亮城堡",
        ],
        composition_notes=[
            "Moon Castle on right side in background",
            "Star Arch centered in foreground",
        ],
    )

    plan = WorldLayoutService().compile(
        profile=WorldProfile(portal_form="Star Arch / 星星拱门"),
        anchor=anchor,
        grid=GridSpec(),
    )

    portal = _element(plan, "portal")
    castle = next(element for element in plan.elements if "Castle" in element.name)

    assert portal.position.x == 25
    assert portal.position.z > 25
    assert castle.position.x > 25
    assert castle.position.z < 25

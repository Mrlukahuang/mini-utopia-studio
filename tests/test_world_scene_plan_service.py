from studio.models.world import (
    WorldPromptInterpretation,
    WorldProfile,
    WorldSceneElement,
    WorldScenePlan,
)
from studio.providers.base import StructuredTextProvider
from studio.services.world_blueprint_service import WorldBlueprintService
from studio.services.world_scene_plan_service import WorldScenePlanService


class FakeStructuredProvider(StructuredTextProvider):
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def generate_structured(self, *, system: str, user: str, schema):
        self.calls.append({"system": system, "user": user, "schema": schema})
        return schema.model_validate(self.payload)


def _prompt_payload():
    return {
        "world_name": "Pink Star Isles",
        "world_type": "Floating Islands / 漂浮岛",
        "reality_mode": "Fantasy / 幻想",
        "story_function": "Explore / 探索",
        "terrain": ["Floating Land / 漂浮陆地"],
        "season": "Spring / 春",
        "weather": "Clear / 晴朗",
        "time_of_day": "Day / 白天",
        "architecture": "Rounded Block Castle / 圆润方块城堡",
        "mood": ["Dreamy / 梦幻"],
        "portal_form": "Star Arch / 星星拱门",
        "theme_color_hexes": ["#F7B7D2", "#B9E7D0", "#D7C2F3"],
        "scene_plan": {
            "source_mode": "prompt",
            "summary": "Pink floating islands around a central lake.",
            "route_intent": "Discover the lake, castle and scenic moments, then reveal the Portal.",
            "elements": [
                {
                    "scene_id": "SCENE_LAKE",
                    "name": "Lake / 湖泊",
                    "kind": "water",
                    "source": "creator_required",
                    "required": True,
                    "placement_hint": "center",
                    "relation_hints": [],
                    "photo_opportunity": True,
                    "notes": "",
                },
                {
                    "scene_id": "SCENE_PORTAL",
                    "name": "Star Arch / 星星拱门",
                    "kind": "portal",
                    "source": "creator_required",
                    "required": True,
                    "placement_hint": "behind Lake",
                    "relation_hints": ["Star Arch behind Lake"],
                    "photo_opportunity": True,
                    "notes": "",
                },
                {
                    "scene_id": "SCENE_GLOW_PATH",
                    "name": "Soft Glow Path",
                    "kind": "decoration",
                    "source": "utopia_enrichment",
                    "required": False,
                    "placement_hint": "",
                    "relation_hints": [],
                    "photo_opportunity": False,
                    "notes": "",
                },
                {
                    "scene_id": "SCENE_STAR_VIEW",
                    "name": "Star Viewpoint",
                    "kind": "landmark",
                    "source": "utopia_enrichment",
                    "required": False,
                    "placement_hint": "left side",
                    "relation_hints": [],
                    "photo_opportunity": True,
                    "notes": "",
                },
                {
                    "scene_id": "SCENE_LANTERNS",
                    "name": "Tiny Lake Lanterns",
                    "kind": "decoration",
                    "source": "utopia_enrichment",
                    "required": False,
                    "placement_hint": "",
                    "relation_hints": [],
                    "photo_opportunity": False,
                    "notes": "",
                },
                {
                    "scene_id": "SCENE_EXTRA",
                    "name": "Fourth Extra Detail",
                    "kind": "decoration",
                    "source": "utopia_enrichment",
                    "required": False,
                    "placement_hint": "",
                    "relation_hints": [],
                    "photo_opportunity": False,
                    "notes": "",
                },
            ],
            "spatial_relations": ["Star Arch behind Lake"],
            "exploration_order": ["SCENE_LAKE", "SCENE_STAR_VIEW", "SCENE_PORTAL"],
            "photo_spot_ids": ["SCENE_LAKE", "SCENE_STAR_VIEW", "SCENE_PORTAL"],
            "enrichment_notes": ["Keep enrichment small and supportive."],
        },
    }


def test_prompt_plan_preserves_explicit_objects_and_caps_enrichment():
    provider = FakeStructuredProvider(_prompt_payload())
    service = WorldScenePlanService(structured_provider=provider)
    description = (
        "A pink floating island world with a Lake in the center, a Star Arch "
        "behind the Lake, a Castle on the right, and a Bridge connecting the "
        "Lake and Castle, with flowers and glow plants."
    )

    interpretation = service.plan_from_prompt(
        description=description,
        style_profile={
            "visual_dna_pillars": ["Miniature", "Macaron Dreamscape"],
            "portal_language": "Rounded toy-like luminous Portal",
            "color_harmony_rule": "High lightness, soft contrast",
        },
    )

    names = [item.name.lower() for item in interpretation.scene_plan.elements]
    assert any("lake" in name for name in names)
    assert any("castle" in name for name in names)
    assert any("bridge" in name for name in names)
    assert any("flower" in name for name in names)
    assert any("glow plant" in name for name in names)

    enrichment = [
        item
        for item in interpretation.scene_plan.elements
        if item.source == "utopia_enrichment"
    ]
    assert len(enrichment) == 3

    by_id = {
        item.scene_id: item
        for item in interpretation.scene_plan.elements
    }
    last_id = interpretation.scene_plan.exploration_order[-1]
    assert by_id[last_id].kind == "portal"

    profile = interpretation.to_profile(source_description=description)
    assert any("lake" in value.lower() for value in profile.water_features)
    assert any("castle" in value.lower() for value in profile.landmark_ideas)
    assert profile.theme_color_hexes == ["#F7B7D2", "#B9E7D0", "#D7C2F3"]
    assert provider.calls
    assert "CONTROLLED UTOPIA ENRICHMENT" in provider.calls[0]["system"]


def test_custom_build_creates_scene_plan_without_prompt_provider():
    profile = WorldProfile(
        world_name="Custom Garden",
        world_type="Dream Garden / 梦境花园",
        terrain=["Meadow / 草地"],
        water_features=["Lake / 湖泊"],
        landmark_ideas=["Castle / 城堡", "Bridge / 大桥"],
        landscape_elements=["Flowers / 花海"],
        surprise_elements=["Glow Path / 发光小路"],
        portal_form="Star Arch / 星星拱门",
        traversability_notes="Clear Loop / 清晰环线",
        theme_color_hexes=["#F7B7D2", "#B9E7D0"],
    )
    service = WorldScenePlanService(structured_provider=None)

    plan = service.plan_from_profile(profile=profile)

    assert plan.source_mode == "custom"
    assert all(item.source == "custom_selection" for item in plan.elements)
    assert any(item.kind == "water" for item in plan.elements)
    assert any(item.kind == "bridge" for item in plan.elements)
    assert any(item.kind == "portal" for item in plan.elements)
    assert plan.exploration_order
    by_id = {item.scene_id: item for item in plan.elements}
    assert by_id[plan.exploration_order[-1]].kind == "portal"


def test_scene_plan_drives_spatial_layout_route_and_photo_cameras():
    plan = WorldScenePlan(
        source_mode="prompt",
        summary="Lake, castle, bridge and final portal.",
        route_intent="Walk around the lake, cross the bridge, visit the castle, then reveal the portal.",
        elements=[
            WorldSceneElement(
                scene_id="SCENE_LAKE",
                name="Lake",
                kind="water",
                source="creator_required",
                required=True,
                placement_hint="center",
                photo_opportunity=True,
            ),
            WorldSceneElement(
                scene_id="SCENE_CASTLE",
                name="Castle",
                kind="structure",
                source="creator_required",
                required=True,
                placement_hint="right side",
                relation_hints=["Castle right of Lake"],
                photo_opportunity=True,
            ),
            WorldSceneElement(
                scene_id="SCENE_BRIDGE",
                name="Bridge",
                kind="bridge",
                source="creator_required",
                required=True,
                relation_hints=["Bridge connects Lake and Castle"],
                photo_opportunity=True,
            ),
            WorldSceneElement(
                scene_id="SCENE_PORTAL",
                name="Star Arch",
                kind="portal",
                source="creator_required",
                required=True,
                relation_hints=["Star Arch behind Lake"],
                photo_opportunity=True,
            ),
        ],
        spatial_relations=[
            "Castle right of Lake",
            "Bridge connects Lake and Castle",
            "Star Arch behind Lake",
        ],
        exploration_order=[
            "SCENE_LAKE",
            "SCENE_BRIDGE",
            "SCENE_CASTLE",
            "SCENE_PORTAL",
        ],
        photo_spot_ids=[
            "SCENE_LAKE",
            "SCENE_CASTLE",
            "SCENE_PORTAL",
        ],
    )
    profile = WorldProfile(
        world_name="Route Garden",
        source_description="Lake, castle, bridge and portal.",
        terrain=["Meadow / 草地"],
        portal_form="Star Arch",
        theme_color_hexes=["#F7B7D2"],
    )

    blueprint = WorldBlueprintService().plan_from_scene_plan(
        location_asset_id="LOC_TEST",
        style_asset_id="STYLE_TEST",
        profile=profile,
        scene_plan=plan,
    )

    elements = {item.element_id: item for item in blueprint.layout_elements}
    lake = elements["SCENE_LAKE"]
    castle = elements["SCENE_CASTLE"]
    bridge = elements["SCENE_BRIDGE"]
    portal = elements["SCENE_PORTAL"]

    assert castle.position.x > lake.position.x
    assert portal.position.z < lake.position.z
    assert min(lake.position.x, castle.position.x) <= bridge.position.x <= max(
        lake.position.x, castle.position.x
    )

    path = blueprint.paths[0]
    assert path.points[-1].x == portal.position.x
    assert path.points[-1].z == portal.position.z
    # The water visit is a shoreline viewpoint, not the blocked water center.
    assert not any(
        abs(point.x - lake.position.x) < .01
        and abs(point.z - lake.position.z) < .01
        for point in path.points[:-1]
    )
    assert any(zone.kind == "water" for zone in blueprint.zones)
    assert len(
        [camera for camera in blueprint.camera_points if camera.role == "landmark"]
    ) >= 2


def test_prompt_normalizes_portal_plaza_away_from_main_portal():
    payload = _prompt_payload()
    payload["scene_plan"]["elements"].insert(
        1,
        {
            "scene_id": "SCENE_PLAZA",
            "name": "Portal Plaza / 传送门广场",
            "kind": "portal",
            "source": "creator_required",
            "required": True,
            "placement_hint": "near the lake",
            "relation_hints": [],
            "photo_opportunity": True,
            "notes": "",
        },
    )
    provider = FakeStructuredProvider(payload)
    service = WorldScenePlanService(structured_provider=provider)

    result = service.plan_from_prompt(
        description="A Portal Plaza beside a Lake with a Star Arch behind the Lake.",
        style_profile={},
    )

    plaza = next(
        item for item in result.scene_plan.elements
        if "Portal Plaza" in item.name
    )
    assert plaza.kind == "structure"
    assert len(
        [item for item in result.scene_plan.elements if item.kind == "portal"]
    ) == 1

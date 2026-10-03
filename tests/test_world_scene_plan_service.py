from studio.models.world import (
    WorldPromptInterpretation,
    WorldProfile,
    WorldSceneElement,
    WorldScenePlan,
    WorldSceneRelation,
)
from studio.providers.base import StructuredTextProvider
from studio.runtime.three_world import build_world_runtime_html
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
            "macaron_palette": {
                "enabled_families": ["strawberry pink", "mint", "lavender"]
            },
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
    assert "creator explicitly names colors" in provider.calls[0]["system"]
    assert "strawberry pink" in provider.calls[0]["user"]


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


class FailingStructuredProvider(StructuredTextProvider):
    def generate_structured(self, *, system: str, user: str, schema):
        raise RuntimeError("provider unavailable")


def test_custom_extra_details_fall_back_to_deterministic_plan_on_ai_failure():
    profile = WorldProfile(
        world_name="Resilient Garden",
        world_type="Dream Garden / 梦境花园",
        terrain=["Meadow / 草地"],
        water_features=["Lake / 湖泊"],
        landmark_ideas=["Castle / 城堡"],
        portal_form="Star Arch / 星星拱门",
        creator_extra_details="Put a tiny observatory near the castle.",
    )
    service = WorldScenePlanService(
        structured_provider=FailingStructuredProvider()
    )

    plan = service.plan_from_profile(profile=profile)

    assert any("Lake" in item.name for item in plan.elements)
    assert any("Castle" in item.name for item in plan.elements)
    assert any(item.kind == "portal" for item in plan.elements)
    assert plan.source_mode == "custom"


def test_prompt_keeps_only_one_executable_main_portal():
    payload = _prompt_payload()
    payload["scene_plan"]["elements"].insert(
        2,
        {
            "scene_id": "SCENE_SECOND_GATE",
            "name": "Moon Gate",
            "kind": "portal",
            "source": "utopia_enrichment",
            "required": False,
            "placement_hint": "left side",
            "relation_hints": [],
            "photo_opportunity": True,
            "notes": "",
        },
    )
    provider = FakeStructuredProvider(payload)
    service = WorldScenePlanService(structured_provider=provider)

    result = service.plan_from_prompt(
        description="A Lake with my Star Arch behind it.",
        style_profile={},
    )

    portals = [
        item for item in result.scene_plan.elements if item.kind == "portal"
    ]
    assert len(portals) == 1
    assert "Star Arch" in portals[0].name
    moon_gate = next(
        item for item in result.scene_plan.elements if item.name == "Moon Gate"
    )
    assert moon_gate.kind == "landmark"


def test_relative_placement_hints_compile_without_moving_the_target():
    plan = WorldScenePlan(
        source_mode="prompt",
        summary="Floating garden with lake, castle, bridge and portal.",
        route_intent=(
            "Playable discovery route with scenic/photo stops and a final Portal reveal."
        ),
        elements=[
            WorldSceneElement(
                scene_id="SCENE_LAKE",
                name="蓝色湖泊",
                kind="water",
                source="creator_required",
                required=True,
                placement_hint="世界中央",
                photo_opportunity=True,
            ),
            WorldSceneElement(
                scene_id="SCENE_CASTLE",
                name="奶油白小城堡",
                kind="structure",
                source="creator_required",
                required=True,
                placement_hint="湖的右侧",
                photo_opportunity=True,
            ),
            WorldSceneElement(
                scene_id="SCENE_BRIDGE",
                name="湖畔拱桥",
                kind="bridge",
                source="creator_required",
                required=True,
                placement_hint="连接湖边与奶油白小城堡",
                photo_opportunity=True,
            ),
            WorldSceneElement(
                scene_id="SCENE_PORTAL",
                name="星星传送门",
                kind="portal",
                source="creator_required",
                required=True,
                placement_hint="湖的后方偏左",
                photo_opportunity=True,
            ),
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
        world_name="草莓薄荷漂浮花园",
        source_description="中央湖、右侧城堡、连接桥、后方偏左传送门",
        terrain=["Floating Islands / 漂浮岛"],
        portal_form="Star Portal / 星星传送门",
        theme_color_hexes=["#F7B7D2", "#B9E7D0", "#D7C2F3"],
    )

    blueprint = WorldBlueprintService().plan_from_scene_plan(
        location_asset_id="LOC_RELATIVE",
        style_asset_id="STYLE_MINI",
        profile=profile,
        scene_plan=plan,
    )

    elements = {item.element_id: item for item in blueprint.layout_elements}
    lake = elements["SCENE_LAKE"]
    castle = elements["SCENE_CASTLE"]
    bridge = elements["SCENE_BRIDGE"]
    portal = elements["SCENE_PORTAL"]

    assert lake.position.x == 25.0
    assert lake.position.z == 25.0
    assert castle.position.x > lake.position.x
    assert castle.position.z == lake.position.z
    assert lake.position.x < bridge.position.x < castle.position.x
    assert portal.position.x < lake.position.x
    assert portal.position.z < lake.position.z


def test_prompt_system_designs_routes_for_playability_photo_and_video():
    provider = FakeStructuredProvider(_prompt_payload())
    service = WorldScenePlanService(structured_provider=provider)

    service.plan_from_prompt(
        description="A lake, castle and Star Arch world.",
        style_profile={},
    )

    system = provider.calls[0]["system"]
    assert "PLAYABILITY, PHOTOGRAPHY and VIDEO" in system
    assert "2-4 meaningful scenic/photo stopping moments" in system
    assert "establishing arrival" in system
    assert "final Portal reveal" in system
    assert "Avoid placing" in system


def test_utopia_path_enrichment_is_not_an_executable_structure():
    payload = _prompt_payload()
    payload["scene_plan"]["elements"][2]["name"] = "湖畔漫步小径"
    payload["scene_plan"]["elements"][2]["kind"] = "structure"
    provider = FakeStructuredProvider(payload)
    service = WorldScenePlanService(structured_provider=provider)

    result = service.plan_from_prompt(
        description="A Lake with a Star Arch.",
        style_profile={},
    )

    path = next(
        item for item in result.scene_plan.elements
        if item.name == "湖畔漫步小径"
    )
    assert path.kind == "decoration"


def test_scene_plan_v01_remains_backward_compatible():
    plan = WorldScenePlan.model_validate(
        {
            "schema_version": "0.1",
            "source_mode": "prompt",
            "summary": "Legacy scene",
            "route_intent": "Walk to the portal",
            "elements": [
                {
                    "scene_id": "OLD_PORTAL",
                    "name": "Star Arch",
                    "kind": "portal",
                    "source": "creator_required",
                }
            ],
        }
    )

    assert plan.schema_version == "0.1"
    assert plan.elements[0].spatial_mode == "grounded"
    assert plan.elements[0].elevation == "ground"
    assert plan.elements[0].orientation == "normal"
    assert plan.elements[0].relations == []


def test_typed_relation_ids_are_remapped_during_scene_normalization():
    payload = _prompt_payload()
    payload["scene_plan"]["elements"] = [
        {
            "scene_id": "SCENE_WHALE",
            "name": "Sky Whale",
            "semantic_key": "sky_whale",
            "kind": "landmark",
            "source": "creator_required",
            "required": True,
            "spatial_mode": "aerial",
            "elevation": "high",
            "orientation": "normal",
            "geometry_role": "organic",
            "traversability": "scenic",
            "placement_hint": "high in the sky",
            "relation_hints": [],
            "relations": [],
            "photo_opportunity": True,
            "notes": "",
        },
        {
            "scene_id": "SCENE_GARDEN",
            "name": "Whale Back Garden",
            "semantic_key": "whale_back_garden",
            "kind": "terrain",
            "source": "creator_required",
            "required": True,
            "spatial_mode": "elevated",
            "elevation": "high",
            "orientation": "normal",
            "geometry_role": "platform",
            "traversability": "walkable",
            "placement_hint": "",
            "relation_hints": [],
            "relations": [
                {
                    "relation": "on_top_of",
                    "target_scene_ids": ["SCENE_WHALE"],
                }
            ],
            "photo_opportunity": True,
            "notes": "",
        },
        {
            "scene_id": "SCENE_PORTAL",
            "name": "Moon Portal",
            "semantic_key": "moon_portal",
            "kind": "portal",
            "source": "creator_required",
            "required": True,
            "spatial_mode": "aerial",
            "elevation": "high",
            "orientation": "normal",
            "geometry_role": "arch",
            "traversability": "walkable",
            "placement_hint": "",
            "relation_hints": [],
            "relations": [],
            "photo_opportunity": True,
            "notes": "",
        },
    ]
    payload["scene_plan"]["exploration_order"] = [
        "SCENE_GARDEN",
        "SCENE_PORTAL",
    ]
    payload["scene_plan"]["photo_spot_ids"] = ["SCENE_WHALE", "SCENE_GARDEN"]

    service = WorldScenePlanService(
        structured_provider=FakeStructuredProvider(payload)
    )
    result = service.plan_from_prompt(
        description="A sky whale carrying a walkable garden on its back.",
        style_profile={},
    )

    whale = next(item for item in result.scene_plan.elements if item.semantic_key == "sky_whale")
    garden = next(item for item in result.scene_plan.elements if item.semantic_key == "whale_back_garden")
    assert garden.relations[0].target_scene_ids == [whale.scene_id]
    assert result.scene_plan.schema_version == "0.2"


def test_spatial_semantics_compile_floating_vertical_flow_without_object_specific_rule():
    plan = WorldScenePlan(
        source_mode="prompt",
        summary="A high floating vertical flow reaches a lower island.",
        route_intent="Approach a scenic viewpoint near the receiving island.",
        elements=[
            WorldSceneElement(
                scene_id="SCENE_RECEIVER",
                name="Lower Floating Island",
                semantic_key="lower_floating_island",
                kind="terrain",
                source="creator_required",
                spatial_mode="floating",
                elevation="low",
                geometry_role="terrain_mass",
                traversability="walkable",
            ),
            WorldSceneElement(
                scene_id="SCENE_FLOW",
                name="Sky Flow",
                semantic_key="sky_flow",
                kind="water",
                source="creator_required",
                spatial_mode="aerial",
                elevation="high",
                orientation="vertical",
                geometry_role="vertical_flow",
                traversability="blocked",
                relations=[
                    WorldSceneRelation(
                        relation="flows_to",
                        target_scene_ids=["SCENE_RECEIVER"],
                    )
                ],
                photo_opportunity=True,
            ),
            WorldSceneElement(
                scene_id="SCENE_PORTAL",
                name="Moon Portal",
                semantic_key="moon_portal",
                kind="portal",
                source="creator_required",
                spatial_mode="elevated",
                elevation="medium",
                geometry_role="arch",
                traversability="walkable",
            ),
        ],
        exploration_order=["SCENE_FLOW", "SCENE_PORTAL"],
        photo_spot_ids=["SCENE_FLOW"],
    )
    profile = WorldProfile(
        world_name="Sky Flow World",
        terrain=["Floating Islands"],
        portal_form="Moon Portal",
    )

    blueprint = WorldBlueprintService().plan_from_scene_plan(
        location_asset_id="LOC_FLOW",
        style_asset_id="STYLE_MINI",
        profile=profile,
        scene_plan=plan,
    )
    by_id = {item.element_id: item for item in blueprint.layout_elements}
    receiver = by_id["SCENE_RECEIVER"]
    flow = by_id["SCENE_FLOW"]

    assert flow.spatial_mode == "aerial"
    assert flow.geometry_role == "vertical_flow"
    assert flow.orientation == "vertical"
    assert flow.height >= 12
    assert flow.position.x == receiver.position.x
    assert flow.position.z == receiver.position.z
    assert flow.position.y >= receiver.position.y
    # A vertical aerial flow must not flatten into a ground-level water zone.
    assert not any(zone.name == "Sky Flow" for zone in blueprint.zones)


def test_spatial_semantics_compile_inverted_suspended_world_below_support():
    plan = WorldScenePlan(
        source_mode="prompt",
        summary="An inverted garden hangs below a floating island.",
        route_intent="Look up from a scenic path, then reveal the portal.",
        elements=[
            WorldSceneElement(
                scene_id="SCENE_ISLAND",
                name="Upper Floating Mass",
                semantic_key="upper_floating_mass",
                kind="terrain",
                source="creator_required",
                spatial_mode="floating",
                elevation="high",
                geometry_role="terrain_mass",
                traversability="walkable",
            ),
            WorldSceneElement(
                scene_id="SCENE_FOREST",
                name="Inverted Hanging Garden",
                semantic_key="inverted_hanging_garden",
                kind="terrain",
                source="creator_required",
                spatial_mode="suspended",
                elevation="high",
                orientation="inverted",
                geometry_role="terrain_mass",
                traversability="scenic",
                relations=[
                    WorldSceneRelation(
                        relation="suspended_from",
                        target_scene_ids=["SCENE_ISLAND"],
                    )
                ],
            ),
            WorldSceneElement(
                scene_id="SCENE_PORTAL",
                name="Hidden Star Portal",
                semantic_key="hidden_star_portal",
                kind="portal",
                source="creator_required",
                geometry_role="arch",
                traversability="walkable",
            ),
        ],
        exploration_order=["SCENE_FOREST", "SCENE_PORTAL"],
    )

    blueprint = WorldBlueprintService().plan_from_scene_plan(
        location_asset_id="LOC_INVERTED",
        style_asset_id="STYLE_MINI",
        profile=WorldProfile(world_name="Inverted Garden", portal_form="Hidden Star Portal"),
        scene_plan=plan,
    )
    by_id = {item.element_id: item for item in blueprint.layout_elements}
    island = by_id["SCENE_ISLAND"]
    forest = by_id["SCENE_FOREST"]

    assert forest.orientation == "inverted"
    assert forest.spatial_mode == "suspended"
    assert forest.position.x == island.position.x
    assert forest.position.z == island.position.z
    assert forest.position.y < island.position.y


def test_spatial_semantics_compile_walkable_platform_on_aerial_organic_volume():
    plan = WorldScenePlan(
        source_mode="prompt",
        summary="A station garden sits on an aerial organic landmark.",
        route_intent="Climb toward the station and finish at the portal.",
        elements=[
            WorldSceneElement(
                scene_id="SCENE_CARRIER",
                name="Gentle Sky Carrier",
                semantic_key="sky_carrier",
                kind="landmark",
                source="creator_required",
                spatial_mode="aerial",
                elevation="high",
                geometry_role="organic",
                traversability="scenic",
            ),
            WorldSceneElement(
                scene_id="SCENE_STATION",
                name="Back Garden Station",
                semantic_key="back_garden_station",
                kind="terrain",
                source="creator_required",
                spatial_mode="elevated",
                elevation="high",
                geometry_role="platform",
                traversability="walkable",
                relations=[
                    WorldSceneRelation(
                        relation="on_top_of",
                        target_scene_ids=["SCENE_CARRIER"],
                    )
                ],
                photo_opportunity=True,
            ),
            WorldSceneElement(
                scene_id="SCENE_PORTAL",
                name="Moon Star Portal",
                semantic_key="moon_star_portal",
                kind="portal",
                source="creator_required",
                spatial_mode="aerial",
                elevation="high",
                geometry_role="arch",
                traversability="walkable",
                relations=[
                    WorldSceneRelation(
                        relation="on_top_of",
                        target_scene_ids=["SCENE_CARRIER"],
                    )
                ],
            ),
        ],
        exploration_order=["SCENE_STATION", "SCENE_PORTAL"],
        photo_spot_ids=["SCENE_STATION"],
    )
    profile = WorldProfile(world_name="Sky Station", portal_form="Moon Star Portal")

    blueprint = WorldBlueprintService().plan_from_scene_plan(
        location_asset_id="LOC_SKY_STATION",
        style_asset_id="STYLE_MINI",
        profile=profile,
        scene_plan=plan,
    )
    by_id = {item.element_id: item for item in blueprint.layout_elements}
    carrier = by_id["SCENE_CARRIER"]
    station = by_id["SCENE_STATION"]

    assert carrier.geometry_role == "organic"
    assert carrier.position.y >= 16
    assert station.position.y > carrier.position.y
    assert any(point.y > 0 for point in blueprint.paths[0].points)
    assert max(camera.position.y for camera in blueprint.camera_points) > 12

    html = build_world_runtime_html(
        world_name="Sky Station",
        profile=profile,
        blueprint=blueprint,
    )
    assert '"spatial_mode": "aerial"' in html
    assert '"geometry_role": "organic"' in html
    assert "function pathHeightAt" in html
    assert "role === 'organic'" in html


def test_prompt_negation_does_not_add_a_negated_lake_safety_object():
    payload = _prompt_payload()
    payload["scene_plan"]["elements"] = [
        item
        for item in payload["scene_plan"]["elements"]
        if item["scene_id"] != "SCENE_LAKE"
    ]
    provider = FakeStructuredProvider(payload)
    service = WorldScenePlanService(structured_provider=provider)

    result = service.plan_from_prompt(
        description=(
            "This world is not a lake and 不是湖泊. "
            "Its main feature is a waterfall floating in the sky."
        ),
        style_profile={},
    )

    keys = [item.semantic_key for item in result.scene_plan.elements]
    names = [item.name.lower() for item in result.scene_plan.elements]
    assert "lake" not in keys
    assert not any(name == "lake / 湖泊" for name in names)
    assert any(
        item.kind == "water" and item.semantic_key == "waterfall"
        for item in result.scene_plan.elements
    )


def test_semantic_key_prevents_duplicate_floating_island_safety_element():
    payload = _prompt_payload()
    payload["scene_plan"]["elements"].insert(
        0,
        {
            "scene_id": "SCENE_FLOATING_MASS",
            "name": "高低错落的漂浮岛群",
            "semantic_key": "floating_islands",
            "kind": "terrain",
            "source": "creator_required",
            "required": True,
            "spatial_mode": "floating",
            "elevation": "medium",
            "orientation": "normal",
            "geometry_role": "terrain_mass",
            "traversability": "walkable",
            "placement_hint": "",
            "relation_hints": [],
            "relations": [],
            "photo_opportunity": True,
            "notes": "",
        },
    )
    provider = FakeStructuredProvider(payload)
    service = WorldScenePlanService(structured_provider=provider)

    result = service.plan_from_prompt(
        description="A world made from floating islands / 漂浮岛.",
        style_profile={},
    )

    floating = [
        item
        for item in result.scene_plan.elements
        if item.semantic_key == "floating_islands"
    ]
    assert len(floating) == 1


def test_grounded_scene_regression_stays_grounded():
    plan = WorldScenePlan(
        source_mode="prompt",
        summary="Ordinary ground scene",
        route_intent="Walk from lake to castle to portal.",
        elements=[
            WorldSceneElement(
                scene_id="SCENE_LAKE",
                name="Lake",
                semantic_key="lake",
                kind="water",
                source="creator_required",
                geometry_role="surface",
                traversability="blocked",
                placement_hint="center",
            ),
            WorldSceneElement(
                scene_id="SCENE_CASTLE",
                name="Castle",
                semantic_key="castle",
                kind="structure",
                source="creator_required",
                geometry_role="volume",
                traversability="scenic",
                placement_hint="right of Lake",
            ),
            WorldSceneElement(
                scene_id="SCENE_PORTAL",
                name="Star Portal",
                semantic_key="star_portal",
                kind="portal",
                source="creator_required",
                geometry_role="arch",
                traversability="walkable",
                placement_hint="behind Lake",
            ),
        ],
        exploration_order=["SCENE_LAKE", "SCENE_CASTLE", "SCENE_PORTAL"],
    )
    blueprint = WorldBlueprintService().plan_from_scene_plan(
        location_asset_id="LOC_GROUND",
        style_asset_id="STYLE_MINI",
        profile=WorldProfile(world_name="Ground Garden", portal_form="Star Portal"),
        scene_plan=plan,
    )

    assert all(element.position.y == 0 for element in blueprint.layout_elements)


def test_prompt_system_maps_living_creatures_to_organic_geometry():
    provider = FakeStructuredProvider(_prompt_payload())
    service = WorldScenePlanService(structured_provider=provider)

    service.plan_from_prompt(
        description="A gentle living creature carries a station in the sky.",
        style_profile={},
    )

    system = provider.calls[0]["system"]
    assert "living creatures" in system
    assert "biological carriers" in system
    assert "geometry_role=organic" not in system
    assert "Use organic for living creatures" in system

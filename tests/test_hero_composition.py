from __future__ import annotations

from typing import Type

from pydantic import BaseModel

from studio.models.hero_composition import (
    HeroCompositionCluster,
    HeroCompositionMember,
    WorldHeroCompositionPlan,
)
from studio.models.world import (
    WorldBlueprint,
    WorldLayoutElement,
    WorldPoint,
    WorldProfile,
    WorldSceneElement,
    WorldScenePlan,
    WorldSceneRelation,
    WorldVisualAnchor,
)
from studio.providers.base import StructuredTextProvider
from studio.services.world_hero_composition_service import WorldHeroCompositionService


class FakeCompositionProvider(StructuredTextProvider):
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def generate_structured(self, *, system: str, user: str, schema: Type[BaseModel]):
        self.calls.append({"system": system, "user": user, "schema": schema})
        return schema.model_validate(self.payload)


class FailingCompositionProvider(StructuredTextProvider):
    def generate_structured(self, *, system: str, user: str, schema: Type[BaseModel]):
        raise TimeoutError("composition resolver timed out")


def _profile() -> WorldProfile:
    return WorldProfile(
        world_name="Cloud Whale Station",
        source_description=(
            "A gentle sky whale carries a flower station on its back. "
            "A lighthouse pavilion, moon portal and boarding walkway complete the station."
        ),
    )


def _scene_plan() -> WorldScenePlan:
    return WorldScenePlan(
        source_mode="prompt",
        summary="A dreamlike station carried by a gentle sky whale.",
        route_intent="Board the whale station and reach the moon portal.",
        elements=[
            WorldSceneElement(
                scene_id="SCENE_WHALE",
                name="Gentle Sky Whale",
                semantic_key="sky_whale",
                kind="landmark",
                source="creator_required",
                spatial_mode="aerial",
                elevation="high",
                geometry_role="organic",
                traversability="scenic",
            ),
            WorldSceneElement(
                scene_id="SCENE_GARDEN",
                name="Whale Back Garden Station",
                semantic_key="whale_back_garden",
                kind="terrain",
                source="creator_required",
                spatial_mode="elevated",
                elevation="high",
                geometry_role="platform",
                traversability="walkable",
                relations=[
                    WorldSceneRelation(
                        relation="on_top_of",
                        target_scene_ids=["SCENE_WHALE"],
                    )
                ],
            ),
            WorldSceneElement(
                scene_id="SCENE_LIGHTHOUSE",
                name="Lighthouse Pavilion",
                semantic_key="lighthouse_pavilion",
                kind="structure",
                source="creator_required",
                spatial_mode="elevated",
                elevation="high",
                geometry_role="volume",
                traversability="scenic",
                relations=[
                    WorldSceneRelation(
                        relation="on_top_of",
                        target_scene_ids=["SCENE_WHALE"],
                    )
                ],
            ),
            WorldSceneElement(
                scene_id="SCENE_PORTAL",
                name="Moon Portal",
                semantic_key="moon_portal",
                kind="portal",
                source="creator_required",
                geometry_role="arch",
                traversability="walkable",
                relations=[
                    WorldSceneRelation(
                        relation="attached_to",
                        target_scene_ids=["SCENE_WHALE"],
                    )
                ],
            ),
            WorldSceneElement(
                scene_id="SCENE_SIGN",
                name="Cloud Sign",
                semantic_key="cloud_sign",
                kind="decoration",
                source="utopia_enrichment",
                geometry_role="decorative",
                traversability="decorative",
            ),
        ],
        exploration_order=["SCENE_GARDEN", "SCENE_PORTAL"],
    )


def _blueprint() -> WorldBlueprint:
    elements = [
        WorldLayoutElement(
            element_id="SCENE_WHALE",
            name="Gentle Sky Whale",
            kind="landmark",
            semantic_key="sky_whale",
            spatial_mode="aerial",
            elevation="high",
            geometry_role="organic",
            traversability="scenic",
            position=WorldPoint(x=30, y=12, z=30),
            width=18,
            depth=9,
            height=8,
        ),
        WorldLayoutElement(
            element_id="SCENE_GARDEN",
            name="Whale Back Garden Station",
            kind="terrain",
            semantic_key="whale_back_garden",
            spatial_mode="elevated",
            elevation="high",
            geometry_role="platform",
            traversability="walkable",
            position=WorldPoint(x=30, y=18, z=30),
            width=10,
            depth=7,
            height=2,
        ),
        WorldLayoutElement(
            element_id="SCENE_LIGHTHOUSE",
            name="Lighthouse Pavilion",
            kind="structure",
            semantic_key="lighthouse_pavilion",
            spatial_mode="elevated",
            elevation="high",
            geometry_role="volume",
            traversability="scenic",
            position=WorldPoint(x=28, y=20, z=30),
            width=3,
            depth=3,
            height=5,
        ),
        WorldLayoutElement(
            element_id="SCENE_PORTAL",
            name="Moon Portal",
            kind="portal",
            semantic_key="moon_portal",
            geometry_role="arch",
            traversability="walkable",
            position=WorldPoint(x=33, y=20, z=30),
            width=4,
            depth=2,
            height=5,
        ),
        WorldLayoutElement(
            element_id="SCENE_SIGN",
            name="Cloud Sign",
            kind="decoration",
            semantic_key="cloud_sign",
            geometry_role="decorative",
            traversability="decorative",
            position=WorldPoint(x=10, y=0, z=10),
            width=2,
            depth=1,
            height=2,
        ),
    ]
    return WorldBlueprint(
        location_asset_id="LOC_COMPOSITION",
        visual_anchor=WorldVisualAnchor(
            concept_summary="A whale that reads as a living flying station.",
            must_preserve=["Gentle Sky Whale", "Whale Back Garden Station"],
            composition_notes=["The station should feel integrated with the whale."],
            spatial_relations=["Garden rides on the whale's back."],
        ),
        layout_elements=elements,
    )


def test_gpt_composition_preserves_intrinsic_and_attachment_roles():
    provider = FakeCompositionProvider(
        {
            "source": "gpt",
            "clusters": [
                {
                    "cluster_id": "HERO_CLUSTER_WHALE",
                    "root_element_id": "SCENE_WHALE",
                    "mode": "composite",
                    "concept_summary": "Living whale-station",
                    "members": [
                        {
                            "element_id": "SCENE_WHALE",
                            "role": "root",
                            "reason": "Primary living Hero.",
                        },
                        {
                            "element_id": "SCENE_GARDEN",
                            "role": "intrinsic",
                            "relation_to_root": "on_top_of",
                            "reason": "The garden/station is part of the creature-station silhouette.",
                        },
                        {
                            "element_id": "SCENE_LIGHTHOUSE",
                            "role": "attachment",
                            "relation_to_root": "on_top_of",
                            "reason": "Discrete pavilion.",
                        },
                        {
                            "element_id": "SCENE_PORTAL",
                            "role": "attachment",
                            "relation_to_root": "attached_to",
                            "reason": "Discrete portal.",
                        },
                    ],
                }
            ],
            "standalone_element_ids": ["SCENE_SIGN"],
        }
    )
    service = WorldHeroCompositionService(provider)

    plan = service.resolve(
        profile=_profile(),
        scene_plan=_scene_plan(),
        blueprint=_blueprint(),
    )

    assert plan.source == "gpt"
    assert len(plan.clusters) == 1
    cluster = plan.clusters[0]
    assert cluster.mode == "composite"
    assert cluster.root_element_id == "SCENE_WHALE"
    roles = {item.element_id: item.role for item in cluster.members}
    assert roles["SCENE_WHALE"] == "root"
    assert roles["SCENE_GARDEN"] == "intrinsic"
    assert roles["SCENE_LIGHTHOUSE"] == "attachment"
    assert roles["SCENE_PORTAL"] == "attachment"
    assert plan.standalone_element_ids == ["SCENE_SIGN"]
    assert provider.calls
    assert "visual/creative subject" in provider.calls[0]["system"]
    assert "Cloud Whale Station" not in provider.calls[0]["system"]
    assert "Gentle Sky Whale" in provider.calls[0]["user"]


def test_normalizer_drops_unknown_and_duplicate_ids_and_covers_every_blueprint_element():
    proposed = WorldHeroCompositionPlan(
        source="gpt",
        clusters=[
            HeroCompositionCluster(
                cluster_id="C1",
                root_element_id="SCENE_WHALE",
                members=[
                    HeroCompositionMember(element_id="SCENE_WHALE", role="root"),
                    HeroCompositionMember(element_id="SCENE_GARDEN", role="intrinsic"),
                    HeroCompositionMember(element_id="UNKNOWN", role="attachment"),
                    HeroCompositionMember(element_id="SCENE_GARDEN", role="attachment"),
                    HeroCompositionMember(element_id="SCENE_SIGN", role="standalone"),
                ],
            )
        ],
        standalone_element_ids=["UNKNOWN", "SCENE_GARDEN"],
    )

    normalized = WorldHeroCompositionService._normalize(
        proposed=proposed,
        blueprint=_blueprint(),
    )

    cluster_ids = [item.element_id for item in normalized.clusters[0].members]
    assert cluster_ids == ["SCENE_WHALE", "SCENE_GARDEN"]
    all_ids = set(cluster_ids) | set(normalized.standalone_element_ids)
    assert all_ids == {
        "SCENE_WHALE",
        "SCENE_GARDEN",
        "SCENE_LIGHTHOUSE",
        "SCENE_PORTAL",
        "SCENE_SIGN",
    }


def test_provider_failure_uses_conservative_typed_relation_fallback():
    service = WorldHeroCompositionService(FailingCompositionProvider())

    plan = service.resolve(
        profile=_profile(),
        scene_plan=_scene_plan(),
        blueprint=_blueprint(),
    )

    assert plan.source == "deterministic_fallback"
    cluster = plan.clusters[0]
    assert cluster.root_element_id == "SCENE_WHALE"
    roles = {item.element_id: item.role for item in cluster.members}
    assert roles["SCENE_GARDEN"] == "attachment"
    assert roles["SCENE_LIGHTHOUSE"] == "attachment"
    assert roles["SCENE_PORTAL"] == "attachment"
    assert "SCENE_SIGN" in plan.standalone_element_ids

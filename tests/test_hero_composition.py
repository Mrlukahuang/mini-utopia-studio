from __future__ import annotations

from typing import Type

from pydantic import BaseModel

from studio.models.hero_composition import WorldHeroCompositionPlan
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

    def generate_structured(self, *, system: str, user: str, schema: Type[BaseModel]):
        return schema.model_validate(self.payload)


class FailingCompositionProvider(StructuredTextProvider):
    def generate_structured(self, *, system: str, user: str, schema: Type[BaseModel]):
        raise TimeoutError("composition resolver timed out")


def _profile() -> WorldProfile:
    return WorldProfile(
        world_name="Cloud Whale Station",
        source_description=(
            "A gentle sky whale carries a flower station, lighthouse pavilion "
            "and moon portal as one magical flying station."
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
                        target_scene_ids=["SCENE_GARDEN"],
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
                        target_scene_ids=["SCENE_GARDEN"],
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
    specs = [
        ("SCENE_WHALE", "Gentle Sky Whale", "landmark", "organic", 18, 9, 8),
        ("SCENE_GARDEN", "Whale Back Garden Station", "terrain", "platform", 10, 7, 2),
        ("SCENE_LIGHTHOUSE", "Lighthouse Pavilion", "structure", "volume", 3, 3, 5),
        ("SCENE_PORTAL", "Moon Portal", "portal", "arch", 4, 2, 5),
        ("SCENE_SIGN", "Cloud Sign", "decoration", "decorative", 2, 1, 2),
    ]
    return WorldBlueprint(
        location_asset_id="LOC_COMPOSITION",
        visual_anchor=WorldVisualAnchor(
            concept_summary="One living flying whale station.",
            must_preserve=["Gentle Sky Whale", "Whale Back Garden Station"],
            composition_notes=["Keep the carried station as one Hero composition."],
            spatial_relations=["Garden rides on the whale's back."],
        ),
        layout_elements=[
            WorldLayoutElement(
                element_id=eid,
                name=name,
                kind=kind,
                semantic_key=eid.lower(),
                spatial_mode="aerial" if eid == "SCENE_WHALE" else "grounded",
                elevation="high",
                geometry_role=role,
                traversability="scenic",
                position=WorldPoint(x=30, y=12, z=30),
                width=w,
                depth=d,
                height=h,
            )
            for eid, name, kind, role, w, d, h in specs
        ],
    )


def test_gpt_plan_keeps_whole_hero_in_one_unified_glb():
    provider = FakeCompositionProvider(
        {
            "source": "gpt",
            "clusters": [
                {
                    "cluster_id": "HERO_CLUSTER_WHALE",
                    "root_element_id": "SCENE_WHALE",
                    "render_strategy": "unified_glb",
                    "members": [
                        {"element_id": "SCENE_WHALE", "role": "root"},
                        {"element_id": "SCENE_GARDEN", "role": "baked"},
                        {"element_id": "SCENE_LIGHTHOUSE", "role": "baked"},
                        {"element_id": "SCENE_PORTAL", "role": "baked"},
                    ],
                }
            ],
            "standalone_element_ids": ["SCENE_SIGN"],
        }
    )
    plan = WorldHeroCompositionService(provider).resolve(
        profile=_profile(),
        scene_plan=_scene_plan(),
        blueprint=_blueprint(),
    )
    cluster = plan.clusters[0]
    assert cluster.render_strategy == "unified_glb"
    assert [item.element_id for item in cluster.members] == [
        "SCENE_WHALE",
        "SCENE_GARDEN",
        "SCENE_LIGHTHOUSE",
        "SCENE_PORTAL",
    ]
    assert all(
        item.role == "baked"
        for item in cluster.members
        if item.element_id != "SCENE_WHALE"
    )
    assert plan.standalone_element_ids == ["SCENE_SIGN"]


def test_timeout_fallback_expands_cluster_through_typed_relations():
    plan = WorldHeroCompositionService(FailingCompositionProvider()).resolve(
        profile=_profile(),
        scene_plan=_scene_plan(),
        blueprint=_blueprint(),
    )
    assert plan.source == "deterministic_fallback"
    ids = {item.element_id for item in plan.clusters[0].members}
    assert ids == {
        "SCENE_WHALE",
        "SCENE_GARDEN",
        "SCENE_LIGHTHOUSE",
        "SCENE_PORTAL",
    }
    assert plan.standalone_element_ids == ["SCENE_SIGN"]


def test_normalization_keeps_every_blueprint_id_exactly_once():
    proposed = WorldHeroCompositionPlan.model_validate(
        {
            "source": "gpt",
            "clusters": [
                {
                    "cluster_id": "C1",
                    "root_element_id": "SCENE_WHALE",
                    "members": [
                        {"element_id": "SCENE_WHALE", "role": "root"},
                        {"element_id": "SCENE_GARDEN", "role": "baked"},
                        {"element_id": "SCENE_GARDEN", "role": "baked"},
                        {"element_id": "UNKNOWN", "role": "baked"},
                    ],
                }
            ],
        }
    )
    normalized = WorldHeroCompositionService._normalize(
        proposed=proposed,
        blueprint=_blueprint(),
    )
    ids = [
        item.element_id
        for cluster in normalized.clusters
        for item in cluster.members
    ] + normalized.standalone_element_ids
    assert len(ids) == len(set(ids))
    assert set(ids) == {
        "SCENE_WHALE",
        "SCENE_GARDEN",
        "SCENE_LIGHTHOUSE",
        "SCENE_PORTAL",
        "SCENE_SIGN",
    }

from __future__ import annotations

import json

from studio.models.hero_composition import (
    HeroCompositionCluster,
    HeroCompositionMember,
    WorldHeroCompositionPlan,
)
from studio.models.world import WorldBlueprint, WorldProfile, WorldScenePlan
from studio.providers.base import StructuredTextProvider


class WorldHeroCompositionService:
    """Resolve complete creative Heroes that will render as one GLB."""

    _COMPOSITION_RELATIONS = {
        "on_top_of",
        "attached_to",
        "inside",
        "around",
        "suspended_from",
        "connects_to",
    }

    def __init__(self, structured_provider: StructuredTextProvider | None = None):
        self.structured_provider = structured_provider

    def resolve(
        self,
        *,
        profile: WorldProfile,
        scene_plan: WorldScenePlan,
        blueprint: WorldBlueprint,
    ) -> WorldHeroCompositionPlan:
        fallback = self._fallback(scene_plan=scene_plan, blueprint=blueprint)
        if self.structured_provider is None:
            return fallback
        try:
            proposed = self.structured_provider.generate_structured(
                system=self._system_prompt(),
                user=self._user_prompt(
                    profile=profile,
                    scene_plan=scene_plan,
                    blueprint=blueprint,
                ),
                schema=WorldHeroCompositionPlan,
            )
        except Exception:
            return fallback
        normalized = self._normalize(proposed=proposed, blueprint=blueprint)
        return normalized.model_copy(update={"source": "gpt"})

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are the Mini Utopia Unified Hero Composition Resolver. "
            "A Hero is the complete imaginative visual subject, not one isolated mesh. "
            "If a fantasy idea depends on several parts reading as one whole, place all "
            "those Blueprint element IDs in the same Hero cluster. Every Hero cluster "
            "uses render_strategy=unified_glb: one reference composition and one GLB. "
            "Do not split Hero members for later visual reconstruction. Keep only "
            "genuinely unrelated surrounding scenery standalone."
        )

    @staticmethod
    def _user_prompt(
        *,
        profile: WorldProfile,
        scene_plan: WorldScenePlan,
        blueprint: WorldBlueprint,
    ) -> str:
        anchor = blueprint.visual_anchor
        return (
            "CREATOR INTENT\n"
            + profile.source_description
            + "\n\nSCENE PLAN\n"
            + scene_plan.model_dump_json(indent=2)
            + "\n\nBLUEPRINT\n"
            + blueprint.model_dump_json(indent=2)
            + "\n\nVISUAL ANCHOR\n"
            + json.dumps(
                {
                    "concept_summary": anchor.concept_summary,
                    "must_preserve": anchor.must_preserve,
                    "composition_notes": anchor.composition_notes,
                    "spatial_relations": anchor.spatial_relations,
                },
                ensure_ascii=False,
            )
            + "\n\nEvery Blueprint element must appear exactly once: inside one "
            "Hero cluster or in standalone_element_ids. Non-root cluster members "
            "must use role=baked."
        )

    def _fallback(
        self,
        *,
        scene_plan: WorldScenePlan,
        blueprint: WorldBlueprint,
    ) -> WorldHeroCompositionPlan:
        by_id = {item.element_id: item for item in blueprint.layout_elements}
        root = max(
            blueprint.layout_elements,
            key=self._hero_score,
            default=None,
        )
        if root is None or self._hero_score(root) <= 0:
            return WorldHeroCompositionPlan(
                standalone_element_ids=list(by_id),
                planning_note="No deterministic Hero root.",
            )

        claimed = {root.element_id}
        relation_by_id: dict[str, str] = {}
        changed = True
        while changed:
            changed = False
            for scene in scene_plan.elements:
                if scene.scene_id in claimed or scene.scene_id not in by_id:
                    continue
                relation = next(
                    (
                        rel.relation
                        for rel in scene.relations
                        if rel.relation in self._COMPOSITION_RELATIONS
                        and any(target in claimed for target in rel.target_scene_ids)
                    ),
                    "",
                )
                if relation:
                    claimed.add(scene.scene_id)
                    relation_by_id[scene.scene_id] = relation
                    changed = True

        members = [
            HeroCompositionMember(
                element_id=root.element_id,
                role="root",
                reason="Deterministic Hero root.",
            )
        ]
        for element in blueprint.layout_elements:
            if element.element_id in claimed and element.element_id != root.element_id:
                members.append(
                    HeroCompositionMember(
                        element_id=element.element_id,
                        role="baked",
                        relation_to_root=relation_by_id.get(element.element_id, ""),
                        reason="Typed composition relation keeps this element in the unified Hero.",
                    )
                )

        return WorldHeroCompositionPlan(
            source="deterministic_fallback",
            clusters=[
                HeroCompositionCluster(
                    cluster_id=f"HERO_CLUSTER_{root.element_id}",
                    root_element_id=root.element_id,
                    concept_summary=f"Unified Hero rooted at {root.name}.",
                    members=members,
                )
            ],
            standalone_element_ids=[
                element_id for element_id in by_id if element_id not in claimed
            ],
            planning_note="Related Hero parts are baked together; unrelated scenery stays standalone.",
        )

    @staticmethod
    def _hero_score(element) -> float:
        score = 0.0
        if element.geometry_role == "organic":
            score += 100
        if element.kind == "landmark":
            score += 50
        if element.spatial_mode in {"aerial", "floating", "suspended"}:
            score += 10
        score += min(30.0, max(element.width, element.depth, element.height))
        return score

    @staticmethod
    def _normalize(
        *,
        proposed: WorldHeroCompositionPlan,
        blueprint: WorldBlueprint,
    ) -> WorldHeroCompositionPlan:
        valid = {item.element_id for item in blueprint.layout_elements}
        claimed: set[str] = set()
        clusters = []
        for index, cluster in enumerate(proposed.clusters[:4]):
            root = cluster.root_element_id
            if root not in valid or root in claimed:
                continue
            members = [
                HeroCompositionMember(
                    element_id=root,
                    role="root",
                    reason="Normalized Hero root.",
                )
            ]
            claimed.add(root)
            for item in cluster.members:
                if item.element_id == root:
                    continue
                if item.element_id not in valid or item.element_id in claimed:
                    continue
                members.append(item.model_copy(update={"role": "baked"}))
                claimed.add(item.element_id)
            clusters.append(
                cluster.model_copy(
                    update={
                        "cluster_id": cluster.cluster_id or f"HERO_CLUSTER_{index+1:02d}",
                        "render_strategy": "unified_glb",
                        "members": members,
                    }
                )
            )
        return WorldHeroCompositionPlan(
            source=proposed.source,
            clusters=clusters,
            standalone_element_ids=[
                item.element_id
                for item in blueprint.layout_elements
                if item.element_id not in claimed
            ],
            planning_note=proposed.planning_note,
        )

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
    """Resolve creative Hero ownership without mutating Blueprint identity.

    The plan answers a rendering question only: which semantic objects should
    be generated as one visually fused Hero cluster, which should mount later,
    and which stay standalone.
    """

    def __init__(self, structured_provider: StructuredTextProvider | None = None):
        self.structured_provider = structured_provider

    @property
    def is_available(self) -> bool:
        return self.structured_provider is not None

    def resolve(
        self,
        *,
        profile: WorldProfile,
        scene_plan: WorldScenePlan,
        blueprint: WorldBlueprint,
    ) -> WorldHeroCompositionPlan:
        fallback = self._fallback(
            profile=profile,
            scene_plan=scene_plan,
            blueprint=blueprint,
        )
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

        normalized = self._normalize(
            proposed=proposed,
            blueprint=blueprint,
        )
        return normalized.model_copy(
            update={
                "source": "gpt",
                "planning_note": (
                    normalized.planning_note
                    or "Resolved from creator intent, Scene Plan relations and Visual Anchor."
                ),
            }
        )

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are the Mini Utopia Hero Composition Resolver.\n"
            "You are NOT changing the authoritative Blueprint. Every Blueprint "
            "element ID must remain addressable. Your only job is to decide render "
            "ownership for creative Hero subjects.\n\n"
            "A Hero is a visual/creative subject, not necessarily one object.\n"
            "Use these modes:\n"
            "- monolithic: root plus visually inseparable intrinsic members, no "
            "independently mounted members are required.\n"
            "- composite: root plus one or more intrinsic fused members AND one or "
            "more discrete attachments.\n"
            "- modular: root plus discrete attachments only.\n\n"
            "Member roles:\n"
            "- root: the visual/spatial owner of the cluster.\n"
            "- intrinsic: separation would materially destroy the original visual "
            "idea; examples include grown-from, fused-with, carved-into, shell-like "
            "or terrain that is itself part of the creature/vehicle/building body.\n"
            "- attachment: semantically separate and visually discrete even when "
            "mounted on, connected to, or carried by the root.\n"
            "- standalone: not part of this Hero cluster.\n\n"
            "Preserve imaginative composition. Do not reduce a compound fantasy "
            "idea into generic disconnected props. At the same time, do not bake "
            "ordinary discrete buildings, portals, signs or paths into a Hero merely "
            "because they are nearby. Prefer attachment when clean assembly is "
            "plausible. Prefer intrinsic only when visual fusion is essential.\n"
            "Return only the requested schema."
        )

    @staticmethod
    def _user_prompt(
        *,
        profile: WorldProfile,
        scene_plan: WorldScenePlan,
        blueprint: WorldBlueprint,
    ) -> str:
        layout = [
            {
                "element_id": item.element_id,
                "name": item.name,
                "kind": item.kind,
                "semantic_key": item.semantic_key,
                "geometry_role": item.geometry_role,
                "spatial_mode": item.spatial_mode,
                "traversability": item.traversability,
                "position": item.position.model_dump(mode="json"),
                "size": {
                    "width": item.width,
                    "depth": item.depth,
                    "height": item.height,
                },
            }
            for item in blueprint.layout_elements
        ]
        anchor = blueprint.visual_anchor
        return (
            "CREATOR INTENT\n"
            + profile.source_description
            + "\n\nSCENE PLAN\n"
            + scene_plan.model_dump_json(indent=2)
            + "\n\nBLUEPRINT ELEMENTS\n"
            + json.dumps(layout, ensure_ascii=False, indent=2)
            + "\n\nVISUAL ANCHOR\n"
            + json.dumps(
                {
                    "concept_summary": anchor.concept_summary,
                    "must_preserve": anchor.must_preserve,
                    "composition_notes": anchor.composition_notes,
                    "spatial_relations": anchor.spatial_relations,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n\nREQUIREMENTS\n"
            + "- Use Blueprint element_id values exactly.\n"
            + "- Every Blueprint element must appear exactly once globally: either "
            "as one cluster member or in standalone_element_ids.\n"
            + "- A cluster must contain exactly one root.\n"
            + "- Keep only genuine Hero clusters; ordinary unrelated objects remain standalone.\n"
            + "- Explain intrinsic/attachment choices briefly in reason."
        )

    def _fallback(
        self,
        *,
        profile: WorldProfile,
        scene_plan: WorldScenePlan,
        blueprint: WorldBlueprint,
    ) -> WorldHeroCompositionPlan:
        by_id = {item.element_id: item for item in blueprint.layout_elements}
        scene_by_id = {item.scene_id: item for item in scene_plan.elements}

        root = max(
            blueprint.layout_elements,
            key=lambda item: self._hero_score(item),
            default=None,
        )
        if root is None or self._hero_score(root) <= 0:
            return WorldHeroCompositionPlan(
                source="deterministic_fallback",
                standalone_element_ids=list(by_id),
                planning_note="No deterministic Hero root candidate.",
            )

        members = [
            HeroCompositionMember(
                element_id=root.element_id,
                role="root",
                reason="Highest-value deterministic Hero root candidate.",
            )
        ]
        claimed = {root.element_id}

        for scene in scene_plan.elements:
            if scene.scene_id == root.element_id or scene.scene_id not in by_id:
                continue
            relation_to_root = next(
                (
                    relation.relation
                    for relation in scene.relations
                    if root.element_id in relation.target_scene_ids
                ),
                "",
            )
            if relation_to_root not in {
                "on_top_of",
                "attached_to",
                "inside",
                "around",
                "suspended_from",
                "connects_to",
            }:
                continue

            # Conservative fallback: typed relations establish cluster membership,
            # but only explicit fused language upgrades a member to intrinsic.
            text = " ".join(
                [
                    profile.source_description,
                    scene.placement_hint,
                    *scene.relation_hints,
                    scene.notes,
                ]
            ).lower()
            intrinsic_words = (
                "fused",
                "grown from",
                "growing from",
                "part of its body",
                "built into",
                "carved into",
                "integrated into",
                "inseparable",
            )
            role = (
                "intrinsic"
                if any(word in text for word in intrinsic_words)
                else "attachment"
            )
            members.append(
                HeroCompositionMember(
                    element_id=scene.scene_id,
                    role=role,
                    relation_to_root=relation_to_root,
                    reason=(
                        "Explicit fused-language Scene relation."
                        if role == "intrinsic"
                        else "Typed Scene relation to Hero root; kept discrete by default."
                    ),
                )
            )
            claimed.add(scene.scene_id)

        intrinsic = any(item.role == "intrinsic" for item in members)
        attachment = any(item.role == "attachment" for item in members)
        mode = (
            "composite"
            if intrinsic and attachment
            else "monolithic"
            if intrinsic
            else "modular"
            if attachment
            else "monolithic"
        )
        return WorldHeroCompositionPlan(
            source="deterministic_fallback",
            clusters=[
                HeroCompositionCluster(
                    cluster_id=f"HERO_CLUSTER_{root.element_id}",
                    root_element_id=root.element_id,
                    mode=mode,
                    concept_summary=(
                        f"Deterministic Hero cluster rooted at {root.name}."
                    ),
                    members=members,
                )
            ],
            standalone_element_ids=[
                element_id for element_id in by_id if element_id not in claimed
            ],
            planning_note=(
                "Conservative deterministic fallback: typed Scene relations become "
                "attachments unless creator text explicitly says they are fused."
            ),
        )

    @staticmethod
    def _hero_score(element) -> float:
        size = max(element.width, element.depth, element.height)
        score = 0.0
        if element.geometry_role == "organic":
            score += 100.0
        if element.kind == "landmark":
            score += 50.0
        if element.kind == "structure":
            score += 20.0
        if element.spatial_mode in {"aerial", "floating", "suspended"}:
            score += 10.0
        score += min(30.0, size)
        return score if score >= 40.0 else 0.0

    @staticmethod
    def _normalize(
        *,
        proposed: WorldHeroCompositionPlan,
        blueprint: WorldBlueprint,
    ) -> WorldHeroCompositionPlan:
        valid_ids = {item.element_id for item in blueprint.layout_elements}
        claimed: set[str] = set()
        clusters: list[HeroCompositionCluster] = []

        for index, cluster in enumerate(proposed.clusters[:4]):
            root_id = cluster.root_element_id
            if root_id not in valid_ids or root_id in claimed:
                continue

            members: list[HeroCompositionMember] = [
                HeroCompositionMember(
                    element_id=root_id,
                    role="root",
                    reason=next(
                        (
                            item.reason
                            for item in cluster.members
                            if item.element_id == root_id
                        ),
                        "Normalized Hero root.",
                    ),
                )
            ]
            claimed.add(root_id)

            for item in cluster.members:
                if item.element_id == root_id:
                    continue
                if item.element_id not in valid_ids or item.element_id in claimed:
                    continue
                if item.role not in {"intrinsic", "attachment"}:
                    continue
                members.append(item)
                claimed.add(item.element_id)

            has_intrinsic = any(item.role == "intrinsic" for item in members)
            has_attachment = any(item.role == "attachment" for item in members)
            mode = (
                "composite"
                if has_intrinsic and has_attachment
                else "monolithic"
                if has_intrinsic
                else "modular"
                if has_attachment
                else "monolithic"
            )
            clusters.append(
                cluster.model_copy(
                    update={
                        "cluster_id": cluster.cluster_id
                        or f"HERO_CLUSTER_{index+1:02d}",
                        "root_element_id": root_id,
                        "mode": mode,
                        "members": members,
                    }
                )
            )

        standalone = []
        for element in blueprint.layout_elements:
            if element.element_id in claimed:
                continue
            standalone.append(element.element_id)
            claimed.add(element.element_id)

        return WorldHeroCompositionPlan(
            source=proposed.source,
            clusters=clusters,
            standalone_element_ids=standalone,
            planning_note=proposed.planning_note,
        )

from __future__ import annotations

import json
import re

from studio.models.world import (
    WorldPromptInterpretation,
    WorldProfile,
    WorldSceneElement,
    WorldScenePlan,
)
from studio.providers.base import StructuredTextProvider
from studio.services.world_route_planner_service import WorldRoutePlannerService


_DEFAULT_PORTAL = "Star Arch / 星星拱门"
_DEFAULT_COLORS = ["#F7B7D2", "#B9E7D0", "#D7C2F3"]

_OBVIOUS_OBJECTS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("lake", "湖泊", "湖"), "Lake / 湖泊", "water"),
    (("river", "河流", "河"), "River / 河流", "water"),
    (("waterfall", "瀑布"), "Waterfall / 瀑布", "water"),
    (("ocean", "海洋", "大海"), "Ocean / 海洋", "water"),
    (("pond", "池塘"), "Pond / 池塘", "water"),
    (("castle", "城堡"), "Castle / 城堡", "structure"),
    (("tower", "塔"), "Tower / 塔", "structure"),
    (("temple", "神殿", "寺庙"), "Temple / 神殿", "structure"),
    (("tree house", "treehouse", "树屋"), "Tree House / 树屋", "structure"),
    (("bridge", "桥"), "Bridge / 桥", "bridge"),
    (("portal", "传送门"), "Portal / 传送门", "portal"),
    (("star arch", "星星拱门", "星门"), "Star Arch / 星星拱门", "portal"),
    (("flower", "flowers", "花海", "花朵"), "Flowers / 花海", "decoration"),
    (("glow plant", "glowing plant", "发光植物"), "Glow Plants / 发光植物", "decoration"),
    (("floating island", "floating islands", "漂浮岛"), "Floating Islands / 漂浮岛", "terrain"),
    (("forest", "森林"), "Forest / 森林", "terrain"),
    (("mountain", "mountains", "山地", "山"), "Mountains / 山地", "terrain"),
    (("cave", "洞穴"), "Cave / 洞穴", "landmark"),
)


class WorldScenePlanService:
    """Create the shared semantic Scene Plan for Prompt and Custom creation."""

    def __init__(
        self,
        structured_provider: StructuredTextProvider | None = None,
        route_planner: WorldRoutePlannerService | None = None,
    ):
        self.structured_provider = structured_provider
        self.route_planner = route_planner or WorldRoutePlannerService()

    @property
    def prompt_available(self) -> bool:
        return self.structured_provider is not None

    def plan_from_prompt(
        self,
        *,
        description: str,
        style_profile: dict,
    ) -> WorldPromptInterpretation:
        if self.structured_provider is None:
            raise RuntimeError("Prompt World planning is not configured.")
        description = description.strip()
        if not description:
            raise ValueError("World description must not be empty.")

        system = """You are the Mini Utopia World Planner.

Convert one creator prompt into a structured, playable Scene Plan BEFORE any
image is generated. The creator's explicit idea is sacred. First identify every
important object, place, terrain/water feature and spatial relationship they
asked for. Mark those elements source=creator_required and required=true.

Then perform CONTROLLED UTOPIA ENRICHMENT: add at most 3 small supporting
elements that make the world feel unmistakably Mini Utopia without replacing
or competing with the creator's premise. Good enrichment includes child-friendly
wonder, warm discovery, miniature toy-like details, macaron-compatible glow,
environmental storytelling, a scenic/photo moment, or a connective path detail.
Mark those source=utopia_enrichment and required=false.

Design a natural exploration experience. exploration_order should start with
welcoming discoveries, visit the creator's important landmarks, include useful
photo opportunities, and end with a satisfying main Portal reveal. Do not put
the walking route through the center of lakes or other blocked water.

Use relative semantic placement, not exact runtime coordinates. Examples:
"center", "right side", "behind Lake", "between Lake and Castle". The deterministic
50x50 compiler will assign and validate exact coordinates later.

Return concise names and stable scene_id values such as SCENE_LAKE,
SCENE_CASTLE, SCENE_PORTAL. There should be one clear main Portal. If the creator
did not mention a Portal, add one as source=system_required so the world remains
connected to Mini Utopia.

Keep the result original, warm, approachable and child-friendly. Never copy a
branded game/world. Do not invent a second competing theme."""

        style_context = {
            "visual_dna_pillars": style_profile.get("visual_dna_pillars", []),
            "shape_language": style_profile.get("shape_language", ""),
            "world_geometry_language": style_profile.get("world_geometry_language", ""),
            "environment_scale_language": style_profile.get("environment_scale_language", ""),
            "color_harmony_rule": style_profile.get("color_harmony_rule", ""),
            "palette_notes": style_profile.get("palette_notes", ""),
            "portal_language": style_profile.get("portal_language", ""),
            "positive_rules": style_profile.get("positive_rules", []),
            "locked_rules": style_profile.get("locked_rules", []),
        }
        user = (
            "CREATOR PROMPT\n"
            + description
            + "\n\nMINI UTOPIA STYLE CANON\n"
            + json.dumps(style_context, ensure_ascii=False)
            + "\n\nCreate the Prompt interpretation and shared Scene Plan now."
        )
        raw = self.structured_provider.generate_structured(
            system=system,
            user=user,
            schema=WorldPromptInterpretation,
        )
        interpretation = WorldPromptInterpretation.model_validate(raw)
        normalized_plan = self._normalize_plan(
            interpretation.scene_plan,
            source_mode="prompt",
            fallback_portal=interpretation.portal_form or _DEFAULT_PORTAL,
        )
        normalized_plan = self._ensure_obvious_prompt_objects(
            normalized_plan,
            description,
        )
        normalized_plan = self.route_planner.normalize(normalized_plan)
        colors = [
            value for value in interpretation.theme_color_hexes
            if self._is_hex(value)
        ][:5] or list(_DEFAULT_COLORS)
        return interpretation.model_copy(
            update={
                "world_name": interpretation.world_name.strip() or "New Mini World",
                "portal_form": interpretation.portal_form.strip() or _DEFAULT_PORTAL,
                "theme_color_hexes": colors,
                "scene_plan": normalized_plan,
            }
        )

    def plan_from_profile(
        self,
        *,
        profile: WorldProfile,
        style_profile: dict | None = None,
    ) -> WorldScenePlan:
        """Build a deterministic Custom Scene Plan, optionally interpreting Extra Details."""
        base = self._deterministic_custom_plan(profile)
        if (
            profile.creator_extra_details.strip()
            and self.structured_provider is not None
        ):
            base = self._supplement_custom_extra(
                profile=profile,
                base=base,
                style_profile=style_profile or {},
            )
        return self.route_planner.normalize(
            self._normalize_plan(
                base,
                source_mode="custom",
                fallback_portal=(
                    profile.portal_form
                    if profile.portal_form
                    and not profile.portal_form.lower().startswith("custom /")
                    else _DEFAULT_PORTAL
                ),
            )
        )

    def _deterministic_custom_plan(self, profile: WorldProfile) -> WorldScenePlan:
        elements: list[WorldSceneElement] = []

        def add(
            name: str,
            kind: str,
            *,
            placement_hint: str = "",
            photo: bool = False,
        ) -> None:
            clean = (name or "").strip()
            if (
                not clean
                or clean.lower().startswith("none /")
                or clean.lower().startswith("custom /")
            ):
                return
            if any(self._equivalent(item.name, clean) for item in elements):
                return
            elements.append(
                WorldSceneElement(
                    scene_id=f"SCENE_{len(elements)+1:02d}",
                    name=clean,
                    kind=kind,
                    source="custom_selection",
                    required=True,
                    placement_hint=placement_hint,
                    photo_opportunity=photo,
                )
            )

        for terrain in profile.terrain:
            add(terrain, "terrain")
        for water in profile.water_features:
            add(water, "water", placement_hint="central scenic area", photo=True)
        for landmark in profile.landmark_ideas:
            add(landmark, self._infer_kind(landmark), photo=True)
        for landscape in profile.landscape_elements:
            add(landscape, self._infer_kind(landscape, default="decoration"))
        for surprise in profile.surprise_elements:
            add(surprise, self._infer_kind(surprise, default="decoration"), photo=True)

        portal_name = (
            profile.portal_form
            if profile.portal_form
            and not profile.portal_form.lower().startswith("custom /")
            else _DEFAULT_PORTAL
        )
        add(
            portal_name,
            "portal",
            placement_hint=profile.portal_placement_idea or "final reveal area",
            photo=True,
        )

        relations = [
            value.strip()
            for value in [
                profile.portal_placement_idea,
                profile.creator_extra_details,
            ]
            if value and value.strip()
        ]
        return WorldScenePlan(
            source_mode="custom",
            summary=(
                f"{profile.world_name or 'Mini World'} · "
                f"{profile.world_type or 'Custom World'} · "
                f"{' / '.join(profile.mood) if profile.mood else 'Mini Utopia'}"
            ),
            route_intent=profile.traversability_notes or (
                "Natural walkable discovery route with scenic/photo moments "
                "and a final Portal reveal."
            ),
            elements=elements,
            spatial_relations=relations,
            exploration_order=[
                item.scene_id
                for item in elements
                if item.kind not in {"terrain", "decoration", "portal"}
            ] + [
                item.scene_id for item in elements if item.kind == "portal"
            ],
            photo_spot_ids=[
                item.scene_id for item in elements if item.photo_opportunity
            ][:8],
            enrichment_notes=[],
        )

    def _supplement_custom_extra(
        self,
        *,
        profile: WorldProfile,
        base: WorldScenePlan,
        style_profile: dict,
    ) -> WorldScenePlan:
        system = """You are refining a Custom Build Mini Utopia Scene Plan.
All existing elements are LOCKED custom selections: keep them all. Read only
the creator's Extra Details for missing objects or spatial relations. You may
add at most 2 supporting elements if the Extra Details clearly requests them
or if a tiny Mini Utopia connective detail is useful. Never remove or rename
locked elements. Preserve a walkable discovery/photo route ending at the Portal.
Return a complete WorldScenePlan."""
        user = (
            "LOCKED BASE PLAN\n"
            + base.model_dump_json()
            + "\n\nEXTRA DETAILS\n"
            + profile.creator_extra_details
            + "\n\nSTYLE CANON\n"
            + json.dumps(
                {
                    "visual_dna_pillars": style_profile.get("visual_dna_pillars", []),
                    "portal_language": style_profile.get("portal_language", ""),
                    "color_harmony_rule": style_profile.get("color_harmony_rule", ""),
                },
                ensure_ascii=False,
            )
        )
        candidate = WorldScenePlan.model_validate(
            self.structured_provider.generate_structured(
                system=system,
                user=user,
                schema=WorldScenePlan,
            )
        )
        locked_names = {self._norm(item.name): item for item in base.elements}
        merged = list(base.elements)
        for item in candidate.elements:
            if self._norm(item.name) in locked_names:
                continue
            merged.append(
                item.model_copy(
                    update={
                        "source": "utopia_enrichment",
                        "required": False,
                    }
                )
            )
            if len(merged) >= len(base.elements) + 2:
                break
        return candidate.model_copy(
            update={
                "source_mode": "custom",
                "elements": merged,
                "summary": candidate.summary or base.summary,
            }
        )

    def _normalize_plan(
        self,
        plan: WorldScenePlan,
        *,
        source_mode: str,
        fallback_portal: str,
    ) -> WorldScenePlan:
        enrichment_count = 0
        elements: list[WorldSceneElement] = []
        old_to_new: dict[str, str] = {}
        needs_system_portal = not any(
            item.kind == "portal" for item in plan.elements
        )
        max_before_portal = 15 if needs_system_portal else 16

        for item in plan.elements:
            name = item.name.strip()
            if not name:
                continue
            source = item.source
            kind = item.kind
            if kind == "portal" and any(
                token in name.lower() for token in ("plaza", "square", "广场")
            ):
                kind = "structure"
            if source == "utopia_enrichment":
                if enrichment_count >= 3:
                    continue
                enrichment_count += 1
            if any(
                existing.kind == kind
                and self._equivalent(existing.name, name)
                for existing in elements
            ):
                continue
            new_id = f"SCENE_{len(elements)+1:02d}"
            old_to_new[item.scene_id] = new_id
            elements.append(
                item.model_copy(
                    update={
                        "scene_id": new_id,
                        "name": name,
                        "kind": kind,
                        "required": source != "utopia_enrichment",
                    }
                )
            )
            if len(elements) >= max_before_portal:
                break

        if not any(item.kind == "portal" for item in elements):
            elements.append(
                WorldSceneElement(
                    scene_id=f"SCENE_{len(elements)+1:02d}",
                    name=fallback_portal or _DEFAULT_PORTAL,
                    kind="portal",
                    source="system_required",
                    required=True,
                    placement_hint="final reveal area",
                    photo_opportunity=True,
                    notes="Mini Utopia continuity Portal",
                )
            )

        order = [
            old_to_new.get(scene_id, scene_id)
            for scene_id in plan.exploration_order
        ]
        photos = [
            old_to_new.get(scene_id, scene_id)
            for scene_id in plan.photo_spot_ids
        ]
        return plan.model_copy(
            update={
                "source_mode": source_mode,
                "elements": elements,
                "exploration_order": order,
                "photo_spot_ids": photos,
            }
        )

    def _ensure_obvious_prompt_objects(
        self,
        plan: WorldScenePlan,
        description: str,
    ) -> WorldScenePlan:
        text = description.lower()
        elements = list(plan.elements)
        for keywords, canonical, kind in _OBVIOUS_OBJECTS:
            if not any(keyword in text for keyword in keywords):
                continue
            if kind == "portal" and any(item.kind == "portal" for item in elements):
                continue
            if any(
                self._equivalent(item.name, canonical)
                or any(keyword in item.name.lower() for keyword in keywords)
                for item in elements
            ):
                continue
            if len(elements) >= 16:
                removable = next(
                    (
                        index
                        for index in range(len(elements) - 1, -1, -1)
                        if elements[index].source == "utopia_enrichment"
                    ),
                    None,
                )
                if removable is None:
                    continue
                elements.pop(removable)
            elements.append(
                WorldSceneElement(
                    scene_id=f"SCENE_{len(elements)+1:02d}",
                    name=canonical,
                    kind=kind,
                    source="creator_required",
                    required=True,
                    placement_hint="",
                    relation_hints=[],
                    photo_opportunity=kind in {"portal", "water", "structure", "landmark"},
                    notes="Deterministic safeguard for an explicit creator object.",
                )
            )

        normalized = plan.model_copy(
            update={
                "elements": elements,
                "spatial_relations": list(dict.fromkeys(
                    [*plan.spatial_relations, description]
                )),
            }
        )
        # Re-normalize IDs after deterministic safeguards.
        return self._normalize_plan(
            normalized,
            source_mode="prompt",
            fallback_portal=next(
                (item.name for item in elements if item.kind == "portal"),
                _DEFAULT_PORTAL,
            ),
        )

    @staticmethod
    def _infer_kind(name: str, default: str = "landmark") -> str:
        lowered = name.lower()
        if any(token in lowered for token in ("plaza", "square", "广场")):
            return "structure"
        mapping = (
            ("portal", ("portal", "gate", "arch", "传送门", "拱门")),
            ("water", ("lake", "river", "water", "waterfall", "ocean", "湖", "河", "水", "瀑布", "海")),
            ("bridge", ("bridge", "桥")),
            ("structure", ("castle", "tower", "house", "temple", "plaza", "城堡", "塔", "屋", "殿", "广场")),
            ("terrain", ("island", "mountain", "forest", "meadow", "cliff", "岛", "山", "森林", "草地", "悬崖")),
        )
        for kind, keywords in mapping:
            if any(keyword in lowered for keyword in keywords):
                return kind
        return default

    @classmethod
    def _equivalent(cls, left: str, right: str) -> bool:
        a = set(cls._norm(left).split())
        b = set(cls._norm(right).split())
        return bool(a and b and (a == b or a <= b or b <= a))

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"[^a-z0-9\u4e00-\u9fff ]+", " ", value.lower()).strip()

    @staticmethod
    def _is_hex(value: str) -> bool:
        return bool(re.fullmatch(r"#[0-9A-Fa-f]{6}", value or ""))

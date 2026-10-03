from __future__ import annotations

import json
import re

from studio.models.world import (
    SCENE_PLAN_SCHEMA_VERSION,
    WorldPromptInterpretation,
    WorldProfile,
    WorldSceneElement,
    WorldScenePlan,
)
from studio.providers.base import StructuredTextProvider
from studio.services.world_route_planner_service import WorldRoutePlannerService


_DEFAULT_PORTAL = "Star Arch / 星星拱门"
_DEFAULT_COLORS = ["#F7B7D2", "#B9E7D0", "#D7C2F3"]

_OBVIOUS_OBJECTS: tuple[tuple[tuple[str, ...], str, str, str], ...] = (
    (("lake", "湖泊", "湖"), "Lake / 湖泊", "water", "lake"),
    (("river", "河流", "河"), "River / 河流", "water", "river"),
    (("waterfall", "瀑布"), "Waterfall / 瀑布", "water", "waterfall"),
    (("ocean", "海洋", "大海"), "Ocean / 海洋", "water", "ocean"),
    (("pond", "池塘"), "Pond / 池塘", "water", "pond"),
    (("castle", "城堡"), "Castle / 城堡", "structure", "castle"),
    (("tower", "塔"), "Tower / 塔", "structure", "tower"),
    (("temple", "神殿", "寺庙"), "Temple / 神殿", "structure", "temple"),
    (("tree house", "treehouse", "树屋"), "Tree House / 树屋", "structure", "tree_house"),
    (("bridge", "桥"), "Bridge / 桥", "bridge", "bridge"),
    (("portal", "传送门"), "Portal / 传送门", "portal", "portal"),
    (("star arch", "星星拱门", "星门"), "Star Arch / 星星拱门", "portal", "star_arch"),
    (("flower", "flowers", "花海", "花朵"), "Flowers / 花海", "decoration", "flowers"),
    (("glow plant", "glowing plant", "发光植物"), "Glow Plants / 发光植物", "decoration", "glow_plants"),
    (("floating island", "floating islands", "漂浮岛"), "Floating Islands / 漂浮岛", "terrain", "floating_islands"),
    (("forest", "森林"), "Forest / 森林", "terrain", "forest"),
    (("mountain", "mountains", "山地", "山"), "Mountains / 山地", "terrain", "mountains"),
    (("cave", "洞穴"), "Cave / 洞穴", "landmark", "cave"),
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
image is generated.

CREATOR WORLD LAW:
The creator's explicit imaginative rule is sacred. Do not "correct" impossible
ideas back to normal real-world physics. If the creator says a waterfall floats
in the sky, a forest grows upside-down, or a creature carries a station on its
back, accept that as the physics of this world. Your job is to make the nearby
world coherent, traversable and visually supportive of that rule.

First identify every important object, place, terrain/water feature and spatial
relationship they asked for. Mark those elements source=creator_required and
required=true. Respect explicit negation: if the creator says "not a lake",
"没有湖", "不是湖", "不要湖" or equivalent, do not create that negated object.

Then perform CONTROLLED UTOPIA ENRICHMENT: add at most 3 small supporting
elements that make the world feel unmistakably Mini Utopia without replacing
or competing with the creator's premise. Good enrichment includes child-friendly
wonder, warm discovery, miniature toy-like details, macaron-compatible glow,
environmental storytelling, a scenic/photo moment, or a connective path detail.
Mark those source=utopia_enrichment and required=false.

Design a natural exploration experience, not merely the shortest connection
between objects. The route must work for PLAYABILITY, PHOTOGRAPHY and VIDEO:

- Keep walking progression naturally traversable; never route through the center
  of blocked water or other non-walkable obstacles.
- Create 2-4 meaningful scenic/photo stopping moments where the world supports it.
- Design useful video beats: establishing arrival, follow movement, landmark
  reveal, scenic pause/photo moment, final Portal reveal, and an ending view.
- Preserve sightlines and breathing room between major landmarks. Avoid placing
  every important object on one straight line or crowding everything into one area.
- Use turns, foreground/background layering, height changes or gentle detours when
  they improve discovery without making the route confusing.
- The Portal should remain a satisfying late/final reveal unless the creator
  explicitly asks otherwise.

exploration_order should begin with welcoming discoveries, visit the creator's
important landmarks in a satisfying sequence, include useful photo/video moments,
and normally end with the main Portal reveal.

Use relative semantic placement, not exact runtime coordinates. The deterministic
compiler will assign exact x/y/z coordinates later.

For EVERY Scene element also describe its generic spatial semantics:
- semantic_key: short lower_snake_case concept identity used for dedupe.
- spatial_mode: grounded, elevated, floating, aerial, underground or suspended.
- elevation: ground, low, medium or high.
- orientation: normal, inverted, vertical, horizontal or tilted.
- geometry_role: surface, volume, platform, bridge, vertical_flow, path, organic,
  arch, terrain_mass or decorative.
  Use organic for living creatures, biological carriers, soft creature bodies,
  giant animals, plant-like living bodies, or other non-built organic subjects.
  Use volume for built/artificial solid masses or generic architectural objects.
- traversability: walkable, scenic, blocked, decorative or rideable.
- relations: typed relationships to other scene_id values, using left_of,
  right_of, behind, in_front_of, near, above, below, on_top_of, under, inside,
  attached_to, suspended_from, around, between, connects_to or flows_to.

Examples of the LANGUAGE, not object-specific rules:
- A high floating vertical flow can be spatial_mode=aerial,
  geometry_role=vertical_flow and relation flows_to a lower target.
- Something growing from the underside of a floating mass can be
  spatial_mode=suspended, orientation=inverted, relation=under or suspended_from.
- A walkable garden carried by another object can be geometry_role=platform,
  traversability=walkable and relation=on_top_of that object.

Use placement_hint for coarse composition such as "center", "right side",
"behind the lake". Use typed relations whenever another Scene element is the
reference. Think about walkable approach direction, camera sightlines and reveal
order.

Return concise names and stable scene_id values such as SCENE_01, SCENE_02.
There should be one clear main Portal. If the creator did not mention a Portal,
add one as source=system_required so the world remains connected to Mini Utopia.

COLOR RULES:
- If the creator explicitly names colors, preserve those as the world identity.
- Harmonize them with Mini Utopia's high-lightness, low-to-medium-saturation
  macaron constitution rather than replacing them.
- If the creator gives no colors, choose 3-5 coherent theme HEX colors from the
  Mini Utopia palette families supplied below.
- Enrichment colors support the creator's palette; they must not create a second
  competing palette.

Keep the result original, warm, approachable and child-friendly. Never copy a
branded game/world. Do not invent a second competing theme."""

        style_context = {
            "visual_dna_pillars": style_profile.get("visual_dna_pillars", []),
            "shape_language": style_profile.get("shape_language", ""),
            "world_geometry_language": style_profile.get("world_geometry_language", ""),
            "environment_scale_language": style_profile.get("environment_scale_language", ""),
            "color_harmony_rule": style_profile.get("color_harmony_rule", ""),
            "palette_notes": style_profile.get("palette_notes", ""),
            "macaron_palette": style_profile.get("macaron_palette", {}),
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
            try:
                base = self._supplement_custom_extra(
                    profile=profile,
                    base=base,
                    style_profile=style_profile or {},
                )
            except Exception:
                # Custom Build must remain deterministic and usable even if the
                # optional free-text supplement provider is temporarily unavailable.
                pass
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
                    semantic_key=self._semantic_key(clean, kind),
                    kind=kind,
                    source="custom_selection",
                    required=True,
                    spatial_mode="grounded",
                    elevation="ground",
                    orientation="normal",
                    geometry_role=self._default_geometry_role(kind),
                    traversability=self._default_traversability(kind),
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

        portal_candidates = [
            (index, item)
            for index, item in enumerate(plan.elements)
            if item.kind == "portal"
            and not any(
                token in item.name.lower()
                for token in ("plaza", "square", "广场")
            )
        ]
        main_portal_index = next(
            (
                index
                for index, item in portal_candidates
                if item.source == "creator_required"
            ),
            portal_candidates[0][0] if portal_candidates else None,
        )
        needs_system_portal = main_portal_index is None
        max_before_portal = 15 if needs_system_portal else 16

        for index, item in enumerate(plan.elements):
            name = item.name.strip()
            if not name:
                continue
            source = item.source
            kind = item.kind
            notes = item.notes
            semantic_key = (
                item.semantic_key.strip().lower().replace(" ", "_")
                if item.semantic_key.strip()
                else self._semantic_key(name, kind)
            )
            if (
                source == "utopia_enrichment"
                and kind == "structure"
                and any(
                    token in name.lower()
                    for token in ("path", "trail", "walkway", "小径", "步道", "小路")
                )
            ):
                kind = "decoration"
            if kind == "portal" and any(
                token in name.lower() for token in ("plaza", "square", "广场")
            ):
                kind = "structure"
            elif kind == "portal" and index != main_portal_index:
                kind = "landmark"
                notes = (
                    (notes + " ").strip()
                    + "Secondary portal-like feature; not the executable main Portal."
                ).strip()
            if source == "utopia_enrichment":
                if enrichment_count >= 3:
                    continue
                enrichment_count += 1
            if any(
                (
                    semantic_key
                    and existing.semantic_key
                    and semantic_key == existing.semantic_key
                )
                or (
                    existing.kind == kind
                    and self._equivalent(existing.name, name)
                )
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
                        "semantic_key": semantic_key,
                        "kind": kind,
                        "notes": notes,
                        "required": source != "utopia_enrichment",
                    }
                )
            )
            if len(elements) >= max_before_portal:
                break

        # Scene IDs are normalized above; typed relation targets must follow
        # the same mapping or the deterministic compiler cannot resolve them.
        remapped_elements: list[WorldSceneElement] = []
        valid_ids = {item.scene_id for item in elements}
        for element in elements:
            relations = []
            for relation in element.relations:
                target_ids = [
                    old_to_new.get(target_id, target_id)
                    for target_id in relation.target_scene_ids
                ]
                target_ids = [
                    target_id
                    for target_id in target_ids
                    if target_id in valid_ids and target_id != element.scene_id
                ][:2]
                if not target_ids:
                    continue
                relations.append(
                    relation.model_copy(
                        update={"target_scene_ids": target_ids}
                    )
                )
            remapped_elements.append(
                element.model_copy(update={"relations": relations})
            )
        elements = remapped_elements

        if not any(item.kind == "portal" for item in elements):
            elements.append(
                WorldSceneElement(
                    scene_id=f"SCENE_{len(elements)+1:02d}",
                    name=fallback_portal or _DEFAULT_PORTAL,
                    semantic_key="main_portal",
                    kind="portal",
                    source="system_required",
                    required=True,
                    spatial_mode="grounded",
                    elevation="ground",
                    orientation="normal",
                    geometry_role="arch",
                    traversability="walkable",
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
                "schema_version": SCENE_PLAN_SCHEMA_VERSION,
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
        for keywords, canonical, kind, semantic_key in _OBVIOUS_OBJECTS:
            if not any(
                self._has_affirmed_keyword(text, keyword)
                for keyword in keywords
            ):
                continue
            if kind == "portal" and any(item.kind == "portal" for item in elements):
                continue
            if any(
                item.semantic_key == semantic_key
                or self._equivalent(item.name, canonical)
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
                    semantic_key=semantic_key,
                    kind=kind,
                    source="creator_required",
                    required=True,
                    spatial_mode="grounded",
                    elevation="ground",
                    orientation="normal",
                    geometry_role=self._default_geometry_role(kind),
                    traversability=self._default_traversability(kind),
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

    @classmethod
    def _semantic_key(cls, name: str, kind: str) -> str:
        lowered = name.lower()
        for keywords, _canonical, candidate_kind, key in _OBVIOUS_OBJECTS:
            if candidate_kind == kind and any(keyword in lowered for keyword in keywords):
                return key
        normalized = cls._norm(name)
        tokens = [
            token
            for token in normalized.split()
            if token not in {"the", "a", "an", "of", "and", "with"}
        ]
        if not tokens:
            return kind
        return "_".join(tokens[:5])

    @staticmethod
    def _default_geometry_role(kind: str) -> str:
        return {
            "water": "surface",
            "bridge": "bridge",
            "terrain": "terrain_mass",
            "portal": "arch",
            "decoration": "decorative",
            "structure": "volume",
            "landmark": "volume",
        }.get(kind, "volume")

    @staticmethod
    def _default_traversability(kind: str) -> str:
        return {
            "water": "blocked",
            "bridge": "walkable",
            "terrain": "walkable",
            "portal": "walkable",
            "decoration": "decorative",
            "structure": "scenic",
            "landmark": "scenic",
        }.get(kind, "scenic")

    @staticmethod
    def _has_affirmed_keyword(text: str, keyword: str) -> bool:
        """Return true when at least one occurrence is not explicitly negated."""
        start = 0
        while True:
            index = text.find(keyword, start)
            if index < 0:
                return False
            before = text[max(0, index - 18):index]
            before_compact = re.sub(r"\s+", " ", before)
            negated = any(
                marker in before_compact
                for marker in (
                    "not a ",
                    "not an ",
                    "not ",
                    "no ",
                    "without a ",
                    "without ",
                    "instead of a ",
                    "instead of ",
                    "不是",
                    "并不是",
                    "不要",
                    "没有",
                    "并没有",
                    "无需",
                    "无",
                )
            )
            if not negated:
                return True
            start = index + len(keyword)

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

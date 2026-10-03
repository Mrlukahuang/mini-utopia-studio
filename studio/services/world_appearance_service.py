from __future__ import annotations

import json

from studio.models.render import (
    AttachmentSocketSpec,
    ObjectAppearanceSpec,
    PreviewBBox,
    RenderVec3,
    ShapePartSpec,
    WorldAppearancePlan,
)
from studio.models.world import WorldBlueprint, WorldLayoutElement, WorldProfile
from studio.providers.base import ImageAnalysisProvider, StructuredTextProvider


class WorldAppearancePlanningError(RuntimeError):
    pass


class WorldAppearanceService:
    """Plan object appearance without changing authoritative Blueprint logic."""

    def __init__(
        self,
        *,
        structured_provider: StructuredTextProvider | None = None,
        image_analysis_provider: ImageAnalysisProvider | None = None,
    ):
        self.structured_provider = structured_provider
        self.image_analysis_provider = image_analysis_provider

    def plan_from_blueprint(
        self,
        *,
        profile: WorldProfile,
        blueprint: WorldBlueprint,
        style_profile: dict,
        strict_provider: bool = False,
        repair_weak_heroes: bool = False,
    ) -> WorldAppearancePlan:
        fallback = self._fallback_plan(profile=profile, blueprint=blueprint)
        if self.structured_provider is None:
            return fallback

        try:
            proposed = self.structured_provider.generate_structured(
                system=self._system_prompt(style_profile),
                user=self._blueprint_prompt(
                    profile=profile,
                    blueprint=blueprint,
                    base_plan=None,
                    preview_mode=False,
                ),
                schema=WorldAppearancePlan,
            )
        except Exception as exc:
            if strict_provider:
                raise WorldAppearancePlanningError(
                    f"GPT AppearancePlan generation failed: {exc}"
                ) from exc
            return fallback

        normalized = self._normalize(
            proposed=proposed,
            blueprint=blueprint,
            fallback=fallback,
        )
        if repair_weak_heroes:
            normalized = self._repair_weak_heroes_from_text(
                profile=profile,
                blueprint=blueprint,
                style_profile=style_profile,
                plan=normalized,
                strict_provider=strict_provider,
            )
        return normalized

    def refine_from_preview(
        self,
        *,
        profile: WorldProfile,
        blueprint: WorldBlueprint,
        style_profile: dict,
        base_plan: WorldAppearancePlan,
        image_bytes: bytes,
        mime_type: str = "image/png",
        strict_provider: bool = False,
        repair_weak_heroes: bool = False,
    ) -> WorldAppearancePlan:
        if self.image_analysis_provider is None or not image_bytes:
            return base_plan

        prompt = (
            self._system_prompt(style_profile)
            + "\n\n"
            + "PREVIEW RECONSTRUCTION PASS\n"
            + "You are looking at the beauty Preview rendered from the same authoritative "
              "Blueprint. Refine APPEARANCE ONLY so the future 3D geometry resembles the "
              "Preview. Never move, resize, delete, reorder, or reconnect Blueprint objects. "
              "Return exactly one object spec for each Blueprint element_id. Use preview_bbox "
              "to mark the object's approximate visible region when it can be identified. "
              "If an object is occluded or unclear, keep the base-plan shape rather than inventing "
              "a conflicting identity.\n\n"
            + self._blueprint_prompt(
                profile=profile,
                blueprint=blueprint,
                base_plan=base_plan,
                preview_mode=True,
            )
        )
        try:
            proposed = self.image_analysis_provider.analyze_structured(
                image_bytes=image_bytes,
                mime_type=mime_type,
                prompt=prompt,
                schema=WorldAppearancePlan,
            )
        except Exception as exc:
            if strict_provider:
                raise WorldAppearancePlanningError(
                    f"Preview Vision appearance refinement failed: {exc}"
                ) from exc
            return base_plan

        normalized = self._normalize(
            proposed=proposed,
            blueprint=blueprint,
            fallback=base_plan,
        )
        if repair_weak_heroes:
            normalized = self._repair_weak_heroes_from_vision(
                profile=profile,
                blueprint=blueprint,
                style_profile=style_profile,
                plan=normalized,
                image_bytes=image_bytes,
                mime_type=mime_type,
                strict_provider=strict_provider,
            )
        return normalized

    def _system_prompt(self, style_profile: dict) -> str:
        palette = style_profile.get("macaron_palette", {}) or {}
        return f"""
You are the Mini Utopia Object Appearance Architect.

BLUEPRINT AUTHORITY
- Blueprint owns WHAT exists, world-space x/y/z, width/depth/height, support
  relations, walkability, paths, Portal location and game logic.
- You may NEVER alter those facts.
- Your job is only to describe HOW each Blueprint object should look.

THREE.JS / GEOMETRY OUTPUT INTENT
- Produce compact shape grammar, not JavaScript and not vertex arrays.
- main_body + parts must be sufficient for a Geometry Compiler to create a
  recognizable silhouette using primitive/procedural/voxel geometry.
- Use local normalized positions and relative scales. Blueprint dimensions will
  supply final world scale.
- Keep part count economical. Prefer strong silhouette over micro-detail.
- Use sockets for surfaces/attachment points that other Blueprint objects need.

MINI UTOPIA STYLE CONSTITUTION — HARD CONSTRAINT
Visual DNA: {", ".join(style_profile.get("visual_dna_pillars", []))}
Shape language: {style_profile.get("shape_language", "")}
World geometry: {style_profile.get("world_geometry_language", "")}
Materials: {style_profile.get("runtime_material_rule", style_profile.get("material_language", ""))}
Color harmony: {style_profile.get("color_harmony_rule", style_profile.get("palette_notes", ""))}
Allowed macaron families: {", ".join(palette.get("enabled_families", []))}
Avoid: {", ".join(palette.get("avoid", []))}

STYLE SAFETY
- Never drift into photorealism, unrelated game aesthetics, branded blocks,
  realistic fur/skin, or incompatible material systems.
- Palette assignments are semantic roles only: primary, secondary, accent,
  cream, sky, water, foliage, glow, dark_accent.
- Material roles are controlled: toy_matte, toy_soft, translucent, emissive,
  water, foliage, glass_soft.
- Prefer rounded_block / soft_round / chunky_bevel.
- A living creature or biological carrier should normally use
  silhouette_family=organic_creature and procedural/hybrid shape grammar.
""".strip()

    def _blueprint_prompt(
        self,
        *,
        profile: WorldProfile,
        blueprint: WorldBlueprint,
        base_plan: WorldAppearancePlan | None,
        preview_mode: bool,
    ) -> str:
        elements = [
            {
                "element_id": item.element_id,
                "name": item.name,
                "kind": item.kind,
                "semantic_key": item.semantic_key,
                "spatial_mode": item.spatial_mode,
                "orientation": item.orientation,
                "geometry_role": item.geometry_role,
                "traversability": item.traversability,
                "position": item.position.model_dump(mode="json"),
                "size": {
                    "width": item.width,
                    "depth": item.depth,
                    "height": item.height,
                },
                "source_evidence": list(item.source_evidence),
            }
            for item in blueprint.layout_elements
        ]
        base = (
            base_plan.model_dump(mode="json")
            if base_plan is not None
            else None
        )
        return (
            "CREATOR ORIGINAL DESCRIPTION\n"
            + (profile.source_description or profile.world_name or "Untitled world")
            + "\n\nAUTHORITATIVE BLUEPRINT OBJECTS\n"
            + json.dumps(elements, ensure_ascii=False, indent=2)
            + (
                "\n\nBASE APPEARANCE PLAN TO REFINE\n"
                + json.dumps(base, ensure_ascii=False, indent=2)
                if base is not None
                else ""
            )
            + "\n\nOUTPUT RULES\n"
            + "- Return the same element_id values exactly.\n"
            + "- One ObjectAppearanceSpec per Blueprint object.\n"
            + "- Do not create world-space positions or dimensions.\n"
            + "- Build recognizable silhouettes with main_body + attached parts.\n"
            + "- Keep all objects inside one Mini Utopia visual language.\n"
            + (
                "- Use visible Preview evidence to refine silhouette and local parts.\n"
                if preview_mode
                else "- Infer appearance from creator wording and Blueprint semantics.\n"
            )
        )

    def _normalize(
        self,
        *,
        proposed: WorldAppearancePlan,
        blueprint: WorldBlueprint,
        fallback: WorldAppearancePlan,
    ) -> WorldAppearancePlan:
        proposed_by_id = {item.element_id: item for item in proposed.objects}
        fallback_by_id = {item.element_id: item for item in fallback.objects}
        objects: list[ObjectAppearanceSpec] = []

        for element in blueprint.layout_elements:
            item = proposed_by_id.get(element.element_id)
            if item is None:
                item = fallback_by_id[element.element_id]
            objects.append(
                item.model_copy(
                    update={
                        "element_id": element.element_id,
                        "name": element.name,
                    }
                )
            )

        return WorldAppearancePlan(
            world_style_summary=(
                proposed.world_style_summary.strip()
                or fallback.world_style_summary
            ),
            objects=objects,
        )

    def summarize_plan(
        self,
        *,
        blueprint: WorldBlueprint,
        plan: WorldAppearancePlan,
    ) -> dict:
        by_id = {item.element_id: item for item in plan.objects}
        objects = []
        for element in blueprint.layout_elements:
            item = by_id.get(element.element_id)
            if item is None:
                continue
            objects.append(
                {
                    "element_id": element.element_id,
                    "name": element.name,
                    "kind": element.kind,
                    "geometry_role": element.geometry_role,
                    "silhouette_family": item.silhouette_family,
                    "geometry_strategy": item.geometry_strategy,
                    "main_primitive": item.main_body.primitive,
                    "part_count": len(item.parts),
                    "part_roles": [part.role for part in item.parts],
                    "weak_hero": self._is_weak_hero(element=element, item=item),
                }
            )
        return {
            "object_count": len(objects),
            "weak_hero_count": sum(1 for item in objects if item["weak_hero"]),
            "objects": objects,
        }

    @staticmethod
    def _is_weak_hero(
        *,
        element: WorldLayoutElement,
        item: ObjectAppearanceSpec,
    ) -> bool:
        organic = (
            element.geometry_role == "organic"
            or item.silhouette_family == "organic_creature"
        )
        hero_scale = max(element.width, element.depth, element.height) >= 6.0
        hero_kind = element.kind in {"landmark", "structure"}
        return bool(organic and hero_scale and hero_kind and len(item.parts) < 2)

    def _repair_weak_heroes_from_text(
        self,
        *,
        profile: WorldProfile,
        blueprint: WorldBlueprint,
        style_profile: dict,
        plan: WorldAppearancePlan,
        strict_provider: bool,
    ) -> WorldAppearancePlan:
        if self.structured_provider is None:
            return plan

        by_id = {item.element_id: item for item in plan.objects}
        changed = False
        for element in blueprint.layout_elements:
            current = by_id.get(element.element_id)
            if current is None or not self._is_weak_hero(
                element=element,
                item=current,
            ):
                continue
            try:
                repaired = self.structured_provider.generate_structured(
                    system=self._system_prompt(style_profile),
                    user=self._focused_hero_prompt(
                        profile=profile,
                        element=element,
                        current=current,
                        preview_mode=False,
                    ),
                    schema=ObjectAppearanceSpec,
                )
            except Exception as exc:
                if strict_provider:
                    raise WorldAppearancePlanningError(
                        f"Focused Hero appearance repair failed for "
                        f"{element.element_id} ({element.name}): {exc}"
                    ) from exc
                continue
            repaired = repaired.model_copy(
                update={
                    "element_id": element.element_id,
                    "name": element.name,
                }
            )
            if self._is_weak_hero(element=element, item=repaired):
                if strict_provider:
                    raise WorldAppearancePlanningError(
                        f"Focused Hero appearance repair remained too weak for "
                        f"{element.element_id} ({element.name}): "
                        f"expected at least 2 silhouette parts, got "
                        f"{len(repaired.parts)}."
                    )
                continue
            by_id[element.element_id] = repaired
            changed = True

        if not changed:
            return plan
        return plan.model_copy(
            update={
                "objects": [
                    by_id.get(element.element_id)
                    for element in blueprint.layout_elements
                    if by_id.get(element.element_id) is not None
                ]
            }
        )

    def _repair_weak_heroes_from_vision(
        self,
        *,
        profile: WorldProfile,
        blueprint: WorldBlueprint,
        style_profile: dict,
        plan: WorldAppearancePlan,
        image_bytes: bytes,
        mime_type: str,
        strict_provider: bool,
    ) -> WorldAppearancePlan:
        if self.image_analysis_provider is None:
            return plan

        by_id = {item.element_id: item for item in plan.objects}
        changed = False
        for element in blueprint.layout_elements:
            current = by_id.get(element.element_id)
            if current is None or not self._is_weak_hero(
                element=element,
                item=current,
            ):
                continue
            prompt = (
                self._system_prompt(style_profile)
                + "\n\nFOCUSED HERO RECONSTRUCTION\n"
                + self._focused_hero_prompt(
                    profile=profile,
                    element=element,
                    current=current,
                    preview_mode=True,
                )
                + "\nUse the provided Preview image as visual evidence. "
                  "Return only this one ObjectAppearanceSpec."
            )
            try:
                repaired = self.image_analysis_provider.analyze_structured(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    prompt=prompt,
                    schema=ObjectAppearanceSpec,
                )
            except Exception as exc:
                if strict_provider:
                    raise WorldAppearancePlanningError(
                        f"Focused Hero Vision repair failed for "
                        f"{element.element_id} ({element.name}): {exc}"
                    ) from exc
                continue
            repaired = repaired.model_copy(
                update={
                    "element_id": element.element_id,
                    "name": element.name,
                }
            )
            if self._is_weak_hero(element=element, item=repaired):
                if strict_provider:
                    raise WorldAppearancePlanningError(
                        f"Focused Hero Vision repair remained too weak for "
                        f"{element.element_id} ({element.name}): "
                        f"expected at least 2 silhouette parts, got "
                        f"{len(repaired.parts)}."
                    )
                continue
            by_id[element.element_id] = repaired
            changed = True

        if not changed:
            return plan
        return plan.model_copy(
            update={
                "objects": [
                    by_id.get(element.element_id)
                    for element in blueprint.layout_elements
                    if by_id.get(element.element_id) is not None
                ]
            }
        )

    def _focused_hero_prompt(
        self,
        *,
        profile: WorldProfile,
        element: WorldLayoutElement,
        current: ObjectAppearanceSpec,
        preview_mode: bool,
    ) -> str:
        evidence = list(element.source_evidence)
        return (
            "FOCUSED OBJECT\n"
            f"element_id: {element.element_id}\n"
            f"name: {element.name}\n"
            f"kind: {element.kind}\n"
            f"semantic_key: {element.semantic_key}\n"
            f"geometry_role: {element.geometry_role}\n"
            f"spatial_mode: {element.spatial_mode}\n"
            f"size: width={element.width}, depth={element.depth}, "
            f"height={element.height}\n"
            f"creator_description: {profile.source_description}\n"
            f"source_evidence: {json.dumps(evidence, ensure_ascii=False)}\n"
            "CURRENT WEAK SPEC\n"
            + json.dumps(current.model_dump(mode="json"), ensure_ascii=False, indent=2)
            + "\n\nQUALITY REQUIREMENT\n"
            + "This is a major organic Hero object. A body-only primitive is not "
              "recognizable enough. Keep one clear main body and add 2-8 "
              "silhouette-defining local parts appropriate to the creator's named "
              "subject: e.g. head/muzzle, rear appendage/tail, paired side "
              "appendages, wings/fins/limbs/tentacles when appropriate. Do not "
              "invent traits that contradict the creator. Strong readable silhouette "
              "matters more than micro-detail. Keep Mini Utopia toy/soft-voxel style.\n"
            + (
                "Use the Preview as the primary appearance evidence while preserving "
                "the Blueprint identity."
                if preview_mode
                else "Use creator wording and Blueprint semantics as appearance evidence."
            )
        )

    def _fallback_plan(
        self,
        *,
        profile: WorldProfile,
        blueprint: WorldBlueprint,
    ) -> WorldAppearancePlan:
        return WorldAppearancePlan(
            world_style_summary=(
                "Mini Utopia soft voxel / rounded toy world with one coherent "
                "macaron material and palette language."
            ),
            objects=[
                self._fallback_object(element)
                for element in blueprint.layout_elements
            ],
        )

    def _fallback_object(
        self,
        element: WorldLayoutElement,
    ) -> ObjectAppearanceSpec:
        primitive = "rounded_box"
        family = "abstract"
        palette_role = "primary"
        material_role = "toy_matte"
        symmetry = "none"

        if element.geometry_role == "organic":
            primitive = "ellipsoid"
            family = "organic_creature"
            material_role = "toy_soft"
            symmetry = "bilateral"
        elif element.geometry_role == "terrain_mass":
            primitive = "rounded_box"
            family = "terrain"
            palette_role = "foliage"
        elif element.geometry_role == "bridge":
            primitive = "box"
            family = "bridge"
            palette_role = "cream"
            symmetry = "bilateral"
        elif element.geometry_role == "arch" or element.kind == "portal":
            primitive = "arch"
            family = "portal"
            palette_role = "glow"
            material_role = "emissive"
            symmetry = "bilateral"
        elif element.geometry_role == "vertical_flow":
            primitive = "box"
            family = "water"
            palette_role = "water"
            material_role = "water"
        elif element.kind == "water":
            primitive = "cylinder"
            family = "water"
            palette_role = "water"
            material_role = "water"
        elif element.kind == "structure":
            primitive = "rounded_box"
            family = "architecture"
            palette_role = "cream"
        elif element.kind == "decoration":
            primitive = "sphere"
            family = "prop"
            palette_role = "accent"

        sockets: list[AttachmentSocketSpec] = []
        if element.traversability in {"walkable", "rideable"}:
            sockets.append(
                AttachmentSocketSpec(
                    socket_id="top_walkable",
                    role="walkable_surface",
                    local_position=RenderVec3(x=0, y=.5, z=0),
                )
            )
        return ObjectAppearanceSpec(
            element_id=element.element_id,
            name=element.name,
            geometry_strategy="procedural",
            silhouette_family=family,
            silhouette_notes=(
                f"Fallback silhouette for {element.geometry_role}; "
                "replace/refine with GPT or Preview evidence when available."
            ),
            main_body=ShapePartSpec(
                part_id="body",
                role="main_body",
                primitive=primitive,
                palette_role=palette_role,
                material_role=material_role,
            ),
            parts=[],
            sockets=sockets,
            detail_density="medium",
            edge_profile="rounded_block",
            symmetry=symmetry,
            preview_bbox=PreviewBBox(),
            preview_evidence="",
            creator_evidence=element.name,
        )

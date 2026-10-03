from __future__ import annotations

from studio.models.world import (
    WorldProfile,
    WorldVisualAnalysis,
    WorldVisualAnchor,
)
from studio.providers.base import ImageAnalysisProvider


VISION_PROMPT = """You are analyzing an approved Mini Utopia World Concept image.

Extract only visible evidence from the image. Do not invent hidden rooms, unseen
structures, story facts, or geometry that is not visually supported.

Return:
- a short concept summary,
- Must Preserve: the few features that define this exact world at a glance,
- Flexible Details: visible secondary details that may vary in the playable build,
- dominant palette colors as HEX approximations,
- composition notes such as foreground/midground/background organization,
- spatial relations between major visible elements.

Favor concrete visual nouns and relations over vague mood words. The result will
guide a later playable 3D Blueprint, so prioritize silhouette, landmark placement,
paths, water, bridges, portals, terrain layers, and major structures.
"""


class WorldVisualAnchorService:
    """Derive a provider-neutral visual anchor from an approved World concept.

    Multimodal image evidence is preferred when an ImageAnalysisProvider and
    image bytes are available. Deterministic profile extraction remains the
    safe fallback so world approval never depends on a single AI provider.
    """

    def __init__(self, image_analysis_provider: ImageAnalysisProvider | None = None):
        self.image_analysis_provider = image_analysis_provider

    def extract(
        self,
        *,
        profile: WorldProfile,
        concept_direction: str,
        concept_path: str,
        image_bytes: bytes | None = None,
        mime_type: str = "image/png",
    ) -> WorldVisualAnchor:
        if self.image_analysis_provider is not None and image_bytes:
            try:
                analysis = self.image_analysis_provider.analyze_structured(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    prompt=VISION_PROMPT,
                    schema=WorldVisualAnalysis,
                )
                return WorldVisualAnchor(
                    concept_image_roles=["world_concept_approved"],
                    concept_path=concept_path,
                    concept_direction=concept_direction,
                    extraction_method="openai_vision_v1",
                    concept_summary=analysis.concept_summary,
                    must_preserve=list(analysis.must_preserve),
                    flexible_details=list(analysis.flexible_details),
                    palette_hexes=list(analysis.palette_hexes),
                    composition_notes=list(analysis.composition_notes),
                    spatial_relations=list(analysis.spatial_relations),
                )
            except Exception:
                # Approval and Blueprint creation must remain available even when
                # the optional vision provider is unavailable or rejects an image.
                pass

        return self._extract_deterministic(
            profile=profile,
            concept_direction=concept_direction,
            concept_path=concept_path,
        )

    def _extract_deterministic(
        self,
        *,
        profile: WorldProfile,
        concept_direction: str,
        concept_path: str,
    ) -> WorldVisualAnchor:
        must_preserve: list[str] = []

        def add(value: str) -> None:
            value = (value or "").strip()
            if value and value not in must_preserve:
                must_preserve.append(value)

        add(profile.world_type)
        add(profile.portal_form)
        for item in profile.landmark_ideas:
            add(item)
        for item in profile.water_features:
            add(item)
        for item in profile.landscape_elements[:3]:
            add(item)

        flexible: list[str] = []
        for item in [*profile.surprise_elements, *profile.mood]:
            item = (item or "").strip()
            if item and item not in flexible and item not in must_preserve:
                flexible.append(item)

        summary_parts = [
            profile.world_name,
            concept_direction or "approved concept",
            profile.source_description,
            profile.creator_extra_details,
        ]
        summary = " · ".join(part.strip() for part in summary_parts if part and part.strip())

        return WorldVisualAnchor(
            concept_image_roles=["world_concept_approved"],
            concept_path=concept_path,
            concept_direction=concept_direction,
            extraction_method="deterministic_profile_v1",
            concept_summary=summary,
            must_preserve=must_preserve,
            flexible_details=flexible,
            palette_hexes=list(profile.theme_color_hexes),
            composition_notes=[],
            spatial_relations=[],
        )

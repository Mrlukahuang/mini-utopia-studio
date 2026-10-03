from __future__ import annotations

from studio.models.world import WorldProfile, WorldVisualAnchor


class WorldVisualAnchorService:
    """Derive a provider-neutral visual anchor from an approved World concept.

    v0.1 is deterministic and uses the creator-confirmed WorldProfile plus the
    selected concept direction. A future multimodal provider can replace this
    implementation without changing WorldBlueprint or the runtime contract.
    """

    def extract(
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
        )

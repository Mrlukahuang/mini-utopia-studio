from __future__ import annotations

from studio.models.world import WorldProfile


DIRECTION_NOTES = {
    "playable": (
        "Prioritize a readable playable layout: clear paths, navigable spaces, strong landmarks, "
        "good separation between foreground/midground/background, and obvious routes for a small avatar."
    ),
    "dream": (
        "Push imaginative visual invention: surprising but coherent architecture, magical environmental "
        "details, unusual scale relationships, and emotionally memorable scenery."
    ),
    "story": (
        "Prioritize story potential: visual clues, mysterious destinations, a meaningful Portal location, "
        "and at least one place that makes the viewer wonder what happened there."
    ),
}


class WorldConceptPromptService:
    """Compose World concept prompts from structured profile + global Style Canon."""

    def compose(
        self,
        *,
        profile: WorldProfile,
        style_profile: dict,
        direction: str,
    ) -> str:
        direction_note = DIRECTION_NOTES.get(direction, DIRECTION_NOTES["playable"])

        style_rules = "\n".join(
            f"- {rule}"
            for rule in style_profile.get("locked_rules", [])
        )
        negative_rules = "\n".join(
            f"- {rule}"
            for rule in style_profile.get("negative_rules", [])
        )
        palette = ", ".join(profile.theme_color_hexes) or "Mini Utopia global macaron palette"

        return f"""
MINI UTOPIA WORLD CONCEPT ART

WORLD
Name: {profile.world_name or "Untitled Mini World"}
Type: {profile.world_type}
Reality mode: {profile.reality_mode}
Terrain: {", ".join(profile.terrain)}
Season: {profile.season}
Weather: {profile.weather}
Time: {profile.time_of_day}
Mood: {", ".join(profile.mood)}
Landmark ideas: {", ".join(profile.landmark_ideas)}
Portal form: {profile.portal_form}
Portal placement idea: {profile.portal_placement_idea}
Architecture: {profile.architecture}
Water features: {", ".join(profile.water_features)}
Landscape elements: {", ".join(profile.landscape_elements)}
Surprise elements: {", ".join(profile.surprise_elements)}
Theme HEX colors: {palette}
Creator description: {profile.source_description}
Extra details: {profile.creator_extra_details}

GLOBAL MINI UTOPIA STYLE CANON
Visual DNA: {", ".join(style_profile.get("visual_dna_pillars", []))}
Shape language: {style_profile.get("shape_language", "")}
World geometry: {style_profile.get("world_geometry_language", "")}
Environment scale: {style_profile.get("environment_scale_language", "")}
Materials: {style_profile.get("runtime_material_rule", style_profile.get("material_language", ""))}
Color harmony: {style_profile.get("color_harmony_rule", style_profile.get("palette_notes", ""))}
Lighting: {style_profile.get("lighting", "")}
Camera language: {style_profile.get("camera_language", "")}
Portal language: {style_profile.get("portal_language", "")}

LOCKED RULES
{style_rules}

CONCEPT DIRECTION
{direction_note}

STRICT OUTPUT RULES
- Create one polished wide environment concept image.
- No text, captions, labels, logos, UI, measurements, map legends, watermarks, or typography.
- Do not generate a character portrait or character sheet.
- No visible characters unless the creator description explicitly asks for inhabitants.
- The environment must feel naturally scaled for Mini Playable Avatars.
- Preserve clear block-built / rounded-cuboid geometry and collectible-toy tactility.
- Keep the world original; do not imitate branded game worlds or proprietary toy systems.
- This image is a visual anchor for a future 50x50 expandable playable world, not a final matte painting.

NEGATIVE RULES
{negative_rules}
""".strip()

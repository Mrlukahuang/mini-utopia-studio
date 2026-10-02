from __future__ import annotations

from studio.models.character import CharacterProfile


class CharacterMasterPromptService:
    """Compose a provider-neutral Character Master generation brief.

    This is intentionally deterministic and provider-agnostic. Image providers
    consume the result later without owning Mini Utopia's Canon rules.
    """

    def compose(
        self,
        *,
        name: str,
        profile: CharacterProfile,
        style_profile: dict,
        wearable_descriptions: dict[str, str] | None = None,
    ) -> str:
        eyes = profile.eyes
        wearable_descriptions = wearable_descriptions or {}

        favorite_colors = ", ".join(profile.favorite_colors) or "use Mini Utopia macaron colors"
        personality = ", ".join(profile.personality_traits) or "warm, approachable"
        features = ", ".join(profile.distinctive_features) or "none specified"

        style_bits = [
            style_profile.get("medium", ""),
            style_profile.get("shape_language", ""),
            style_profile.get("character_scale_language", ""),
            style_profile.get("face_language", ""),
            style_profile.get("gameplay_silhouette", ""),
            style_profile.get("material_language", ""),
            style_profile.get("lighting", ""),
            style_profile.get("camera_language", ""),
            style_profile.get("palette_notes", ""),
        ]
        locked = " ".join(style_profile.get("locked_rules", []))
        negative = " ".join(style_profile.get("negative_rules", []))

        return "\n".join(
            line
            for line in [
                "Create a Mini Utopia Character Master.",
                f"Character name: {name}.",
                f"Character Type: {profile.character_type}.",
                (
                    f"Type description: {profile.character_type_description}."
                    if profile.character_type_description
                    else ""
                ),
                f"Age: {profile.age}.",
                f"Story Role: {profile.story_role or 'unspecified'}.",
                (
                    f"Role detail: {profile.story_role_description}."
                    if profile.story_role_description
                    else ""
                ),
                f"Appearance: {profile.appearance}.",
                f"Body build: {profile.body_build or 'Mini Utopia default'}.",
                f"Exact character height reference: {profile.height_cm or 'unspecified'} cm.",
                f"Hair or fur description: {profile.hair_or_fur or 'none specified'}.",
                f"Hair style: {profile.hair_style or 'none specified'}.",
                (
                    f"Hair/fur color: {profile.hair_or_fur_color} "
                    f"({profile.hair_or_fur_color_hex})."
                ),
                (
                    f"Eyes: {eyes.size or 'large'}, {eyes.shape or 'friendly'} shape, "
                    f"{eyes.color or 'macaron-compatible'} ({eyes.color_hex})."
                ),
                f"Favorite colors: {favorite_colors}.",
                f"Personality: {personality}.",
                f"Distinctive features: {features}.",
                (
                    f"Creator extra details: {profile.creator_extra_details}."
                    if profile.creator_extra_details
                    else ""
                ),
                (
                    "Outfit: "
                    f"top={wearable_descriptions.get('top', 'simple clean white T-shirt')}; "
                    f"bottom={wearable_descriptions.get('bottom', 'classic blue jeans')}; "
                    f"shoes={wearable_descriptions.get('shoes', 'simple white sneakers')}; "
                    f"hat={wearable_descriptions.get('hat', 'none')}."
                ),
                (
                    "COLOR SOURCE OF TRUTH: use the hexadecimal swatches exactly where supplied. "
                    f"Hair/fur swatch={profile.hair_or_fur_color_hex}; "
                    f"eye swatch={eyes.color_hex}; "
                    f"favorite palette={', '.join(profile.favorite_color_hexes) or 'Mini Utopia macaron palette'}."
                ),
                "STYLE PRIORITY: preserve the locked Mini Utopia block-built toy-game identity "
                "before adding decorative detail. Use chunky modular geometry, softly rounded "
                "edges, simplified sculpted hair/fur masses, matte collectible-toy surfaces, "
                "and a clear playable silhouette. It should sit between a voxel exploration "
                "world and a construction-toy diorama without copying any branded character, "
                "brick system, texture, stud pattern, UI, or signature asset.",
                "CHARACTER MASTER SHEET V1: one clean landscape visual reference sheet. "
                "Include one larger hero three-quarter view plus a consistent turnaround row "
                "(front, three-quarter, side, back) and five head-and-shoulder expressions "
                "(neutral, happy, curious, excited, surprised). Keep exactly the same character, "
                "hair/fur, colors, proportions and outfit in every view. Keep the layout stable: "
                "large hero area, compact turnaround strip, compact expression strip, generous "
                "negative space. Use a simple warm cream or very light Mini Utopia studio backdrop "
                "with subtle block-world cues only. Do not turn the sheet into a poster or scene.",
                "IMPORTANT OUTPUT RULE: visual artwork only. Do NOT draw or render any words, "
                "letters, labels, measurements, IDs, UI panels, logos, profile cards, captions, "
                "watermarks, arrows or typography anywhere in the image. The application renders "
                "all factual profile information separately from structured data.",
                "MINI UTOPIA VISUAL DNA:",
                " ".join(bit for bit in style_bits if bit),
                "LOCKED CANON RULES:",
                locked,
                "AVOID:",
                negative,
                "Keep the character original. Do not imitate branded characters, game textures, "
                "costumes, logos, interfaces, or signature shapes.",
            ]
            if line
        )

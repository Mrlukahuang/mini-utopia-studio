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
    ) -> str:
        eyes = profile.eyes
        wearables = profile.wearables

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
                    "Default outfit references: "
                    f"top={wearables.top_id or 'none'}, "
                    f"bottom={wearables.bottom_id or 'none'}, "
                    f"shoes={wearables.shoes_id or 'none'}, "
                    f"hat={wearables.hat_id or 'none'}."
                ),
                "MASTER PRESENTATION: full-body single character, centered clean presentation, "
                "clear silhouette, feet visible, neutral-to-cheerful three-quarter pose, "
                "designed as the canonical identity reference for future turnaround, expressions, "
                "animation and game-ready derivatives.",
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

from __future__ import annotations

from studio.core.enums import AssetType, ReviewStatus
from studio.models.asset import Asset
from studio.models.style import MacaronPaletteProfile, StyleProfile
from studio.models.universe import Universe
from studio.repositories.base import StudioRepository


MINI_UTOPIA_BASE_STYLE_NAME = "Mini Utopia Base Visual DNA"
MINI_UTOPIA_BASE_STYLE_SLUG = "mini-utopia-base-visual-dna"


class StyleService:
    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def ensure_mini_utopia_base(self) -> Asset:
        existing = None
        for asset in self.repository.list_assets(AssetType.STYLE):
            if asset.slug == MINI_UTOPIA_BASE_STYLE_SLUG:
                existing = asset
                break

        profile = StyleProfile(
            visual_dna_pillars=[
                "Miniature / 微缩世界",
                "Voxel / Block-inspired geometry / 方块化几何语言",
                "Toy-like / 玩具质感",
                "Macaron Dreamscape / 马卡龙梦幻世界",
                "Cinematic / 电影感",
            ],
            medium=(
                "Miniature diorama with original voxel-inspired and construction-toy-inspired "
                "geometry, translated into a proprietary Mini Utopia look rather than any branded style"
            ),
            shape_language=(
                "Chunky modular forms, soft square and rounded-cuboid masses, simplified planes, "
                "clean readable silhouettes, and gentle toy-like bevels. The identity should sit "
                "between a voxel exploration world and a construction-toy diorama while remaining "
                "original: no branded character anatomy, stud patterns, proprietary textures, "
                "logos, UI, or signature assets. Characters must read as small playable game "
                "avatars rather than realistic people."
            ),
            character_scale_language=(
                "Mini Playable Avatar proportions: approximately 2.8 to 3.0 heads tall for "
                "human-like characters; head occupies roughly one third of total height, with a deliberately compact lower body; "
                "compact torso, short limbs, slightly oversized hands and shoes, low center of "
                "gravity, and a bouncy run-ready silhouette. Non-human characters preserve the "
                "same large-head compact-body readability rather than realistic anatomy."
            ),
            face_language=(
                "Cute simplified game-avatar face: large readable eyes, small nose and mouth, "
                "soft cheeks, minimal facial micro-detail, no skin pores, no realistic adult "
                "facial anatomy, no fashion-doll realism. Expressions must remain legible at "
                "thumbnail size."
            ),
            gameplay_silhouette=(
                "Designed to look controllable in a cozy exploration game: compact body, clear "
                "silhouette, short stride, slightly oversized feet for grounded motion, and "
                "simple appendages that animate cleanly while running, jumping, waving, or "
                "carrying props."
            ),
            material_language=(
                "Matte collectible-toy surfaces, soft vinyl and painted-toy tactility, creamy "
                "finishes, restrained micro-detail, and clearly constructed geometric masses. "
                "Avoid realistic hair strands, plush-heavy fuzz, glossy fashion-doll plastic, "
                "or hyper-real material simulation unless the character concept explicitly needs it."
            ),
            lighting=(
                "Soft cinematic light, dreamy glow, gentle shadows, luminous highlights, "
                "and warm approachable atmosphere."
            ),
            camera_language=(
                "Cinematic miniature-world composition with clear foreground, midground, "
                "and background depth."
            ),
            palette_notes=(
                "Use the full macaron color family. Color variety is free, but saturation, "
                "lightness, contrast, gradients, and material response stay coherent."
            ),
            macaron_palette=MacaronPaletteProfile(
                enabled_families=[
                    "cream yellow",
                    "apricot orange",
                    "peach",
                    "strawberry pink",
                    "lavender",
                    "baby blue",
                    "sky blue",
                    "mint",
                    "pistachio",
                    "cream white",
                    "soft coral",
                    "soft aqua",
                    "light grape purple",
                ],
                avoid=[
                    "neon-heavy color",
                    "large pure-black masses",
                    "harsh contrast",
                    "dirty grey palettes",
                    "industrial coldness",
                ],
            ),
            locked_rules=[
                "Keep a miniature diorama feeling.",
                "Keep original voxel/block-inspired geometry.",
                "Keep chunky modular block-built forms with soft rounded edges.",
                "Keep the visual identity between voxel-world structure and construction-toy tactility, without branded imitation.",
                "Keep Mini Playable Avatar proportions: big head, compact body, short limbs.",
                "Keep cute simplified faces with large readable eyes and minimal realistic detail.",
                "Keep a run-ready game character silhouette readable at thumbnail size.",
                "Keep matte collectible-toy materials and simplified sculpted surfaces.",
                "Keep dreamy macaron color behavior.",
                "Keep soft cinematic lighting.",
                "Keep clear foreground / midground / background depth.",
                "Keep one consistent Portal visual language.",
                "Keep low aggression, high warmth and approachability.",
                "Keep the result refined rather than hyper-realistic.",
            ],
            flexible_expression=[
                "character species or type",
                "clothes and wearables",
                "props",
                "vehicles",
                "houses and architecture",
                "plants",
                "world themes",
                "wings, tails, and magic",
                "story objects",
                "weather",
                "roles and occupations",
            ],
            positive_rules=[
                "Translate any child-created idea into Mini Utopia visual language.",
                "Translate human characters into stylized playable mini-avatars, not realistic people.",
                "Preserve creative content even when the theme is dark, strange, or unexpected.",
                "Let world identity vary while inheriting the base visual DNA.",
            ],
            negative_rules=[
                "Do not reject an idea merely because its content is visually unusual.",
                "Do not copy branded game characters, textures, logos, UI, or signature assets.",
                "Avoid drifting into generic 3D animation, plush-toy rendering, anime illustration, "
                "or smooth cinematic character art without visible block-built geometric logic.",
                "Avoid realistic human proportions, realistic facial anatomy, visible skin pores, "
                "fashion-editorial posing, or long-legged doll-like silhouettes.",
                "Do not let a world-specific style replace the Mini Utopia base DNA in Canon Mode.",
            ],
            portal_language=(
                "Portals share a recognizable Mini Utopia construction: rounded toy-like "
                "architecture, luminous dreamy energy, and macaron-compatible glow."
            ),
        )

        if existing is not None:
            existing.display_name = MINI_UTOPIA_BASE_STYLE_NAME
            existing.description = (
                "The locked visual constitution inherited by Mini Utopia Canon characters, "
                "worlds, props, portals, and scenes."
            )
            existing.status = ReviewStatus.APPROVED
            existing.metadata["style_profile"] = profile.model_dump(mode="json")
            self.repository.save_asset(existing)
            return existing

        asset = Asset.create(
            AssetType.STYLE,
            display_name=MINI_UTOPIA_BASE_STYLE_NAME,
            slug=MINI_UTOPIA_BASE_STYLE_SLUG,
            description=(
                "The locked visual constitution inherited by Mini Utopia Canon characters, "
                "worlds, props, portals, and scenes."
            ),
            status=ReviewStatus.APPROVED,
            metadata={"style_profile": profile.model_dump(mode="json")},
        )
        self.repository.save_asset(asset)
        return asset

    def attach_base_style(self, universe: Universe) -> Universe:
        style = self.ensure_mini_utopia_base()
        if universe.style_asset_id != style.asset_id:
            universe.style_asset_id = style.asset_id
            self.repository.save_universe(universe)
        return universe

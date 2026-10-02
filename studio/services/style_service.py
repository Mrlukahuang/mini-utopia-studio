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
        for asset in self.repository.list_assets(AssetType.STYLE):
            if asset.slug == MINI_UTOPIA_BASE_STYLE_SLUG:
                return asset

        profile = StyleProfile(
            visual_dna_pillars=[
                "Miniature / 微缩世界",
                "Voxel / Block-inspired geometry / 方块化几何语言",
                "Toy-like / 玩具质感",
                "Macaron Dreamscape / 马卡龙梦幻世界",
                "Cinematic / 电影感",
            ],
            medium="Miniature diorama with original block-inspired geometry",
            shape_language=(
                "Rounded, friendly, modular toy-like forms with readable silhouettes; "
                "block-inspired without copying branded game assets, textures, or UI."
            ),
            material_language=(
                "Soft tactile toy materials, creamy surfaces, refined detail, "
                "and gentle stylization rather than hyper-realism."
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
                "Keep rounded, friendly, toy-like forms.",
                "Keep soft tactile materials.",
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
                "Preserve creative content even when the theme is dark, strange, or unexpected.",
                "Let world identity vary while inheriting the base visual DNA.",
            ],
            negative_rules=[
                "Do not reject an idea merely because its content is visually unusual.",
                "Do not copy branded game characters, textures, logos, UI, or signature assets.",
                "Do not let a world-specific style replace the Mini Utopia base DNA in Canon Mode.",
            ],
            portal_language=(
                "Portals share a recognizable Mini Utopia construction: rounded toy-like "
                "architecture, luminous dreamy energy, and macaron-compatible glow."
            ),
        )

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

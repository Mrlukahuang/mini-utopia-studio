# Mini Utopia Visual DNA v1

> The child decides what exists. The Studio decides how it belongs to Mini Utopia.

Mini Utopia separates **creative content freedom** from **visual language consistency**.

Children can invent characters, clothes, props, vehicles, architecture, plants, worlds, weather, magic, roles, and story objects freely. In Canon Mode, those ideas are translated through the same Mini Utopia visual language.

## Five pillars

1. **Miniature / 微缩世界**
2. **Voxel / Block-inspired / 方块化几何语言**
3. **Toy-like / 玩具质感**
4. **Macaron Dreamscape / 马卡龙梦幻世界**
5. **Cinematic / 电影感**

## Locked Visual DNA

The following are inherited by Canon characters, worlds, props, portals, and scenes:

- miniature diorama feeling
- original block-inspired geometry
- rounded, friendly, toy-like forms
- soft tactile materials
- dreamy macaron color behavior
- soft cinematic lighting
- clear foreground / midground / background depth
- one consistent Portal visual language
- low aggression, high warmth and approachability
- refined stylization rather than hyper-realism

Voxel / block-inspired does **not** mean copying Minecraft or another branded visual system. Mini Utopia must avoid branded characters, textures, logos, UI, or signature assets.

## Macaron Dreamscape

Mini Utopia does not use one tiny fixed palette. It enables the **full macaron color family** while locking the behavior of those colors.

Example families:

- cream yellow
- apricot orange
- peach
- strawberry pink
- lavender
- baby blue
- sky blue
- mint
- pistachio
- cream white
- soft coral
- soft aqua
- light grape purple

Color behavior:

- low-to-medium saturation
- high lightness
- soft gradients
- creamy / dreamy material response
- avoid neon-heavy color
- avoid large pure-black masses
- avoid harsh contrast
- avoid dirty grey palettes
- avoid industrial coldness

A volcano world may be dark in subject matter, but the Studio can translate it into deep grape-purple rock, soft coral lava, creamy smoke, toy-like forms, and macaron-compatible highlights rather than rejecting the idea.

## Flexible Expression

Children may freely invent:

- species / character type
- clothes and wearables
- props
- vehicles
- houses and architecture
- plants
- world themes
- wings, tails, and magic
- story objects
- weather
- roles and occupations

The freedom is in **what exists**. The lock is in **how it is visually expressed**.

## Style layering

```text
Mini Utopia Base Visual DNA
        ↓
World Style Pack
        ↓
Scene Mood
```

A practical design guide:

- **70%** Mini Utopia DNA
- **20%** World identity
- **10%** Scene surprise

This is a creative guideline, not a numeric rendering rule.

## Canon Mode vs Playground Mode

### Canon Mode

Canon content inherits the Mini Utopia Base Visual DNA. The user does not need to choose a global style every time.

### Playground Mode

Playground may remove the style lock and experiment with watercolor, realism, clay, comic, monochrome, cyberpunk, or other visual languages.

A successful Playground experiment can later be reviewed and promoted into a compatible Style Pack, but it never changes Canon automatically.

## Style inheritance

World Style Packs inherit from the base style instead of redefining the whole visual language.

For example, a Candy World may override:

- palette emphasis
- architecture
- flora
- atmosphere
- material flavor

while retaining the base Mini Utopia geometry, toy language, lighting philosophy, cinematic depth, and macaron behavior.

## Future prompt composition

```text
Character Profile
+ Mini Utopia Base Visual DNA
+ World Style Pack
+ Scene Mood
+ Shot Instructions
= Final Generation Prompt
```

The creator should not need to manually write or manage this prompt stack.

## Four locks

```text
🔒 Visual DNA Lock
🔒 Character Identity Lock
🔒 World Identity Lock
🎨 Scene Freedom
```

The first three preserve continuity. The last protects imagination.

## Reference set

Future approved reference images belong to the Style Bible and will be attached to the STYLE asset.

This lets the Mini Utopia identity survive provider and model changes instead of being tied to one image model.

## Architecture

The base style is a reusable `STYLE_<ID>` Asset.

- The Mini Utopia Universe points to its base STYLE Asset.
- World Style Packs may use `parent_style_asset_id`.
- Approved visual references may use `reference_asset_ids`.
- Style content is independent of stories and characters.

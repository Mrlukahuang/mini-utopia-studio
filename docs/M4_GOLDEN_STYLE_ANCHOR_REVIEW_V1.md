# Golden Style Anchor Review v1

The first real-asset lineup establishes an important distinction:

**Installed does not mean approved.**

The Golden workflow now has four practical layers:

1. **Style Anchors** — assets allowed to teach GPT what Mini Utopia geometry looks like.
2. **Direct Use** — assets compatible with production but not allowed to define the visual language.
3. **Gameplay Utility** — blockout/traversal/mechanics assets that remain useful but should not leak into style references.
4. **Conditional** — assets that need another compatibility/material/palette test before promotion.

The versioned verdict source is:

`assets/catalogs/golden_style_anchor_verdicts_v1.json`

## Current Style Anchors

- KayKit Forest round tree
- KayKit Medieval home
- KayKit Medieval tower
- KayKit Adventurer Knight

These four form the first **geometry reference spine**.

## Direct-use compatible assets

- Forest branching tree
- Forest bush
- Forest rock
- Medieval bridge
- Dungeon chest
- Skeleton Minion

## Gameplay utility only

- Platformer platform
- Platformer slope

These are useful for traversal and prototyping, but their very blocky geometry should not be shown to GPT as the main Canon style reference.

## Kenney Castle

The first compatibility sample is **conditional**, not rejected globally.

The current tower does not visually blend as cleanly as the KayKit anchors in the lineup. Before deciding the whole pack, test one more representative Kenney Castle asset after the palette/material remap stage.

## Next: semantic palette remap

The next production step is intentionally small:

1. inspect the shared KayKit atlases for the approved Style Anchor packs
2. map atlas swatches/cells to Mini Utopia semantic slots
3. generate derived Candidate-B atlases
4. render the same approved anchors again in Godot
5. only then decide whether Candidate B becomes Core Palette v1.0

Do not recolor every downloaded pack yet.

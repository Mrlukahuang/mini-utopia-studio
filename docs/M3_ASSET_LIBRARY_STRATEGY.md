# Mini Utopia Full-3D Asset Library Strategy v1

## Product decision

Mini Utopia continues toward a **Full 3D playable World**, but it will not
generate every object from scratch.

The goal is still the original one:

> A child imagines a world, enters it, plays in it, returns to the same place
> later, and can tell many different stories in that same persistent world.

The world must therefore be a long-lived canonical asset, not a disposable
single render.

## Core rule

Use the cheapest reliable source that preserves quality:

```text
Blueprint semantic need
        ↓
1. Reuse approved Mini Utopia Asset Library GLB
        ↓ if unavailable
2. Procedural/simple geometry for regular structural pieces
        ↓ if the object is visually distinctive and cannot be reused
3. Image-to-3D generation for creator-specific Hero assets
        ↓
Mini Utopia normalization / approval
        ↓
WorldRenderSpec
        ↓
Three.js
```

Pixal3D or future generators are therefore **Hero asset makers**, not the
default source for every tree, rock, stair, bridge plank, or patch of grass.

## Why this matters

A canonical World may be used for:

- free play today
- another story two days later
- a different episode next month
- recurring camera shots for generated video
- multiple characters visiting the same place

Reusing the same stable asset IDs protects continuity. A bridge, whale, tree,
Portal, or house should not randomly change appearance because a new story is
being generated.

## Sources

### Preferred: CC0/open game-ready libraries

Initial audit targets:

1. **Quaternius**
   - especially Stylized Nature MegaKit and compatible stylized packs
   - glTF available
   - CC0
   - strong candidate for trees, plants, flowers, rocks and environment props

2. **KayKit**
   - especially Forest Nature Pack
   - GLTF available
   - CC0
   - optimized low-poly assets and shared gradient-atlas workflow are useful
     references for Mini Utopia style consistency and web runtime efficiency

3. **Kenney**
   - Mini Forest and other compatible mini/stylized 3D packs
   - CC0
   - useful for simple environment/gameplay modules

Third-party assets are never accepted merely because they are free. They must
pass the Mini Utopia style/technical review.

### Generated assets

Use Pixal3D or another HeroAssetProvider for objects that are:

- creator-specific
- identity-bearing
- hard to find in a reusable library
- important enough to justify GPU quota

Examples:

- Sky Whale
- Candy Dragon
- Star Turtle
- Walking House
- creator-invented magical machine

## Library asset contract

Every reusable GLB records:

- permanent Mini Utopia Asset ID
- category and semantic keys
- content SHA-256
- ObjectStorage path
- byte size
- source name and source URL
- license identifier and attribution requirement
- generator model when applicable
- transform normalization expectations
- style review status: raw → normalized → approved
- allowed non-destructive variants
- parent asset ID for derived variants

The GLB binary is immutable and content-addressed.

## Derived variants

A color/material/scale variant should normally **not** consume another GPU
generation.

Example:

```text
MU Round Tree Base GLB
├── Spring Green variant
├── Strawberry Pink variant
├── Lavender Night variant
└── Snowy Cream variant
```

These variants may share the same GLB bytes while recording different runtime
palette/material/scale overrides.

Geometry-changing edits are a separate operation and may require Blender,
mesh processing, or regeneration.

## Mini Utopia normalization gate

Before an imported/generated GLB becomes approved:

1. verify GLB 2.0
2. preserve source/license metadata
3. normalize orientation
4. normalize ground pivot / x-z centering
5. normalize scale convention
6. inspect polygon/file-size budget
7. inspect textures/materials
8. apply or map into Mini Utopia Visual DNA
9. produce review thumbnail
10. approve into the reusable Library

The current M3.4 foundation implements the metadata/storage/deduplication layer.
Binary mesh/material rewriting and visual normalization are the next layer.

## Asset sourcing priorities

### Reuse first

High-frequency objects should come from the Library when possible:

- trees
- plants / flowers
- grass patches
- rocks
- mushrooms
- clouds
- lamps
- benches
- fences
- doors / windows
- simple houses / towers
- bridge / stair / platform modules
- crystals / stars / lanterns
- Portal components

### Procedural first

Do not spend GPU quota on simple regular geometry:

- floor/path tiles
- simple platforms
- steps
- walls
- rails
- basic bridge deck pieces
- collision proxies
- invisible navigation meshes

### Generate first

Reserve image-to-3D quota for distinctive imagination:

- major creatures
- signature fantasy vehicles
- signature buildings
- unusual magical machines
- unique story-defining objects

## Character wearables are a separate pipeline

Shoes, clothes and hair are not ordinary props. A standalone GLB does not
automatically fit a character skeleton or animation rig.

Wearables need a later modular-character pipeline covering:

- body compatibility
- rig / skin weights
- clipping
- animation deformation
- attachment sockets

Do not burn Hero generation quota on a large wardrobe before that system exists.

## Benchmark

Continue to use **Cloud Whale Station** as the main regression world.

The first Full-3D library benchmark should prove:

- common environment pieces are reused from the library
- Sky Whale can come from Hero generation
- procedural fallback remains available
- Nancy can navigate the same canonical Blueprint
- returning to the World later loads the exact same asset identities
- a later Story/Video mode can reuse the same World without regenerating assets

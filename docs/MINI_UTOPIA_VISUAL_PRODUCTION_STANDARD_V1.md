# Mini Utopia Visual Production Standard v1.0

> **Soft Blocky Toy Diorama + Constructed Toy Grammar**
>
> Every object should look designed from a few beautiful toy-like masses, not sculpted from hundreds of small details.

This document is the production-facing authority for Canon 3D assets. It refines the earlier Visual DNA into rules that can be applied to third-party assets, GPT image generation, image-to-3D reconstruction, Golden Asset curation, and Godot runtime assembly.

## 1. Locked visual direction

### Core geometry rule

**Structure boxy. Silhouette rounded. Hero may be organic. Organic does not mean detailed.**

The same language applies across the game, with different strictness by asset class:

| Asset class | Blockiness | Curves | Production rule |
| --- | --- | --- | --- |
| Architecture / props | highest | bevels and limited rounded accents | modular, readable, buildable |
| Nature | medium | allowed as large clumps | tree crowns 3–5 masses; rocks use large faces |
| Characters | KayKit-compatible | allowed | preserve compact playable proportions |
| Hero body | low | free | one strong organic primary mass; no fragile micro-geometry |
| Hero attached structures | high | same as architecture | platforms, stairs, towers, rails follow kit rules |

### Constructed Toy Grammar

A production asset should decompose visually into:

1. **Primary mass** — the identity-bearing shape.
2. **Secondary masses** — 2–5 clear structural parts.
3. **Tertiary details** — a small number of large readable accents.
4. **Micro detail** — should normally be color, decal, shader or Godot dressing, not geometry.

Design guidance for shape hierarchy is approximately large : medium : small = 1 : 1/3 : 1/9. This is a visual guideline, not a numeric validation rule.

### Geometry guardrails

- Bevel target: visually obvious, generally about **5–12%** of local part thickness.
- Bevel hard ceiling: avoid exceeding roughly **20%** of the shortest local dimension unless the object is intentionally organic.
- Thin rods, rails and supports must read at gameplay camera distance. If too thin, thicken them or replace them with a solid panel.
- Ordinary assets should use no more than **3–5 meaningful tertiary parts**.
- No dense repeated micro-parts.
- Avoid unsupported thin fins, whiskers, wires, chains, flags, thin sheets and tiny suspended elements in image-to-3D input.
- At least one clear planar surface should remain visible on constructed assets.
- Flat-shaded low-poly facets are not the default identity; soft bevels and toy-like masses are.
- Repeated unit cubes and pixel textures are not Canon.

## 2. Style anchors and source policy

### Geometry authority

**KayKit is the primary geometry/style anchor** for Golden Asset curation.

Other sources are compatible only when they pass the same production tests:

- Kenney Castle: architecture supplement.
- Kenney Fantasy Town: utility pieces only unless explicitly approved.
- Quaternius: nature, props and creature supplement; curate before Golden promotion.
- AI-generated assets: reserved for original Mini Utopia concepts or gaps not covered by the Golden Library.

Third-party source files and atlases are immutable. Never overwrite the original package.

```text
Source asset / source atlas
        ↓ curate
Semantic mapping
        ↓ derive
Golden asset / Golden atlas
        ↓
Godot
```

## 3. Golden Asset acceptance tests

An asset may enter the Golden Library only after these checks:

### Lineup Test
Render it beside approved KayKit-derived Style Anchors. It must not look like a different asset pack.

### 64 px Silhouette Test
At small size the asset remains identifiable. A Hero must remain recognizable by its primary silhouette.

### Grayscale Readability Test
Critical gameplay objects, character and ground must retain clear value separation without relying on hue.

### Construction Test
Primary, secondary and tertiary masses can be named and understood. Medium forms must not collapse into one soft blob.

### Gameplay Test
Scale, collision intent, walkability and camera clearance are known before final promotion.

## 4. Color architecture

Mini Utopia uses **Semantic Slots + Core Palette + Curated Biome Profiles**.

### Core
Defines persistent Mini Utopia visual DNA.

### Semantic gameplay roles
Interaction, danger, quest and other gameplay state colors are global and are not baked into the static environment atlas.

### Curated biome profiles
A small approved set such as:

- CORE
- CLOUD
- FOREST
- MOON
- SNOW
- AUTUMN

Profiles inherit from Core and override only approved semantic material slots. Do not create one-off per-scene palettes.

### Value hierarchy

Target screen-area behavior:

- Light: about 60–70%
- Mid: about 20–30%
- Dark anchors: about 5–10%
- Glow/emissive accents: under 5%

Macaron means soft color behavior, not zero contrast.

Exact HEX values are **not locked by this document**. Candidate values live in the versioned palette profile and must be validated in the Godot Style Calibration Lab before becoming Palette v1.0.

## 5. Atlas strategy

Primary route: **offline bake**.

```text
Source Atlas (read-only)
→ Swatch Registry
→ Pack Cell → Semantic Slot mapping
→ Palette Profile
→ Bake
→ Golden Atlas
```

Runtime recolor is reserved for state:

- hover / selection
- quest / danger
- damage feedback
- temporary magic
- art-preview hot reload
- approved time/season transition effects

Do not use a runtime shader as the default solution for whole-biome palette replacement.

A physical Mini Utopia Master Atlas is a later optimization stage. Semantic slots are standardized now; global atlas repacking is not required for v1.

## 6. GPT reference stack

### Production reference stack

For ordinary props/nature:

1. one versioned Golden Style Sheet
2. one or two same-category Golden studio renders
3. text geometry rules

For Hero components:

1. one versioned Golden Style Sheet
2. one or two same-family Golden studio renders
3. one target blockout render
4. text geometry and reconstruction rules

Game screenshots are mood references, not reconstruction references.

Reference images should not contain labels, arrows or measurements that the image model may reproduce.

## 7. Concept image vs reconstruction reference

These are different deliverables.

### Concept image
May contain cinematic composition, fog, DOF, glow and story dressing. It decides the idea.

### Reconstruction reference
Exists only to produce a clean 3D model.

Required baseline:

- one object/component
- 3/4 camera
- about 25° elevation and 35° yaw
- minimal perspective distortion
- entire object visible
- subject occupies about 70–85% of frame
- flat light neutral background
- soft even top/front light
- matte opaque materials
- 5–8 clear palette colors
- clear part color separation
- one primary mass
- 2–5 secondary masses
- roughly no more than 10 tertiary visible details
- no DOF, bloom, fog, glow or complex environment
- no glass, water or transparency
- no fine rails, rope, wire, chain or thin flags
- no dense foliage
- no floating decorative fragments
- no high-frequency texture noise

Feature-size guidance:

- primary masses: large and dominant
- secondary forms: normally >= about 8% of image width
- tertiary forms: normally >= about 3–5%
- smaller information should become paint/decal/runtime dressing instead of reconstruction geometry

## 8. Hero production architecture

A Hero is unified **semantically**, not necessarily as one GLB.

The previous monolithic Unified Hero GLB approach is superseded for complex Hero clusters by **Unified Hero Assembly**.

Example:

```text
HeroWhaleStation.tscn
├── Whale.glb
├── Platform.glb
├── Tower.glb
├── PortalFrame.glb
├── Golden fence / lamps / plants
├── PortalFX
├── Collision
└── gameplay scripts
```

Split a Hero before reconstruction when any of these are true:

1. more than three major semantic components with different function/material
2. an important component occupies less than roughly 8% of the reference
3. meaningful component occlusion is roughly over 25%
4. a component needs independent animation, interaction or collision
5. the design includes transparent, emissive or water effects
6. important parts depend on thin connectors such as rails, rope or bridges

Portal emission, water, particles, distortion and other effects belong in Godot, not in the reconstruction mesh.

## 9. Production pipeline

```text
Idea / Blueprint
      ↓
Existing Golden asset? ── yes → use / compose
      │
      no
      ↓
Blockout
      ↓
Concept design
      ↓
Reconstruction-safe reference
      ↓
Image-to-3D component
      ↓
Mesh cleanup
      ↓
Palette mapping
      ↓
Golden Asset
      ↓
Godot Hero Assembly
      ↓
Lighting / FX / collision / gameplay
```

## 10. Anti-drift rules

### Avoid generic low-poly pack soup
- palette must use approved semantic slots
- scale must match the global gameplay scale
- every Golden candidate must pass the Lineup Test

### Avoid Minecraft / voxel drift
- no pixel textures
- no surface detail made from repeated unit cubes
- constructed forms need visible bevel language
- at least one rounded, cylindrical, angled or organic mass should break pure cuboid repetition where appropriate

### Avoid over-soft AI clay
- bevels have an upper limit
- preserve clear planes
- medium forms must remain distinct
- use 64 px silhouette and grayscale tests
- rounded does not mean melted

## 11. Change control

Changes to Geometry DNA, Color Architecture, Reconstruction Standard or Golden acceptance tests require an explicit version bump.

Prompt templates are downstream consumers of this standard and must not redefine it.

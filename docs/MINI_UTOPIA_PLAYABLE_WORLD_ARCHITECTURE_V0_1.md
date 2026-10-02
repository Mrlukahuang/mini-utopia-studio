# Mini Utopia Playable World Architecture v0.1

## Purpose

Mini Utopia Worlds are not static pictures. A child first imagines a world, AI helps visualize it, the creator chooses/refines the direction, and the Studio translates that approved direction into saved structured data that can later be rendered as an expandable playable 3D world.

Creation flow:

```text
Imagine → Visualize → Choose / Refine → Blueprint → Build → Explore → Record
```

## 1. Global Style Canon

Visual language is a Universe-level rule, not a Character-owned rule.

The Mini Utopia base STYLE asset is inherited by:
- Characters
- Worlds
- Terrain
- Architecture
- Props
- Portals
- Runtime materials
- Director Camera presentation

Character-specific identity data such as exact hair, eye, clothing or favorite-color HEX values remains Character data.

World theme colors may differ, but both Character and World must obey the same global Mini Utopia color constitution:
- high lightness
- low-to-medium saturation
- soft gradients
- gentle contrast
- macaron-compatible palette families
- matte collectible-toy material response

This avoids treating the World as if it must "match a Character". Both are siblings inheriting the same visual constitution.

## 2. Concept Art Is a Visual Anchor

AI-generated concept art is intentionally used for creative divergence.

It may define:
- atmosphere
- composition
- landmark ideas
- palette direction
- surprising visual ideas
- architecture language
- spatial relationships

It is not executable geometry and is not the source of truth.

After creator approval, the Studio records a `WorldVisualAnchor` and produces a structured `WorldBlueprint`.

## 3. World Blueprint Is the Source of Truth

The saved Blueprint defines:
- initial grid
- chunk layout
- spawn point
- landmarks
- Portal
- walkable / blocked zones
- camera points
- Director Camera tours
- expansion borders
- approved concept constraints

The runtime is replaceable. The first renderer target is Three.js/Web, but the Blueprint must remain independent enough to support another runtime later.

## 4. Initial Playable Area

Default v0.1:
- 50 × 50 cells
- cell size: 1 world unit
- 10 × 10 cells per chunk
- 25 initial chunks

World growth happens by creating new chunks beyond an open expansion edge. Existing chunks are not regenerated merely because the world expands.

## 5. Modular Assets

A playable world should prefer reusable Assets over one monolithic mesh.

Examples:
- terrain modules
- trees
- houses
- bridges
- lamps
- plants
- landmarks
- Portals

Special one-off assets can be introduced later, but the Blueprint references them rather than embedding runtime-specific geometry.

## 6. Director Camera

Director Camera is data-driven.

A World may save:
- establishing viewpoints
- Portal reveal
- landmark orbit
- character follow points
- flythrough points
- ending shot
- tour routes and timing

This allows the same playable world to serve both:
1. exploration / mini-game
2. recorded World Tour / video production

## 7. Asset Identity

v0.1 continues to use:
- `AssetType.LOCATION`
- `LOC_<ID>`

A Mini World is a richer Location profile for now.

Do not introduce a separate WORLD asset type until one World genuinely needs to own multiple independent Location assets.

## 8. Human Review Gates

Important approvals:
1. Concept direction
2. World Blueprint
3. Playable build
4. Director Tour, when used for production

The child decides what exists. The Studio decides how it belongs to Mini Utopia.

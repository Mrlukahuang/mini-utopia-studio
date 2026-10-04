# M3.5 Core CC0 Asset Audit

This audit is based on the four source ZIPs supplied for the Mini Utopia
Full-3D foundation.

## Verified source packs

| Pack | License file verified | Model payload in supplied ZIP | Role |
| --- | --- | ---: | --- |
| Quaternius Stylized Nature MegaKit Standard | CC0 1.0 | 68 glTF models | secondary scenic/high-detail nature |
| KayKit Forest Nature Pack 1.0 FREE | CC0 1.0 | 105 glTF models | primary lightweight core nature |
| Kenney Fantasy Town Kit 2.0 | CC0 1.0 | 167 native GLB models | primary modular architecture |
| Quaternius Fantasy Props MegaKit Standard | CC0 1.0 | 94 glTF models | selected story/environment props |

All four supplied license files explicitly permit commercial use through CC0.

## Important technical finding

The packs have very different web-runtime characteristics.

### KayKit Forest

KayKit uses one small shared 1024×1024 forest atlas. A representative converted
Tree GLB was about **0.08 MB** in the local audit.

This makes KayKit the strongest default source for repeated trees, bushes,
grass and rocks in the first Mini Utopia library.

### Kenney Fantasy Town

Kenney already ships compact native GLB.

Across the supplied 167 GLBs, the local audit found a median file size around
**10 KB** and the largest asset around **134 KB**.

This is ideal for repeated modular walls, roofs, roads, stairs, fences,
fountains and similar gameplay structure.

### Quaternius Stylized Nature

The visual direction is useful for Mini Utopia, especially as richer scenic
nature, but the source pack relies on larger 1K/2K shared textures.

A representative CommonTree conversion was roughly:

- naïve self-contained GLB: about **8.8 MB**
- after 512px source-texture normalization: about **1.05 MB**

Therefore these assets should be selectively imported rather than used as the
default repeated foliage set.

### Quaternius Fantasy Props

The props are useful, but the source pack includes several 2K/4K trim/PBR
textures.

A representative Bench conversion was roughly:

- naïve self-contained GLB: about **14.7 MB**
- after 512px source-texture normalization: about **1.37 MB**

This confirms that blindly converting every prop to a self-contained GLB would
waste web bandwidth. Selected props should pass the offline texture ceiling
first.

## Core Asset Pack v1 selection

The first curated pack selects **69 high-reuse assets**:

| Source | Selected |
| --- | ---: |
| KayKit Forest | 24 |
| Kenney Fantasy Town | 25 |
| Quaternius Nature | 10 |
| Quaternius Props | 10 |

By Mini Utopia category:

- 13 trees
- 8 plants/bushes/flowers
- 5 grass variants
- 7 rocks
- 1 mushroom
- 23 architecture modules
- 12 props

After conversion/normalization, the local build measured about **19.8 MB** of
GLB payload and about **17.8 MB** for the complete compressed portable pack.

The binaries are deliberately **not committed to Git**. They belong in
ObjectStorage through the reusable library importer.

## Selection strategy

### Default repeated nature

Use KayKit first:

- simple trees
- bushes
- grass
- rock clusters

Reason: compact, game-ready, visually compatible with the rounded toy direction,
and efficient for repeated placement.

### Modular construction

Use Kenney first:

- walls
- doors/windows
- stairs
- roof modules
- roads/paths
- fences
- pillars
- planks/bridge pieces
- fountain/windmill modules

Reason: native GLB, tiny payloads and strong modularity.

### Scenic accents

Use selected Quaternius Nature where the World benefits from more organic visual
detail:

- twisted/fantasy trees
- flowers/ferns
- mushrooms
- scenic rocks

### Story props

Use selected Quaternius Props only after texture normalization:

- benches
- lanterns
- chests
- books
- potions
- candles
- cauldrons
- tables/chairs
- crates

## Style review

The current portable pack remains **style_status=raw**.

M3.5 normalizes technical placement:

- Y-up
- model base aligned to Y=0
- centered X/Z
- self-contained GLB
- stable source/license metadata
- SHA-256 identity

The next style layer will inspect/normalize:

- Mini Utopia macaron palette
- roughness/metalness
- texture strength
- silhouette compatibility
- target scale classes
- thumbnail/review approval

Only style-approved library assets should become automatic Blueprint matches.

## Full-3D sourcing rule

```text
semantic object needed
        ↓
approved reusable asset?
        ├─ yes → reuse stable asset ID
        └─ no
            ↓
simple structural geometry?
        ├─ yes → procedural
        └─ no
            ↓
creator-specific / identity-bearing?
        └─ yes → Pixal3D or future Hero provider
```

This protects both GPU quota and future Story/Video continuity.

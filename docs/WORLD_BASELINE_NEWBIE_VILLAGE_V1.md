# Mini Utopia World Baseline — 新手村 100×100 v1

Status: **LOCKED BASELINE**  
Scene: `res://scenes/newbie_village_100x100_v0_1.tscn`

This document is the source of truth for the first explorable Mini Utopia village world. Future village iterations should preserve these rules unless this baseline is explicitly versioned.

## 1. World goal

新手村 should feel like a beautiful, spacious, storybook valley that is worth exploring rather than a dense asset showcase.

The design must balance:

- **合理性** — clear circulation, readable zones and road-facing buildings.
- **探索性** — layered elevation, outer paths, lookout areas and edge encounters.
- **美观性** — lush forest-valley composition with breathing room and strong silhouettes.
- **可玩性** — navigable roads, solid collisions, resource areas and light combat/exploration hooks.

## 2. Locked map rules

- Playable footprint: approximately **100 × 100 world units**.
- Terrain language: **NO hex / honeycomb terrain**.
- Settlement sits on a broad valley floor enclosed by layered highlands.
- Structural terrain uses solid terraced masses with grassy caps; visible natural dressing is led by **KayKit Forest Nature Pack**.
- Outer terrain should read as hills / cliffs / mountain shelves, not as repeated hex tiles.
- Major terrain is solid collision.

## 3. Road hierarchy

The road network remains deliberately simple:

- **1 north–south main road**
  - built from **KayKit Block Bits dirt blocks**
  - **3 blocks wide**
- **2 east–west branch roads**
  - built from the same Block Bits dirt language
  - **2 blocks wide**
- Roads organize the settlement; buildings support the roads instead of competing with them.
- The central plaza sits at the road core.

If a requested Block Bits dirt mesh cannot be found in the installed Asset Vault, the runtime may use a temporary solid dirt-block fallback and should emit a warning. The layout rules do not change.

## 4. Buildings and scale

- The village must contain **many buildings**, not a sparse demo row.
- Houses line both sides of roads and face the nearest road.
- Building scale must be comfortable next to the current ~1.6 m player.
- Ordinary homes target roughly **4.5–5.2 m visual height**.
- Landmark buildings can be larger.
- Leave gardens, tree pockets, yards and small gaps so the town has breathing room.
- Buildings receive simple solid collision proxies even when the source GLB has no usable collision.

## 5. Forest Nature Pack role

Use Forest Nature Pack as the primary natural visual language for:

- grass dressing,
- trees,
- bushes,
- rocks,
- cliff / mountain dressing,
- terrace edges,
- scenic pockets.

The structural terrain may use simple solid procedural masses underneath so the world remains reliable and collision-safe. Those masses should be visually softened and covered by Forest Nature assets rather than shown as a naked prototype grid.

## 6. Resource Bits role

Use **KayKit Resource Bits** to create believable work / gathering zones, including:

- log stacks,
- planks,
- stone chunks / bricks,
- pallets,
- crates or similar material props when present.

Resource props should be clustered into readable work yards instead of scattered randomly through the main street.

## 7. Skeleton encounters

- Exactly **2 skeleton soldiers** in the v1 baseline.
- They are **scattered** in different outer exploration zones.
- They do not spawn together and do not occupy the central safe plaza.
- They act as landmarks / encounter hooks for later gameplay.
- The runtime should select matching Skeleton Pack assets from the full Asset Vault.

## 8. Collision baseline

The following must be solid enough that the player cannot obviously walk through them:

- valley floor,
- outer terrain / mountain shelves,
- houses,
- major resource piles / large props where practical,
- encounter blockers / world boundary.

Use simple box / cylinder collision proxies when exact mesh collision is unnecessary. Playability and reliability are more important than perfect collision fidelity.

## 9. v0.1 composition target

The first implementation should include:

- 100×100 valley floor,
- layered outer terraces / mountains,
- one 3-block-wide main road,
- two 2-block-wide horizontal branch roads,
- central plaza,
- 36+ road-oriented buildings,
- multiple Forest Nature clusters,
- at least one Resource Bits work yard,
- two separated skeleton soldiers,
- two or more visually interesting outer highland / lookout areas,
- player spawn at the southern approach.

## 10. Non-goals

Do **not** reintroduce:

- hex terrain,
- dense random road networks,
- tiny toy houses that feel underscaled next to the player,
- a floating bridge,
- scenery with no collision where the player can obviously pass through it,
- one-off asset extraction workflows.

The Full Asset Vault is the reusable source for future world iterations.

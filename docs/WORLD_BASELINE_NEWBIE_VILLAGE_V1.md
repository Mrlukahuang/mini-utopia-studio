# Mini Utopia World Baseline — 新手村 100×100 v1

Status: **LOCKED BASELINE**  
Current scene: `res://scenes/newbie_village_100x100_v0_3.tscn`

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
- The visible village-floor language uses the **plain green KayKit Block Bits cube** over a reliable solid collision foundation.
- Outer terrain uses solid grey cliff masses with green block caps, then Forest Nature trees / rocks / bushes / grass to create the lush layered reference feel.
- The outer mountain composition must have **valley level + at least two additional elevation bands**.
- Outer terrain should read as layered hills / cliffs / mountain shelves, not as repeated hex tiles.
- Major terrain is solid collision.

## 3. Road hierarchy

The road network remains deliberately simple:

- **1 north–south main road**
  - built from the **plain yellow KayKit Block Bits cube**
  - **3 blocks wide**
- **2 east–west branch roads**
  - built from the same **plain yellow Block Bits cube**
  - **2 blocks wide**
- Roads organize the settlement; buildings support the roads instead of competing with them.
- The central plaza sits at the road core.

The runtime should prefer the plain Block Bits meshes whose filenames contain **yellow** for roads and **green** for village ground / house pads. If a matching local mesh cannot be found, it may use a temporary solid color fallback and must emit a warning. The layout rules do not change.

## 4. Buildings and scale

- The village must contain **many buildings**, not a sparse demo row.
- Houses line both sides of roads and face the nearest road.
- Houses must visibly sit **on green block terrain / raised green-capped pads**, not look pasted onto a flat plane.
- Edge neighborhoods should step upward so the village participates in the terrain rather than remaining completely flat.
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

The user's current Forest Nature archive is the free tier, so modular terrain meshes are not assumed. The world may use simple solid procedural cliff masses underneath, but they must be softened with green Block Bits caps plus Forest Nature trees, rocks, bushes and grass so the result follows the supplied layered-island reference rather than looking like naked prototype geometry.

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

## 8.1 Surface-alignment rule

This is a hard technical rule after the v0.2 smoke-test failure:

- A visible Block Bits surface and its physical collision top must resolve to the **same world Y**.
- Valley green blocks must finish at **Y = 0**.
- Yellow road tops must sit slightly above the green surface so they cannot disappear through coplanar overlap.
- Raised house pads must return one authoritative `surface_y`; the house bottom, cap collision, and visible green-block cap must all use that same value.
- Asset pivots must never be guessed. Block Bits cubes are box-fitted from measured mesh bounds.

## 9. v0.1 composition target

The first implementation should include:

- 100×100 solid valley floor,
- visible green Block Bits village ground,
- irregular layered outer cliff clusters with two additional elevation bands plus compact peaks,
- one yellow Block Bits 3-block-wide main road,
- two yellow Block Bits 2-block-wide horizontal branch roads,
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

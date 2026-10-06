# M4.11 — Green Terraced Mountain Town 50×50 v0.4

This pass is a direct response to the v0.3 visual review.

## Asset audit correction

The supplied **KayKit Forest Nature Pack** does **not** contain terrain / hill / mountain mesh blocks.

It contains the natural dressing layer:
- 20 grass GLTF variants
- 22 bush variants
- 43 rock variants
- 20 tree variants

The actual modular terrain / hills / mountains are in **KayKit Medieval Hexagon**:
- grass base + grass bottoms
- low/high grass slopes
- road tiles A–M + sloped road tiles
- river + river crossing tiles
- hill and mountain assemblies with grass / trees

This v0.4 therefore uses the packs by role:

- **Medieval Hexagon** → terrain, roads, river, terraces, mountain ring
- **Forest Nature** → real grass, bushes, rocks, trees
- **Resource Bits** → working-town resource yards
- **Block Bits** → kept as fallback; not needed in this pass

## Green terrain fix

The previous Candidate-B Medieval remap incorrectly treated the atlas grass swatch (row 2 / col 0) as a magic/glow color. That is why the v0.3 terrain became bright yellow.

v0.4 adds a dedicated derived profile:

`core_candidate_b_green_terrain`

For terrain assets it maps:
- grass → Sage green
- water → Aqua
- road → warm neutral

Buildings continue to use the normal `core_candidate_b` profile.

## World composition

New scene:

`res://scenes/green_terraced_mountain_town_50x50_v0_4.tscn`

The layout now has:
- one long main street from the south gate to the northern terrace
- exactly four winding side roads
- integrated river-crossing tile (no separate floating bridge object)
- layered grass-bottom support blocks for level-1 and level-2 terraces
- a high/low mountain + hill ring around the outside
- 30 buildings
- houses / special buildings automatically face the nearest street
- homes and landmarks on raised northern / side terraces
- expanded Forest Nature dressing
- Resource Bits around lumber / mine / market / blacksmith areas

## Local test

After Fetch/Pull, rebuild the local world kit because v0.4 adds new Forest variants and the new green-terrain derived profile:

```bash
python3 tools/prepare_mountain_town_assets.py --clean
```

Then let Godot finish importing and run:

`res://scenes/green_terraced_mountain_town_50x50_v0_4.tscn`

with F6 / fn+F6.

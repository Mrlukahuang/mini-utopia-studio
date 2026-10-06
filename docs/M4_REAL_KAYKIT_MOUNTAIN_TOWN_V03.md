# M4.10 — Real KayKit Mountain Town 50×50 v0.3

This milestone replaces the procedural-looking ground experiment with the actual terrain language already present in the user's KayKit library.

## Asset audit result

The local packs already contain the systems we need:

### KayKit Medieval Hexagon
- **15 road modules**: `hex_road_A` through `hex_road_M`
- sloped road modules for elevation changes
- base grass hexes + low/high sloped grass
- river modules + river crossings
- two bridge buildings
- preassembled hills and mountains, including grass + tree variants
- homes plus tavern, market, blacksmith, church, well, lumbermill, mine, windmill, watermill, barracks, towers and more

### KayKit Forest Nature
- 20 grass GLTF variants
- 22 bush variants
- 43 rock variants
- multiple rounded, blocky and pine tree families

### KayKit Resource Bits
- stone bricks / chunks
- logs / planks
- pallets
- textiles and other resource piles

### KayKit Block Bits
Useful as hidden utility/filler, but intentionally **not** used as the visible terrain language in v0.3. Making Block Bits the main ground would pull Mini Utopia toward voxel/Minecraft, which conflicts with the C+ Soft Blocky Toy direction.

## Creative direction

The world now becomes a **green mountain-ring village**, not a flat meadow with scattered buildings:

- 10×12 true Medieval hex terrain grid
- ~50×50 meter playable footprint
- real road hexes as streets
- real river hexes + bridge
- raised northern terrace
- sloped access road toward the terrace
- mountain/hill assemblies wrapping the village
- exactly 30 buildings
- homes on both valley floor and upper terrace
- town specials: tavern, market, blacksmith, church, well, lumbermill, mine, windmill, watermill, barracks, tower
- real Forest Nature grass / bushes / rocks / trees
- Resource Bits around working districts

## One-time local preparation

After Fetch/Pull run:

```bash
python3 tools/prepare_mountain_town_assets.py
```

The tool finds the already-downloaded ZIPs, extracts only the 87 versioned assets, and bakes Candidate B variants for Medieval + Forest. Source ZIPs remain untouched.

## Run

Open:

`res://scenes/mountain_town_50x50_v0_3.tscn`

Then run current scene with F6 / fn+F6 on macOS.

The previous v0.1/v0.2 scenes remain available for direct comparison.

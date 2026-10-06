# Mini Utopia · Godot Runtime Spike

Goal: a playable "newbie village" proving the new One Persistent World runtime direction.

## Engine
- Godot 4.7.2 stable
- GDScript
- Compatibility renderer (chosen so the same project can later export to Web/Streamlit iframe)

## Run
1. Open `godot/project.godot` in Godot 4.7.2.
2. Press **F6/F5**.
3. Click the game window once so mouse look captures.
4. WASD / arrows move, Shift runs, Space jumps, mouse looks, Esc releases mouse.

## Scope of v0.1
- third-person locomotion
- camera-relative movement
- collision and gravity
- warm whimsical storybook placeholder village
- one locked expansion gate representing the next WorldAtlas Zone

The art is intentionally placeholder geometry. Existing Mini Utopia asset packs and unified HF/Pixal3D Hero GLBs will replace these primitives incrementally without changing the runtime structure.

## Reference
Movement/camera behavior is intentionally modeled after the publicly available Kenney Starter Kit 3D Platformer (MIT; included assets CC0). See THIRD_PARTY_NOTICES.md.


## Zone 01 + real Hero workflow

The persistent world now includes a second runtime Zone behind the Newbie Village gate.

1. Run the game and approach the `NEW WORLD / Cloud Whale District` gate.
2. Press **E** near the gate to unlock the passage.
3. Zone 01 is already instantiated under the same WorldRoot; player and camera are not replaced.
4. Without a Hero bundle, Zone 01 shows a whale-shaped placeholder.
5. In World Factory > 3D Build Check, use **Prepare Godot Hero Bundle** on a stored Hero GLB.
6. Download the zip and extract it into `godot/assets/external/`.
7. Confirm these files exist:
   - `godot/assets/external/heroes/<hero>.glb`
   - `godot/assets/external/heroes/hero_manifest.json`
8. Return to Godot, let it import/rescan, then run again.

The Hero runtime loader supports:
- local `res://` GLB files
- filesystem GLB paths in desktop development
- HTTP(S) GLB URLs through `HTTPRequest`

Runtime GLB import uses Godot's `GLTFDocument` / `GLTFState` API, then uniformly fits the generated scene to the manifest target envelope and grounds it at the Hero root.


## Style Calibration Lab

Before locking palette HEX values or rewriting Canon asset-generation prompts, open `res://scenes/style_calibration_lab.tscn` and run the current scene (F6).

The Lab fixes camera, Filmic tonemapping, exposure and lighting, then shows the v0.9 Core Macaron candidate palette in COLOR / GRAYSCALE / SILHOUETTE lanes. See `STYLE_CALIBRATION_LAB.md` for the review workflow.


## Forest Village 50×50 vertical slice

After installing Golden anchors and baking `core_candidate_b`, open:

`res://scenes/forest_village_50x50_v0_1.tscn`

and run the current scene (F6 / fn+F6 on macOS).

This scene is generated from the versioned layout:

`res://config/worlds/forest_village_50x50_v0_1.json`

It uses real Golden Forest + Medieval assets, prefers the Candidate-B derived profile, adds simple gameplay collision proxies, and keeps the footprint inside a 50×50 meter boundary.

The layout is intentionally data-driven so density, placement and world composition can be iterated without hand-placing every object in the editor.


## Forest Village 50×50 Rich v0.2

To see the richer visual target without manually placing anything, open:

`res://scenes/forest_village_50x50_rich_v0_2.tscn`

and run the current scene (F6 / fn+F6 on macOS).

This keeps the real Candidate-B Golden Forest + Medieval assets, then adds the first reusable Ground & Dressing Kit:

- multi-tone meadow patches
- warm dirt underlay
- irregular low-poly stone road
- curved creek + banks + edge stones
- grass tufts
- clustered flowers
- pebbles
- mushrooms
- house-side flower gardens
- denser forest edge

The dressing is deterministic and driven by:

`res://config/ground/storybook_meadow_v0_1.json`

The richer world layout is:

`res://config/worlds/forest_village_50x50_rich_v0_2.json`

The earlier v0.1 scene remains available as a sparse baseline for comparison.


## Mountain Town 50×50 v0.3 — real KayKit terrain

This scene uses the actual Medieval Hexagon road / river / hill system plus Forest Nature dressing and Resource Bits.

Prepare local assets once:

```bash
python3 tools/prepare_mountain_town_assets.py
```

Then open:

`res://scenes/mountain_town_50x50_v0_3.tscn`

and run the current scene (F6 / fn+F6 on macOS).

The scene contains a real hex-terrain village with roads, river crossing, bridge, raised hill terrace, mountain ring and exactly 30 buildings.


## Green Terraced Mountain Town 50×50 v0.4

After pulling this milestone, rebuild the local world kit once:

```bash
python3 tools/prepare_mountain_town_assets.py --clean
```

Then run:

`res://scenes/green_terraced_mountain_town_50x50_v0_4.tscn`

This version fixes the yellow terrain with a dedicated green-terrain palette profile, uses one main street plus four winding side roads, removes the floating bridge object in favor of the integrated river crossing tile, builds layered terraces, places 30 street-facing buildings, and surrounds the valley with high/low hills and mountains.

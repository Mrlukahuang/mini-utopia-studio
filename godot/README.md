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

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

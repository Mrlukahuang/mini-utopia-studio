# Mini Utopia Style Calibration Lab

Open `res://scenes/style_calibration_lab.tscn` and run the current scene (F6).

The Lab is deliberately separate from the playable Newbie Village. It fixes a neutral viewing environment so palette decisions are made in the same renderer instead of from browser color chips.

## Current purpose

The first version is a **calibration scaffold**, not the final Golden Style Sheet. It renders the same toy-language test forms in three lanes:

- COLOR
- GRAYSCALE
- SILHOUETTE

It also renders all candidate Core colors from:

`res://config/style/core_palette_candidates_v0_9.json`

Use it to review:

- whether macaron colors remain distinct under Godot Filmic tonemapping
- whether Light / Mid / Dark separation survives grayscale
- whether structural shapes remain readable without hue
- whether Deep Ink is dark enough without becoming pure black
- whether Glow Gold reads as an accent rather than a large-area base color

## Locked viewing setup

- Godot Compatibility renderer
- neutral gray background
- Filmic tonemapper
- exposure 1.0
- fixed warm key light
- fixed low-energy cool fill
- fixed camera and FOV

Do not tune the palette in a different environment and call it final.

## Next calibration pass

After the first Golden Asset curation, replace/proxy the procedural forms with approved real assets representing:

- KayKit character
- architecture
- tree / nature
- rock
- prop
- creature
- terrain
- one Mini Utopia Hero component

Palette v1.0 should be locked only after the real-asset lineup passes color, grayscale and 64 px silhouette review.


## Golden Style Anchor install

The v1 lineup is versioned in:

`assets/catalogs/golden_style_anchors_v1.json`

The source ZIPs remain local and immutable. From the repository root run:

```bash
python3 tools/install_golden_anchors.py
```

The installer searches common local folders such as `~/Downloads`, extracts only the 13 curated anchor models plus their direct GLTF dependencies, and writes them under:

`godot/assets/external/golden/`

Those extracted binaries/textures are ignored by git.

After Godot finishes importing them:

- run `scenes/golden_anchor_lineup.tscn` to inspect all 13 source-geometry anchors
- run `scenes/style_calibration_lab.tscn` to compare the representative real COLOR lineup against the deterministic GRAYSCALE / SILHOUETTE controls

The first 13 anchors cover KayKit nature, architecture, gameplay modules, prop, character and creature geometry plus one Kenney Castle compatibility check.

This stage is for **geometry/style compatibility**, not final palette approval. The source materials remain unchanged until the semantic-slot atlas mapping step.

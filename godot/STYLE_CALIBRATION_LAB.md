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

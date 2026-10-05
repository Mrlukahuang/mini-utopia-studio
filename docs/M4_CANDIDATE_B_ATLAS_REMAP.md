# Candidate B Atlas Remap — First Pack Experiment

This milestone recolors only the first approved Golden packs:

- KayKit Forest Nature
- KayKit Medieval Hexagon

The source ZIPs, extracted source glTF files and extracted source PNG atlases stay unchanged.

## Bake locally

From the repository root, after Golden anchors are installed:

```bash
python3 tools/bake_golden_palette.py --profile core_candidate_b
```

Expected result:

```text
Baked forest_tree_round -> core_candidate_b
...
Baked medieval_bridge -> core_candidate_b

Baked 7 derived Golden assets for core_candidate_b.
Source glTF/PNG files were not modified.
```

The tool creates derived files beside the locally installed Golden copies:

```text
forest_texture__core_candidate_b.png
Tree_1_A_Color1__core_candidate_b.gltf

hexagons_medieval__core_candidate_b.png
building_home_A_red__core_candidate_b.gltf
```

and records their `res://` paths under `profile_res_paths.core_candidate_b` in the ignored local `installed_manifest.json`.

## Atlas mapping

Forest uses four horizontal semantic bands:

1. foliage
2. wood
3. stone
4. warm neutral

Medieval uses the pack's actual **4 row × 8 column** swatch grid. Each cell is assigned a Mini Utopia semantic material slot. The remap preserves the source cell's value gradient while moving its hue/chroma/value center to Candidate B.

This is deliberately a first-pass mapping. If a cell is semantically wrong on real geometry, adjust the versioned atlas map rather than hand-editing a model.

## Godot review

After the bake, let Godot import the new files and run:

`res://scenes/golden_palette_compare.tscn`

This shows the same four anchors twice under identical conditions:

- SOURCE
- CANDIDATE B

Then run:

`res://scenes/style_calibration_lab.tscn`

The real Forest/Medieval assets in the COLOR lane will automatically prefer the Candidate-B derived profile when it exists.

Do not promote Candidate B to Core Palette v1.0 until this real-geometry comparison is approved.

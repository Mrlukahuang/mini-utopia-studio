# M4.9 Ground & Dressing Kit v1

The rich 50×50 Forest Village is intentionally a **visual possibility test**.

It keeps the real Candidate-B Golden Forest + Medieval assets, then adds a reusable procedural ground layer so the scene no longer reads as buildings placed on a flat green board.

## New scene

`res://scenes/forest_village_50x50_rich_v0_2.tscn`

Run with F6 / fn+F6 on macOS.

## Ground language

The first profile is:

`res://config/ground/storybook_meadow_v0_1.json`

It controls:

- darker Sage meadow base
- overlapping Mint/Sage/Moss ground patches
- warm dirt road underlay
- irregular 8-sided stone pavers
- curved creek and warm banks
- creek stones
- clustered grass tufts
- flower meadows
- small pebble fields
- mushroom pockets
- three house-side flower gardens
- deterministic generation seed

## Production intent

This version is deliberately richer than the previous v0.1 so we can judge the upper visual range before deciding final density.

The ground dressing uses procedural C+ primitives for now because the immediate goal is composition and world feel. Real Golden grass/flower/mushroom assets can replace these primitive dressings later without changing the ground-profile contract.

The real architecture, trees, bushes and major rocks remain the installed Golden assets and prefer `core_candidate_b`.

## Comparison

Keep both scenes:

- `forest_village_50x50_v0_1.tscn` — sparse baseline
- `forest_village_50x50_rich_v0_2.tscn` — rich storybook pass

The contrast tells us how much dressing Mini Utopia actually needs.

# Third-party references

## Kenney Starter Kit 3D Platformer
Repository: KenneyNL/Starter-Kit-3D-Platformer

The Mini Utopia spike uses Kenney's starter kit as a behavioral/reference baseline for:
- CharacterBody3D-based movement
- camera-relative directional controls
- simple third-person camera
- gamepad-friendly action-map structure

Kenney's code is MIT licensed. Assets in the starter kit are CC0. This spike currently uses its own primitive placeholder art rather than copying Kenney binary assets.

Copyright notice:
MIT License
Copyright (c) 2026 Kenney

## Noto Sans SC (selected Simplified Chinese Web subsets)
Source: https://github.com/fontsource/font-files/tree/main/fonts/google/noto-sans-sc/files
Upstream source: https://github.com/google/fonts/tree/main/ofl/notosanssc
Font family: Noto Sans SC, regular (400), WOFF2 subsets 86–88, 105, 110–119 and Latin; original per-shard font data preserved.
License: SIL Open Font License 1.1 (OFL-1.1), **not CC0**. Full terms: `res://assets/fonts/OFL-NotoSansSC.txt`.
Subset selection: code points used by the existing Chinese Creator/My Heroes labels, plus standard controls; larger language families are not bundled. If other glyphs are introduced, extend only the necessary shard and verify screenshots.

## Noto Emoji (monochrome UI glyph fallback)
Source: https://github.com/fontsource/font-files/tree/main/fonts/google/noto-emoji/files
Upstream source: https://github.com/google/fonts/tree/main/ofl/notoemoji
Font family: Noto Emoji, regular (400), selected WOFF2 subsets 2–5 and 7–9. Used solely for UI labels containing emoji; **does not add a second Chinese UI font**.
License: SIL Open Font License 1.1 (OFL-1.1), **not CC0**. Full terms: `res://assets/fonts/OFL-NotoEmoji.txt`.

## KayKit Adventurers v1.0 (official selected equipment; A-008)
Creator: Kay Lousberg. Official source: https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0
Original pack: https://kaylousberg.itch.io/kaykit-adventurers
License: CC0 1.0 Universal, original `LICENSE.txt` copied unchanged to `res://assets/kaykit/adventurers/LICENSE.txt`.
Only these original files from `addons/kaykit_character_pack_adventures/Assets/gltf/` are included: sword_1handed, shield_round, staff, wand with paired binary sidecars and knight/mage texture atlases. Original official `Characters/gltf/Knight.glb` also included unchanged (3,659,532 bytes; source Git blob `717b56ca2b5ff5392679774725201ba03a3eefab`), with its Rig_Medium skeleton and bundled animations. Godot import, runtime Skeleton3D/AnimationPlayer checks and Web bundle must pass before PR3 completion.

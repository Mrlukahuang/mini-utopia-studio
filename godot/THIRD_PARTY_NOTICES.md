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


## KayKit Medieval Hexagon Pack 1.0 — selected village homes (A-010 / W1.5)
Creator: Kay Lousberg. Official source: https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0
License: CC0 1.0 Universal; original LICENSE.txt preserved unchanged as res://assets/kaykit/medieval/LICENSE.txt.
Only eight official low-poly medieval houses, building_home_A and building_home_B in blue, green, red, and yellow, are included with original glTF/.bin pairs and the original hexagons_medieval.png shared texture atlas. All Git blobs match official originals. They are instantiated as 20 houses with physical StaticBody3D blockers; the original upstream pack is not copied wholesale.
Fifteen visible villagers reuse the original KayKit Knight animation/skeleton asset already licensed above, with five distinct modular toy hats/head styles and three coat colors, instead of claiming fifteen separate upstream character models. Each villager and the player have a CharacterBody3D capsule collider.


## KayKit Medieval Hexagon — eight more authentic architecture meshes (V1-W15-01 / Lane A)
Official source: https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0
Creator: Kay Lousberg; license: CC0 1.0 Universal (existing unchanged `godot/assets/kaykit/medieval/LICENSE.txt`). Exact source-verified glTF and paired binary Git blobs: **tavern, church, market, windmill, blacksmith, tower_A, lumbermill, well**. Reuses official `hexagons_medieval.png` atlas. Along with the two existing home shapes, the village offers ten distinct base architectural meshes in twenty plots. Curated resources stay under A-010's 150MB ceiling.


## Lane A KayKit forest performance preparation (#404, unmerged draft)
Official CC0 1.0 original KayKit Medieval Hexagon sources: https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 ; tree_single_A/B and rock_single_A/B glTF plus paired original SHA-matched bin files. Author Kay Lousberg. Existing medieval/LICENSE.txt and hexagons_medieval.png are reused. Rendering uses region-clustered MultiMesh, no shadows, and independent lightweight BoxShape3D colliders. This is a draft until the owner measures iPad FPS.


## Lane A KayKit prop and stone-road performance preparation (unmerged Draft)
CC0 1.0 original source https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 by Kay Lousberg. Curated unchanged original glTF/bin for barrel, crate_A_small, crate_A_big, sack, flag_blue, wheelbarrow, hex_grass and hex_road_A; original SHA and medieval/LICENSE.txt/hexagons_medieval.png are reused. Visible grass/stone roads and props use low-draw-call MultiMesh, shadowless materials and visibility-range culling; market physics is 30 primitive boxes. Remains Draft until owner supplies real iPad FPS and approves budget.


## Lane A six distinct iPad NPC models (official KayKit-derived lightweight assets)
Official CC0 source: https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0 and https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Skeletons-1.0 (Kay Lousberg). Five unique meshes: Barbarian, Mage, Rogue, Rogue_Hooded, Skeleton_Warrior, added alongside existing unmodified Knight. Files with `_iPad.glb` suffix are **derived** from the official GLB, retaining original meshes, skin/skeleton, textures, scene transforms and only `Idle` and `Walking_A` clips; no synthetic geometry or procedural hats. Source Git blob SHAs respectively 66d312ab6dc02b35fb648e7585bfdddb4e02eeef, c89f19f6e707f6e07e4632a08876bd6d0172b082, c8827661105eef7b2bfbef3bc676d41a47625733, 5d2b1403240d5f9ffff12e02c007572038eca2a8, 769e85c9e4cee8d1bd0952ddb3e9d26293144581. Original CC0 1.0 terms apply. Each derived model is approximately 0.39–0.46 MB rather than 3.5–4.9 MB, reducing mobile Web texture/animation payload.

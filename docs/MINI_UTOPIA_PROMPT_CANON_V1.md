# Mini Utopia Prompt Canon v1.0

This document freezes the two basic outputs that all Canon character generation must preserve.

## 1. Layout Canon — Character Master Sheet

The approved layout direction is a structured character design board, not a poster.

Required visual zones:
- one larger hero three-quarter view
- one compact turnaround set: front, three-quarter, side, back
- one compact expression set: neutral, happy, curious, excited, surprised
- generous negative space
- light neutral Mini Utopia studio backdrop
- factual profile, palette, height, outfit names, IDs and brand marks are rendered by the application, not hallucinated by the image model

The image model must not render words, labels, measurements, IDs, UI cards, logos, watermarks or captions.

## 2. Style Canon — Mini Utopia Character Identity

The approved visual identity sits between voxel-world structure and construction-toy tactility while remaining original.

Required:
- Mini Playable Avatar
- human-like characters approximately 2.8–3.0 heads tall
- large head, compact torso, short limbs, slightly oversized hands and shoes
- chunky modular geometry
- soft square / rounded-cuboid masses
- simplified sculpted hair or fur masses
- matte collectible-toy materials
- macaron dreamscape palette
- clear game-ready silhouette
- warm cinematic light
- original forms, not branded game or toy assets

Avoid:
- photorealism
- realistic hair strands or skin
- long-legged fashion-doll anatomy
- generic smooth 3D animation styling
- plush-heavy rendering unless the character is explicitly plush
- anime illustration drift
- direct branded character anatomy, stud systems, proprietary textures, UI or signature assets

## 3. Prompt Composition Contract

Final prompt order:

Character Profile
→ resolved Wearable descriptions
→ exact HEX color swatches
→ Mini Utopia Style Canon
→ Character Master Sheet Layout Canon
→ strict negative rules
→ generation instructions

Style Canon has higher priority than decorative character detail.

## 4. Input Contract

Character Factory has exactly two entry modes:

1. Prompt Generate / 描述生成
   - free-form description is parsed into CharacterProfile
   - creator then reviews the same structured Custom Build fields

2. Custom Build / 自定义搭建
   - preset/select/multiselect first
   - no per-field prose boxes
   - selecting Custom means the creator explains it in the single final Extra Details field
   - name and exact numeric height remain direct inputs because they are data, not descriptive style fields

Both modes converge into one CharacterProfile and one generation pipeline.

## 5. Data Truth Rules

- HEX swatches are the source of truth for colors.
- Asset IDs stay internal.
- Wearable IDs must resolve to human-readable semantic descriptions before image generation.
- Application-rendered text always wins over generated-image text.
- Character approval remains a human gate: Keep This Look.

## 6. Change Control

Changes to Layout Canon or Style Canon require an explicit design decision and version bump.
Ordinary character content must never override these two Canon layers.

# Mini Utopia Baby Foundation v1

**Track:** BB-01 Initial Baby Foundation

## Goal

Give the creator one persistent Initial Baby companion with a permanent identity and visible growth.

## Canonical ownership

Baby companions are creator-owned companion records. They are not Equipment instances and are not permanently owned by a Character.

The roster owns:

- `babies[]`
- `active_baby_id`

Each Baby owns:

- permanent `baby_id`
- display name
- species/archetype
- deterministic persistent appearance seed
- growth stage
- level / XP / bond
- active flag
- cosmetics
- reserved ability / stat / evolution metadata

## v1 archetypes

- Cloud Baby
- Sheep Baby
- Star Baby
- Robot Baby
- Forest Baby

## Runtime hook

`BabyService.runtime_spec()` exposes the active Baby identity for the later Godot follow runtime. BB-01 does not implement companion following or combat yet.

## Deferred

BB-01 intentionally does not implement:

- Baby combat
- breeding
- needs
- a full evolution tree
- Baby equipment

## Smoke test

1. Open **🐣 My Baby**.
2. Pick an archetype and name the Initial Baby.
3. Add XP and Bond.
4. Rename the Baby.
5. Reload Streamlit.
6. Confirm the same Baby ID, appearance seed, name, level, XP, bond and active state remain.
7. Open **🎒 My Stuff** and **🎭 My Characters** and confirm the active Baby is visible in Character context.

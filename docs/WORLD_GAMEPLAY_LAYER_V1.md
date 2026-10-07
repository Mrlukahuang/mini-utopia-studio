# WORLD-01 · Reusable World Gameplay Layer v1

Mini Utopia keeps one canonical World Asset and overlays reusable gameplay
references instead of copying the map for every experience.

## WorldGameplayLayer

Stored inside the existing Location Asset metadata:

- `world_asset_id`
- supported modes
- Quest IDs
- Story IDs
- stable gameplay targets
- schema version / updated_at

No new World record is created.

## Experience modes

v1:

- `explore`
- `quest`
- `story_play`

A World starts as Explore. Registering a playable Quest adds Quest mode.
When that Quest references a Story, the same layer also adds Story Play.

## Targets

Quest objectives contribute stable target references to the World layer.

Examples from Newbie Village:

- `newbie_village_story_clue`
- `training_skeleton_01`
- `reward_bone_buckler`
- `newbie_village_portal`

Targets may include a position/prompt when the gameplay layer needs to create a
runtime marker. Enemy/loot targets can remain ID-only when the canonical World
already owns their spawn.

## Story / Quest integration

**Make Playable Quest** now registers its Story + Quest on the same Location
Asset. Repeating the operation is idempotent.

## PlaySession / Godot

Creator PlaySession carries:

- `world_asset_id`
- optional Quest
- optional `world_gameplay` layer

All three reference the same World.

Godot `MiniUtopiaWorldGameplayRuntime` exposes:

- supported modes
- Quest IDs
- Story IDs
- target lookup

The Player receives the World gameplay ID/modes as runtime metadata.

## Child-visible result

Explore World displays:

**One World · Multiple Ways to Play / 同一个世界，多种玩法**

with Explore / Quest / Story Play and counts for connected Quests/Stories.

## Persistence

The layer lives in Location Asset metadata, so SQLite/Supabase existing Asset
persistence carries it automatically. No destructive schema migration is
required.

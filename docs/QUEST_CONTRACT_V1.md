# GP-03 · Quest Contract v1

Quest is now a reusable data object instead of quest-specific Godot code.

## QuestDefinition

A Quest references existing content:

- `world_asset_id` — required Location Asset
- `story_id` — optional Story
- `universe_id` — optional Universe continuity
- start triggers
- ordered objectives
- rewards
- repeatability
- review status
- schema version

## Objective types

- `go_to_location`
- `defeat_enemy`
- `collect_item`
- `interact`
- `return_to_target`
- `open_portal`

Every objective has a stable `objective_id`, target, count and explicit order.
IDs and order values must be unique inside one Quest.

## Reward types

- `equipment`
- `baby_xp`
- `baby_bond`
- `unlock`

GP-03 defines reward intent only. GP-05 will execute generic reward creation.

## Persistence

SQLite stores Quest JSON in a dedicated additive `quests` table.
Existing databases are migrated safely through `CREATE TABLE IF NOT EXISTS`.

Supabase uses the existing `studio_records` table with `kind=quest`, so no
new Supabase schema is required.

## Reference Quest

The reference definition represents:

1. arrive in Newbie Village
2. defeat `training_skeleton_01`
3. claim `reward_bone_buckler`
4. open `newbie_village_portal`
5. earn Baby Bond and unlock the next Portal

The same definition can serialize to JSON without changing Godot source code.
GP-04 will make Godot execute this generic contract.

# GP-04 · Story → Playable Quest v1

GP-04 connects the existing structured Story Builder to the GP-03 Quest
contract and then to a generic Godot Quest runtime.

## Creator flow

1. Create a structured Story that references a Character and World.
2. Open **Stories**.
3. Choose **Make Playable Quest / 变成可玩任务**.
4. The Story is converted once and persisted as a QuestDefinition.
5. **Gear Up & Play** opens Dressing Room with that Quest active.
6. Dressing Room exports Character + Equipment + Baby + World + Quest in one
   Creator PlaySession.

Repeated conversion reuses the same Quest for the Story.

## Story beat mapping

The first gameplay template keeps Story meaning while using stable runtime
targets:

- ARRIVE → `go_to_location`
- DISCOVER → `interact` with a visible clue marker
- PROBLEM → `defeat_enemy`
- ADVENTURE → `collect_item`
- PORTAL → `open_portal`

Story prose becomes the child-visible objective label. Gameplay target IDs and
positions remain structured metadata instead of being guessed from prose.

The v1 proof targets the Newbie Village gameplay layer:

- `newbie_village_story_clue`
- `training_skeleton_01`
- `reward_bone_buckler`
- `newbie_village_portal`

Later World gameplay layers can supply different target templates without
changing the Quest runtime.

## PlaySession

`PlaySessionRuntimeSpec.quest` is optional and contains the same persisted
QuestDefinition. If a Quest is selected and no World was explicitly selected,
its `world_asset_id` becomes the PlaySession World.

Explore World preserves the active Quest when re-exporting the session.

## Godot runtime

`MiniUtopiaQuestRuntime` is event-driven and does not know Story-specific
Python code.

Supported runtime events match objective types:

- `go_to_location`
- `interact`
- `defeat_enemy`
- `collect_item`
- `return_to_target`
- `open_portal`

It provides:

- current objective HUD,
- visible interact/Portal markers from objective metadata,
- sequential count tracking,
- E-key interaction,
- Quest completion feedback.

The existing Training Skeleton publishes generic `defeat_enemy` and
`collect_item` events. It does not advance a named Quest directly.

## Headless proof

CI executes a Quest entirely through the generic runtime:

`ARRIVE → interact → enemy → item → Portal → complete`.

This proves the Quest is an event layer on the reusable World rather than a
second copy of the map.

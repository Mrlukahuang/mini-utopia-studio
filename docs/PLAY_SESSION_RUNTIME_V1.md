# Creator Play Session Runtime v1

## Purpose

One payload moves the Creator's saved state into a playable runtime without
reconstructing it independently.

`PlaySessionRuntimeSpec` contains:

- Character identity + `CharacterRuntimeSpec`
- persisted `EquipmentRuntimeSpec` and final HP / ATK / DEF
- Active `BabyRuntimeSpec`
- optional World identity

## Local development bridge

Creator pages write the latest session to:

`godot/runtime_state/creator_play_session.json`

The folder is ignored by git. When that file is absent, Godot can use the
committed schema/example payload:

`godot/config/runtime/creator_play_session_example.json`

This file bridge is a local prototype boundary. A production build can later
replace transport with an API or cloud sync while keeping the payload schema.

## Godot Player runtime

`MiniUtopiaCreatorPlayRuntime`:

1. loads the latest play session
2. applies body type / surface / hair / eye colors
3. builds animated arm / leg / foot nodes where needed
4. creates canonical equipment sockets
5. places right/left weapon sockets beneath the corresponding animated arms
6. attaches the same Equipment loadout through `MiniUtopiaEquipmentRuntime`
7. stores final stats on the Player
8. spawns the Active Baby through `MiniUtopiaBabyFollowRuntime`

## Baby follow v1

Baby v1 follows behind and to the side of the Player, bobs gently, and snaps
back when separated beyond the recovery distance. No Baby combat or needs are
introduced here.

## Creator flow

Dressing Room → **Play This Loadout** → Explore World.

Explore World updates the play-session payload with the selected World so the
same Character / Equipment / Baby bundle is ready for Godot.

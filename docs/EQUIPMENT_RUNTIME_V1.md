# Mini Utopia Equipment Runtime v1

**Track:** EQ-02 — 3D Equipment Runtime  
**Status:** Implementation contract

## Purpose

Bridge the same `CreatorCollection` and `CharacterLoadout` used by **My Stuff** into Godot without creating a second equipment system.

Python owns:

- owned Equipment Instances,
- rarity,
- HP / ATK / DEF,
- equipped item IDs,
- Definition metadata.

Godot consumes an `EquipmentRuntimeSpec`.

## Runtime slots

| Equipment slot | Avatar socket |
| --- | --- |
| Weapon Main | `Socket_Weapon_R` |
| Backpack | `Socket_Backpack` |
| Wings | `Socket_Wings` |
| Accessory | `Socket_Accessory` |
| Outfit | whole-body visual module |

The five socket names remain owned by `MiniUtopiaAvatarContract`.

## Asset strategy

`mesh_asset_id` is optional.

When a runtime item provides an Asset Vault-compatible mesh ID, Godot can instantiate it on the correct socket.

When no mesh is available yet, EQ-02 uses an intentionally simple procedural fallback. This lets the attachment contract be tested before final generated/imported equipment art exists.

## Body types

Slim / Standard / Chubby share the same logical socket names.

Only normalized socket positions change with body width.

A loadout must not be recreated or reassigned when Body Type changes.

## Smoke scene

Run:

`res://scenes/equipment_runtime_smoke_test.tscn`

Expected:

- three Avatars: Slim / Standard / Chubby,
- all three show the same loadout,
- Purple sword is attached to the right hand,
- Blue backpack is attached to the back,
- Green wings are attached to the wings socket,
- accessory and outfit are visible,
- HUD shows HP 129 / ATK 26 / DEF 19.

The Output panel should print one `EQ-02 smoke:` line per Body Type with attached slot names.

## Source-of-truth rule

The committed smoke JSON is only a deterministic fixture.

Real runtime payloads are created by:

`EquipmentService.runtime_spec(character_asset_id)`

and can be serialized with:

`EquipmentService.export_runtime_spec(...)`.

That service reads the exact same Collection and Loadout used by My Stuff.

## Definition of Done

EQ-02 is complete when:

- runtime spec round-trips through JSON,
- Godot parses the equipment runtime,
- Weapon / Backpack / Wings / Accessory attach to stable sockets,
- Outfit applies without changing the Character ID,
- Slim / Standard / Chubby all retain the loadout,
- one local Godot smoke test is visually approved,
- CI is green.

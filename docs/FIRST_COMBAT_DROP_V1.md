# Mini Utopia First Combat + Drop Loop v1

## Goal

Deliver the first visible progression loop:

**Creator Loadout → Newbie Village → Skeleton → Drop → My Stuff → Equip → Stronger Character**

## Controls

- WASD / arrows: move
- Shift: run
- Space: jump
- **F or Left Click: attack**

## Training Skeleton

A Training Skeleton spawns near the Newbie Village starting road.

- HP: 42
- attack: 8
- aggro range: 9
- attack range: 1.45
- Player damage uses the ATK from the current Creator Play Session
- Player damage mitigation uses the current DEF

The Player and Skeleton both expose visible world-space HP/status labels for the
first smoke-testable combat loop.

## First reward

Defeating the Training Skeleton writes one local combat receipt for:

**Bone Buckler / 骨盾**

- slot: Offhand
- rarity: Blue
- base stats: HP +5 / DEF +9
- not part of the starter collection

The reward is intentionally a progression item rather than another free starter.

## Persistence boundary

Godot writes receipts to:

`godot/runtime_state/combat_drop_inbox.json`

This runtime-state folder is ignored by git.

Opening **My Stuff** calls `CombatDropService.claim_available()`, which:

1. validates the inbox
2. resolves the canonical Equipment definition
3. creates a deterministic EquipmentInstance
4. adds it to CreatorCollection
5. records the permanent `drop_id` in `claimed_drop_ids`

The same receipt can be read repeatedly without duplicating the item. SQLite
process-restart tests lock this behavior.

## First-loop smoke

1. Equip a Character in Dressing Room.
2. Click **Play This Loadout** and select Newbie Village.
3. Launch the Newbie Village Godot scene.
4. Approach the Training Skeleton near spawn.
5. Press F / Left Click until it is defeated.
6. Confirm the console reports Bone Buckler dropped.
7. Return to Streamlit → My Stuff.
8. Confirm the Battle Reward banner and Bone Buckler in Collection.
9. Equip Bone Buckler and confirm DEF increases.
10. Restart Streamlit and confirm the item/loadout remains.

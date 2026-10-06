# First Child Play Loop v1

## Purpose

PLAY-04 closes the first child-visible Mini Utopia progression loop without
inventing a second progression database.

The loop is:

**Character → Initial Baby → Dressing Room → Equip → Enter World → Battle →
Drop → My Stuff → Equip Reward → Re-enter Stronger**

## Durable progress

Home derives the First Adventure card from saved Creator state:

1. a non-archived Character exists
2. an Active Baby exists
3. that Character has at least one persisted equipment slot
4. the non-starter **Bone Buckler / 骨盾** reward exists in Collection

The loop is complete only after the Training Skeleton reward has actually been
claimed into Collection. A temporary browser/session flag never marks the loop
complete.

After the reward is claimed, the card still distinguishes whether the Bone
Buckler has been equipped. This gives the child a clear next action while
keeping the completed-loop definition stable.

## Continue flow

Once a Character exists, **Continue Adventure / 继续冒险** routes to Dressing
Room. Dressing Room remains the preparation hub for:

- Avatar
- Equipment / stats
- Active Baby
- Play This Loadout

From there the existing PLAY-02 bridge exports the canonical Creator Play
Session to Godot.

## Battle and reward

PLAY-03 provides the first reachable Training Skeleton. Defeat writes a local
combat receipt. My Stuff claims the receipt idempotently into
CreatorCollection.

The first reward is:

- **Bone Buckler / 骨盾**
- Offhand
- Blue
- stronger defensive baseline than the starter Wood Shield

## Integration proof

The PLAY-04 integration test performs the full data loop:

1. create Character
2. create Initial Baby
3. equip starter main/offhand gear
4. export first PlaySession
5. write a Training Skeleton reward receipt
6. claim Bone Buckler
7. equip Bone Buckler
8. restart SQLite/services
9. export a second PlaySession
10. verify the same Baby persists, Bone Buckler is equipped, final stats are
    stronger, and the same receipt cannot duplicate

## Local acceptance smoke

After CI is green, the consolidated local smoke test should verify:

1. Home shows First Adventure progress
2. Dressing Room shows the 9-slot loadout + Active Baby
3. Play This Loadout prepares Godot
4. Newbie Village Player has Creator stats/equipment/Baby
5. Training Skeleton can be defeated with F or Left Click
6. returning to My Stuff claims Bone Buckler
7. Dressing Room can equip Bone Buckler
8. restarting Streamlit preserves the reward/loadout
9. playing again carries the upgraded offhand/stats

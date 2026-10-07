# BB-02 · Baby Growth Integration v1

The existing Baby identity now grows from real Quest completion rewards.

## Sources

BB-02 executes the existing generic Quest reward types:

- `baby_xp`
- `baby_bond`

It reads the same GP-05 Quest completion receipt used by equipment rewards.
There is no second gameplay/progression inbox.

## Persistence and idempotency

Baby XP / Bond are written through `BabyService` into the existing
`BabyRoster`.

The reward claim uses the same `claimed_quest_reward_ids` collection ledger:

- non-repeatable Quest → Quest + reward can grant once
- repeatable Quest → each completion can grant once
- no Active Baby → reward stays unclaimed and can recover later
- app/process restart → Baby state and claimed reward IDs remain durable

## Level

v1 keeps the existing simple growth rule:

`level = 1 + floor(total_xp / 100)`

This preserves BB-01 compatibility while making gameplay the real source of
growth. Evolution and growth-stage changes remain reserved.

## Child-visible result

Story-generated playable Quests now grant:

- +60 Baby XP
- +5 Bond

My Baby and My Stuff announce newly claimed growth. Manual child-facing
"Growth Smoke Controls" are removed.

Godot receives Baby Level / XP / Bond in the same PlaySession runtime spec and
the follow companion nameplate shows the current Level.

## Non-goals

BB-02 does not add:

- Baby combat
- needs/hunger
- breeding
- evolution tree
- Baby equipment

# Mini Utopia · MASTER PRODUCT ROADMAP v2.0

**Status:** Source of Truth  
**Locked on:** 2026-10-07  
**Repository:** `Mrlukahuang/mini-utopia-studio`

---

# 0. Why this roadmap exists

Mini Utopia has already built a large amount of foundation work: Character creation, World creation, durable persistence, Concept → Blueprint → Runtime, and a rough playable Godot world.

The next risk is no longer “can we build the technology?”

The next risk is:

> **Can the children see progress, participate regularly, and feel that Mini Utopia is becoming their game while the deeper World / Story / Gameplay systems are still being built?**

This roadmap therefore introduces an **Engagement Bridge** before Story → Gameplay is expanded.

The product sequence is now:

> **Create → Collect → Dress / Grow → Play → Story → Produce → Grow the Universe**

The children should always have something visible and playable while deeper systems are being developed.

---

# 1. Product North Star

Mini Utopia is a child-friendly creative game and production system where a creator can:

1. create a character,
2. customize and equip the character,
3. collect items,
4. grow a Baby companion,
5. enter reusable worlds,
6. explore and complete adventures,
7. turn adventures into stories,
8. direct those stories into episodes and videos,
9. keep the same characters, equipment, companions and continuity across the whole universe.

The child decides **what exists and what is fun**.

The Studio handles **how the systems fit together**.

---

# 2. Core product loop

```text
CREATE
  ↓
COLLECT
  ↓
CUSTOMIZE / EQUIP / GROW
  ↓
EXPLORE
  ↓
QUEST / STORY PLAY
  ↓
MAKE A STORY
  ↓
DIRECT / RECORD
  ↓
EPISODE / VIDEO
  ↓
NEW REWARDS / NEW WORLDS / NEW STORIES
  ↺
```

The loop must remain asset-first.

Characters, Worlds, Equipment, Babies, Props and Stories are reusable objects. They should not be rebuilt separately for every mode.

---

# 3. Product areas

The Creator experience is organized by **what the child wants to do**, not by technical subsystems.

## 3.1 Home / Adventure Hub

Purpose:

- show visible progress,
- provide Continue buttons,
- surface recent Characters / Worlds / Stories,
- show collection progress,
- show active Baby companion,
- show active quest / adventure,
- guide the child to the next fun action.

Home is not a technical dashboard.

### Future primary actions

- Continue Adventure
- Build My Character
- Open My Stuff
- Visit My Baby
- Explore a World
- Make a Story
- Make a Movie

---

## 3.2 Character / Avatar Lab

Purpose:

Create and customize the playable identity.

The first-generation Avatar system is deliberately constrained so that 3D equipment, animation and gameplay stay reliable.

### Locked Avatar simplification

All primary playable characters use one **KayKit-compatible Humanoid Rig contract**.

Playable body variation is limited to:

- **Slim**
- **Standard**
- **Chubby**

Identity comes mainly from:

- Species Head / Head Shell
- Skin / Fur / Surface Type
- Skin / Fur / Surface Color
- Eye Style
- Eye Color
- Hair Style
- Hair Color
- Body Type
- Outfit
- Equipment

We do **not** create a unique skeleton for every species.

### Species Head examples

- Human
- Elf
- Cat
- Sheep
- Robot
- Cloud Creature
- future compatible humanoids

A Species Head is identity, not ordinary removable equipment.

### First-generation appearance contract

```text
Avatar
├── Rig Family
│   └── Humanoid
├── Body Type
│   ├── Slim
│   ├── Standard
│   └── Chubby
├── Species Head
├── Surface Type
├── Surface Color
├── Eyes
├── Eye Color
├── Hair Style
├── Hair Color
└── Current Loadout
```

### Animation direction

Target:

- one humanoid skeleton contract,
- one shared animation library,
- KayKit Character Animations as the baseline animation source where compatible,
- one animation should work across Slim / Standard / Chubby,
- new characters must not require custom Walk / Run / Attack animation authoring.

Before the contract is locked, the exact imported bone map and animation compatibility must be smoke-tested in Godot.

---

## 3.3 My Stuff / Collection

Purpose:

Make progress visible and give the children something they can use every day.

My Stuff is the child-facing collection of reusable items.

### Initial categories

- Weapons
- Outfits
- Backpacks
- Wings
- Accessories
- later: Offhand / Shields
- later: Tools
- later: Baby cosmetics

Eyes / hair / skin are primarily Avatar appearance options, not loot equipment in v1.

### Collection principle

> **Items belong to the Collection, not permanently to one Character.**

A Character only stores a Loadout referencing owned Item Instances.

The same owned item can later be unequipped and used by another compatible Character.

### Child-visible progress

My Stuff should show:

- number of discovered items,
- rarity counts,
- categories completed,
- equipped items,
- newest items,
- favorite items,
- comparison against currently equipped item.

This is a major engagement system, not a backend inventory table.

---

## 3.4 Baby / Companion

Purpose:

Give every creator a persistent companion that starts small and grows alongside their progress.

The Baby system is intentionally small in v1 but must have a strong extension seam.

### v1 promise

Every creator can have an **Initial Baby**.

The Baby:

- has a permanent ID,
- has a name,
- has an archetype / species,
- has an appearance seed,
- starts in `BABY` growth stage,
- has Level / XP,
- has Bond,
- can be selected as Active Companion,
- is visible in My Character / My Stuff,
- later follows the Avatar in gameplay.

### v1 Baby data contract

```text
BabyCompanion
├── baby_id
├── display_name
├── species_id
├── appearance_seed
├── growth_stage
│   └── BABY
├── level
├── xp
├── bond
├── active
├── cosmetic_item_ids[]
├── ability_ids[]          # reserved
├── stat_modifiers         # reserved
└── evolution_metadata     # reserved
```

### Important rule

The v1 Baby is **not** a full combat pet system yet.

We keep hooks for:

- growth stages,
- evolution,
- skills,
- combat support,
- gathering support,
- Baby equipment,
- mood / needs,
- personality,
- species-specific growth,
- story participation.

But we do not block the current roadmap on those systems.

### Future loop

```text
Explore / Create / Quest
        ↓
      Baby XP
        ↓
   Bond / Growth
        ↓
New look / ability / story moment
```

---

## 3.5 Adventure / Play

Purpose:

Use the same Avatar, Equipment, Baby and World state inside Godot.

The current Newbie Village is the first rough playable-world baseline.

Adventure grows through several experience modes without duplicating the World.

### Experience modes

#### Explore

- walk,
- run,
- jump,
- discover,
- visit landmarks,
- find secrets,
- take screenshots / recordings.

#### Quest

- objectives,
- collection,
- NPC interaction,
- enemies,
- rewards,
- Portal progression.

#### Story Play

A saved Story becomes a playable event layer inside an existing World.

#### Build / Creative Play

Later:

- place decorative props,
- decorate a home,
- add small world objects,
- personalize unlocked spaces.

#### Director Play

Use the same World and Characters but switch from “player” to “director”.

---

## 3.6 Story Studio

Purpose:

Define **what happens**.

Story does not own Character / World / Item assets.

A Story references them.

### Current structured rhythm

```text
ARRIVE
  ↓
DISCOVER
  ↓
PROBLEM
  ↓
ADVENTURE
  ↓
SURPRISE
  ↓
PORTAL / NEXT WORLD
```

### Story Builder foundation status

At roadmap creation:

- PR #180 implements Story Builder v1 foundation.
- CI #277 passed.
- PR #180 is mergeable and pending merge.

Story expansion pauses after the foundation until the Avatar & Collection Engagement Bridge is usable.

---

## 3.7 Director / Production

Purpose:

Turn a Story into an Episode / short video.

Future production chain:

```text
Story
  ↓
Script
  ↓
Scene
  ↓
Shot
  ↓
Character placement / animation
  ↓
Camera
  ↓
Dialogue / narration
  ↓
Storyboard
  ↓
Godot capture / generated media
  ↓
Edit / subtitles / audio
  ↓
Final video
```

Story defines what happens.

Director defines how it is performed and filmed.

---

## 3.8 Studio Mode

Studio Mode is a backstage layer, not a child gameplay area.

It owns:

- model / provider configuration,
- job inspection,
- asset diagnostics,
- Supabase,
- GitHub / CI,
- Godot export,
- errors,
- retries,
- cost,
- advanced quality controls.

Creator Mode must hide this complexity.

---

# 4. Canon and Playground

Canon and Playground are not separate products.

They are a cross-cutting mode.

## Canon

Canon actions may contribute to:

- continuity,
- relationships,
- discovered places,
- items,
- Baby growth,
- lore,
- recurring characters,
- story history.

## Playground

Playground is unrestricted experimentation.

It does not automatically change official continuity.

### Future action

`Promote to Canon`

A successful Playground Character / World / Prop / Story idea can later be approved into Canon.

---

# 5. Shared runtime state

All modes must consume the same state.

Example:

```text
Character Asset
   +
Avatar Appearance
   +
Character Loadout
   +
Owned Equipment Instances
   +
Active Baby
   +
Final Stat Block
   ↓
Explore / Quest / Story / Director / Movie
```

A Character should not have to be reconfigured separately for each mode.

---

# 6. Equipment foundation

## 6.1 Equipment slots

v1:

- Outfit
- Weapon Main
- Backpack
- Wings
- Accessory

Reserved:

- Weapon Offhand
- Shield
- Tool
- Baby Equipment

---

## 6.2 Core stats

v1 uses only:

- ❤️ **HP**
- ⚔️ **ATK**
- 🛡️ **DEF**

Avoid adding complex RPG stats until combat proves they are needed.

### Character

Each playable Character has:

```text
base_hp
base_atk
base_def
```

### Equipment

Equipment may contribute:

```text
hp_bonus
atk_bonus
def_bonus
```

### Final Stat Block

```text
final_hp  = base_hp  + equipment hp
final_atk = base_atk + equipment atk
final_def = base_def + equipment def
```

Gameplay reads only the Final Stat Block.

---

## 6.3 Category tendencies

Initial balancing direction:

- Weapon → mainly ATK
- Outfit → mainly DEF / HP
- Backpack → mainly HP / utility
- Wings → small mixed bonuses; movement abilities later
- Accessory → flexible
- Eyes / Hair / Skin → cosmetic in v1

---

# 7. Rarity system

Locked rarity order:

1. 🟢 Green
2. 🔵 Blue
3. 🟣 Purple
4. 🟡 Gold
5. 🔴 Red
6. 🌈 Rainbow

Internal enum:

```text
GREEN
BLUE
PURPLE
GOLD
RED
RAINBOW
```

Display names can be changed later without changing the enum.

---

# 8. Random item generation

Randomness must be controlled and reproducible.

## EquipmentDefinition

Defines what a kind of item can be.

Example fields:

```text
definition_id
display_name
category
slot
mesh_asset_id
animation_class
compatible_tags
base_stats
allowed_affixes
rarity_rules
```

## EquipmentInstance

Represents the exact owned item.

```text
item_instance_id
definition_id
rarity
item_level
generation_seed
rolled_stats
affixes
special_effect_ids
created_at
```

### Deterministic generation

Every generated item stores `generation_seed`.

Reloading the item must never reroll its stats.

### Power Budget

Rarity uses a configurable power budget rather than arbitrary random numbers.

Example direction only:

```text
Green    1.00
Blue     1.25
Purple   1.55
Gold     1.90
Red      2.35
Rainbow  2.90
```

Exact values remain balancing configuration.

### Rarity probability

Probability must live in configuration, not hardcoded gameplay code.

No real-money random loot system is part of the child Creator experience.

Random equipment is earned through:

- treasure,
- quests,
- exploration,
- crafting / forge,
- creator rewards,
- future events.

---

# 9. Inventory and Loadout

## Inventory / My Stuff

Stores owned `EquipmentInstance` IDs.

## CharacterLoadout

```text
character_asset_id
outfit_item_id
weapon_main_item_id
weapon_offhand_item_id   # reserved
backpack_item_id
wings_item_id
accessory_item_id
active_baby_id
```

Loadout changes should update:

- Avatar 3D appearance,
- Final Stat Block,
- gameplay runtime,
- future Story continuity metadata where appropriate.

---

# 10. 3D Avatar contract

Target node contract:

```text
AvatarRoot
├── Skeleton / Humanoid Rig
├── Body
├── SpeciesHead
├── Eyes
├── Hair
├── Outfit
├── Socket_Weapon_R
├── Socket_Weapon_L
├── Socket_Backpack
├── Socket_Wings
└── Socket_Accessory
```

### Hard rule

Attachment sockets are stable contracts.

A Sword should be authored once and work across compatible Humanoid characters.

A Backpack should not require a unique placement implementation for every Character.

---

# 11. Clothing strategy

v1 Outfit is a **whole-body outfit module**, not separate shirt / pants / shoes.

Reason:

- fewer clipping problems,
- fewer rigging combinations,
- faster child-visible result,
- easier compatibility across Body Types.

Later versions may split Outfit after the Avatar runtime is proven.

---

# 12. Child-visible progress rule

This roadmap adds a permanent development requirement:

> **No long stretch of backend development without a child-visible improvement.**

At least every 1–2 implementation milestones should produce something the children can:

- see,
- collect,
- customize,
- equip,
- name,
- grow,
- explore,
- or play with.

A technically complete milestone that creates no visible Creator value should normally be paired with a visible follow-up before starting another deep infrastructure track.

---

# 13. Milestone plan

The old repository contains historical M3 / M4 implementation documents.

To avoid more numbering collisions, this roadmap uses **Track IDs**.

---

# PHASE A — Current Foundation / Freeze

## F-01 — Character Asset Foundation ✅

Already available:

- Character Profile
- Character Master
- reusable Character Asset
- persistence
- editing
- runtime bridge work

### Done when

Historical milestone already satisfied.

---

## F-02 — World Asset + Playable World Foundation ✅

Already available:

- World Factory
- Concept approval
- Blueprint
- visual-anchor pipeline
- runtime experiments
- Godot Asset Vault
- Newbie Village rough playable baseline

### Done when

Accepted for now.

Newbie Village remains visually rough but is frozen as a baseline while engagement systems are built.

---

## F-03 — Story Builder Foundation 🟡

Current implementation:

- PR #180
- CI #277 passed
- pending merge at roadmap creation

### Completion standard

- Creator can select Characters + World + optional Props.
- Creator can choose Canon / Playground.
- Creator can save ARRIVE / DISCOVER / PROBLEM / ADVENTURE / SURPRISE / PORTAL beats.
- Story stores Asset IDs, not copied asset content.
- old Stories continue loading.
- Supabase persistence smoke test passes.

### Gate

After merge and smoke test, Story expansion pauses.

---

# PHASE B — Engagement Bridge

This phase is the next highest priority.

Goal:

> A child can build a recognizable playable Avatar, own items, equip them, see stats change, and grow an Initial Baby while World / Story systems continue behind the scenes.

---

## AV-01 — Humanoid Rig & Avatar Contract

### Build

- inspect/import the chosen KayKit-compatible humanoid rig,
- verify bone names in Godot,
- verify KayKit Character Animations against the rig,
- define stable socket names,
- define `BodyType = SLIM | STANDARD | CHUBBY`,
- create Avatar appearance data models,
- maintain backward compatibility with existing Character assets.

### Completion standard

- one test Avatar can Idle / Walk / Run in Godot,
- the same animation works on all three Body Type test meshes,
- socket contract is documented,
- Character appearance config serializes and reloads,
- existing Character records still load,
- CI green.

### Child-visible result

Small 3D Avatar preview showing one moving character.

---

## AV-02 — Modular Appearance v1

### Build

- Species Head,
- Surface Type,
- Surface Color,
- Eye Style,
- Eye Color,
- Hair Style,
- Hair Color,
- Body Type selector,
- compatibility rules.

### Completion standard

A creator can change at least:

- 3 Species Heads,
- 3 Body Types,
- 3 surface/color combinations,
- 3 Eye styles,
- 3 Hair styles,
- multiple colors,

without changing the skeleton.

Changes persist after reload.

### Child-visible result

“Build My Character” starts feeling like a character creator instead of a technical form.

---

## AV-03 — Character Builder v2

### Build

Replace the current Creator-facing character workflow gradually with:

- visual choices,
- Avatar preview,
- simple labels,
- Save Character,
- edit existing Character.

Technical generation options remain in Studio Mode.

### Completion standard

A child can create / edit a Character without touching:

- JSON,
- model names,
- API concepts,
- raw prompts.

Saved Character reopens with the same appearance.

### Child-visible result

A reusable “dress-up / character builder” experience.

---

## EQ-01 — Equipment Data Foundation

### Build

- EquipmentSlot,
- EquipmentDefinition,
- EquipmentInstance,
- Rarity enum,
- deterministic generation seed,
- power budget config,
- HP / ATK / DEF,
- Inventory,
- CharacterLoadout,
- stat calculation.

### Completion standard

Tests prove:

- same seed → same item,
- rarity stays stable,
- item persists,
- duplicate Definition may create distinct Instances,
- equip / unequip recalculates stats,
- invalid slot compatibility is rejected,
- no existing Character data breaks.

### Child-visible result

May initially be limited; must be paired immediately with MY-01.

---

## MY-01 — My Stuff v1

### Build

Creator page showing:

- owned items,
- rarity,
- category,
- stats,
- equipped state,
- collection counts,
- comparison to current equipment,
- Equip / Unequip.

### Completion standard

A child can:

1. open My Stuff,
2. see at least one Green / Blue / Purple test item,
3. equip an item,
4. see HP / ATK / DEF update,
5. reload the app,
6. see the item and loadout preserved.

### Child-visible result

First real persistent Collection loop.

---

## EQ-02 — 3D Equipment Runtime

### Build

- Weapon socket,
- Backpack socket,
- Wings socket,
- Outfit replacement module,
- Accessory socket,
- animation-class metadata for weapons.

### Completion standard

In the 3D Avatar preview:

- Equip sword → sword appears in correct hand.
- Equip backpack → backpack appears on back.
- Equip wings → wings appear at correct back socket.
- Equip outfit → body outfit changes without breaking rig.
- switching Body Type does not detach equipment.
- reload preserves visual loadout.

### Child-visible result

“Equip” visibly changes the Character in 3D.

---

## BB-01 — Initial Baby Foundation

### Build

- BabyCompanion model,
- permanent Baby ID,
- name,
- species/archetype,
- appearance seed,
- `growth_stage = BABY`,
- Level / XP,
- Bond,
- Active Baby,
- persistence,
- reserved abilities / modifiers / evolution fields.

### Completion standard

A creator can:

- receive or create one Initial Baby,
- name it,
- see it on My Character / My Stuff,
- gain test XP,
- reload and preserve XP / Bond,
- select it as Active Baby.

No combat system required yet.

### Child-visible result

A persistent companion that visibly “belongs to me”.

---

## PLAY-01 — Dressing Room Playground

### Build

A lightweight play space, separate from full World gameplay.

Features:

- rotate Avatar,
- Idle / Walk / Run / Jump previews,
- Equip / Unequip,
- weapon animation preview,
- Baby visible nearby,
- live HP / ATK / DEF,
- collection shortcut.

### Completion standard

A child can spend several minutes changing appearance and equipment without using World Factory or Story Builder.

One session must support:

- change appearance,
- equip weapon,
- equip wings/backpack,
- see stats,
- see Baby,
- play at least 3 animations.

### Child-visible result

This is the first repeatable “Mini Utopia toy” while deeper gameplay is built.

### Engagement Bridge Exit Gate

Do not resume major Story → Gameplay expansion until:

- AV-01 ✅
- AV-02 ✅
- EQ-01 ✅
- MY-01 ✅
- EQ-02 ✅
- BB-01 ✅
- PLAY-01 ✅

Character Builder v2 may continue improving in parallel.

---

# PHASE C — Gameplay Fusion

After the Engagement Bridge is usable, connect Story + World + Avatar + Equipment.

---

## GP-01 — Shared Player State Contract

### Build

Godot receives:

- Character ID,
- Avatar appearance,
- Loadout,
- Final Stat Block,
- Active Baby,
- current World ID,
- optional Story / Quest ID.

### Completion standard

Changing equipment in Creator affects the next Godot session without rebuilding the Character.

---

## GP-02 — Basic Combat Foundation

### Build

- HP,
- ATK,
- DEF,
- damage formula,
- hit / damage / death state,
- weapon animation class,
- simple enemy health,
- respawn / safe reset.

### Completion standard

Player and one Skeleton can:

- detect hit,
- deal deterministic damage,
- reduce HP,
- die / reset safely.

No advanced RPG stats required.

---

## GP-03 — Quest Contract

### Build

Generic quest schema:

- quest_id,
- objectives,
- target IDs,
- trigger conditions,
- completion,
- rewards,
- story reference,
- world reference.

### Completion standard

One quest can be authored as data without changing Godot code.

Example:

- go to location,
- defeat skeleton,
- collect key,
- return / open Portal,
- receive reward.

---

## GP-04 — Story → Playable Quest

### Build

Convert a structured Story into one or more gameplay events / quests.

### Completion standard

A Story using Newbie Village can produce a playable sequence without duplicating the World.

Minimum proof:

```text
ARRIVE
→ discover clue
→ skeleton encounter
→ collect item
→ Portal unlock
```

---

## GP-05 — Loot & Reward Loop

### Build

Quest rewards can create Equipment Instances using the rarity / seed system.

### Completion standard

Complete quest → receive item → item appears in My Stuff → Equip → stats / 3D update.

This closes the first major game loop.

---

## BB-02 — Baby Growth Integration

### Build

Baby gains XP / Bond from selected activities.

Possible initial sources:

- finish quest,
- discover location,
- create Story,
- explore with Baby active.

### Completion standard

Baby progression is event-driven and persistent.

No evolution tree required yet.

---

# PHASE D — World Growth

## WORLD-01 — Reusable World Gameplay Layer

World stores stable environment data.

Gameplay layers add:

- NPCs,
- quest triggers,
- encounter spawns,
- loot,
- secrets,
- interactables.

### Completion standard

The same Newbie Village supports:

- free Explore,
- one Quest,
- one Story Play event,

without copying the map.

---

## WORLD-02 — Build / Creative Play v1

Later child-facing world personalization:

- place selected props,
- decorate unlocked areas,
- save layout deltas.

### Completion standard

Personalization persists without modifying the canonical base World geometry.

---

# PHASE E — Story & Living Universe

## STORY-01 — AI Story Suggestions

Add AI suggestions into the existing structured Story Builder.

Human remains the approval gate.

### Completion standard

AI proposes beats; creator can edit every beat before saving.

---

## STORY-02 — Continuity Context

Canon mode can read:

- current Character state,
- important owned items,
- Baby,
- prior Story history,
- known Worlds / NPCs.

### Completion standard

New Story suggestions can reference past approved continuity without duplicating old content.

---

## STORY-03 — Living Universe Memory

Track durable lore / relationships / major events.

### Completion standard

Canon continuity survives new model/provider versions and is inspectable in Studio Mode.

---

# PHASE F — Director / Production

## DIR-01 — Story → Episode

Create Episode from approved Story.

### Completion standard

Episode references Story ID and reusable asset IDs.

---

## DIR-02 — Script & Scene Breakdown

Generate / edit:

- scenes,
- dialogue,
- actions,
- locations.

### Completion standard

Human can approve scenes before shots are generated.

---

## DIR-03 — Shot List / Camera Plan

Create:

- shot IDs,
- camera,
- duration,
- action,
- expression,
- dialogue,
- continuity notes.

### Completion standard

A Scene can be represented by an ordered executable shot list.

---

## DIR-04 — Godot Director Mode

Use gameplay assets for staged performance.

### Completion standard

A shot can load:

- World,
- Character appearance,
- Equipment,
- Baby / companions,
- animation,
- camera.

---

# PHASE G — Storyboard / Media

## MEDIA-01 — Storyboard

Approved shot list → visual storyboard.

### Completion standard

Each shot has an approved visual planning frame or preview.

---

## MEDIA-02 — Capture / Video Generation

Combine:

- Godot capture,
- generated media where useful,
- voice,
- subtitles,
- audio.

### Completion standard

One short Episode can be rendered end-to-end.

---

## MEDIA-03 — Edit / Publish Package

Create:

- final video,
- subtitles,
- title,
- thumbnail / cover,
- platform metadata.

### Completion standard

One Episode can become a finished shareable short-form package.

---

# 14. Global Definition of Done

A milestone is not complete because code exists.

Every implementation milestone must satisfy the relevant items below.

## Engineering

- CI green.
- new models / services have tests.
- backward compatibility is tested when persistent data changes.
- no secrets in code or logs.
- failure path does not corrupt saved Creator assets.

## Persistence

Anything the child “owns” must survive:

- reload,
- redeploy,
- new session.

This includes:

- Characters,
- Avatar appearance,
- Inventory,
- Loadout,
- Equipment Instances,
- Baby,
- Baby XP / Bond,
- Stories,
- approved World state.

## Creator UX

Child-facing pages must not require:

- raw JSON,
- API keys,
- model/provider names,
- filesystem paths,
- GitHub concepts,
- stack traces.

## Runtime

A runtime feature is not complete until tested with the real Creator state, not only hardcoded test values.

## Visual Progress

At least every 1–2 milestones must produce a visible improvement or playable interaction.

---

# 15. Technical non-goals for the Engagement Bridge

Do not block v1 on:

- unlimited body morph sliders,
- a unique skeleton per species,
- complex cloth simulation,
- separate Top / Bottom / Shoes / Gloves slots,
- advanced elemental combat,
- multiplayer,
- Baby breeding,
- complex Baby evolution trees,
- paid random loot,
- MMO inventory economics,
- perfect Newbie Village art.

These can be revisited after the first closed gameplay loop works.

---

# 16. First closed-loop target

The most important intermediate target is:

> A child opens Mini Utopia, sees their Character and Initial Baby, changes appearance, equips a Purple sword, sees ATK increase, enters Newbie Village, defeats a Skeleton, receives a new item, returns to My Stuff, equips the reward, and both Character state and Baby progress remain saved.

When this works, the Avatar, Collection, Gameplay and Progression foundations are successfully connected.

---

# 17. First production-loop target

After the gameplay loop:

> The child turns that Newbie Village adventure into a structured Story, converts it into an Episode, directs it with the same Character / Equipment / Baby / World state, and produces a short video.

This is the end-to-end Mini Utopia promise.

---

# 18. Immediate execution order

Current:

1. Merge / smoke-test Story Builder PR #180.
2. Merge this Roadmap v2 documentation.
3. Start **AV-01 — Humanoid Rig & Avatar Contract**.
4. Then **AV-02 — Modular Appearance v1**.
5. Then **EQ-01 + MY-01** as a paired data + visible milestone.
6. Then **EQ-02 — 3D Equipment Runtime**.
7. Then **BB-01 — Initial Baby Foundation**.
8. Then **PLAY-01 — Dressing Room Playground**.
9. Only then resume the major Story → Gameplay track.

---

# 19. Development workflow

Default workflow remains:

```text
Agree direction
→ GitHub Issue
→ branch
→ implementation
→ tests
→ PR
→ CI green
→ user merges
→ Fetch / Pull
→ Creator / Godot smoke test
```

For routine implementation after a direction is already locked, the assistant should proceed directly to Issue / branch / PR rather than asking the user to manually create files or copy code.

---

# 20. Roadmap decision summary

The project is no longer optimized only for “technical completion”.

It is optimized for two goals in parallel:

### Goal A — Build the deep platform

- reusable worlds,
- stories,
- gameplay,
- production,
- living continuity.

### Goal B — Keep the children inside the project

- visible Avatar,
- My Stuff,
- equipment,
- rarity,
- stats,
- Initial Baby,
- collection progress,
- Dressing Room Playground.

Both are required for Mini Utopia to succeed.

The Engagement Bridge is therefore a **main-line product phase**, not side work.

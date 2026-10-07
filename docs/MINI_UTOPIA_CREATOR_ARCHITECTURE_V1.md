# Mini Utopia Creator Architecture v1

**Status:** Locked architecture contract  
**Track:** ARCH-01  
**Primary child runtime:** Godot 4.7.x  
**Studio surface:** Streamlit  
**Canonical metadata owner:** Python Core repository

## 1. Product boundary

Mini Utopia now has two product surfaces with deliberately different jobs.

### Godot — Mini Utopia Creator + Game

Godot is the child-facing interactive product.

It owns the **editing experience** for:

- Character Creator
- Avatar appearance
- Dressing Room
- Equipment Factory
- Baby interaction
- World Builder
- Director staging / camera / blocking
- Adventure / combat / exploration

Godot may read and write Creator state only through the Mini Utopia Bridge / Python Core contract. Godot must not create a second canonical Character, Equipment, Baby, World or Story database.

### Streamlit — Mini Utopia Studio

Streamlit is a **View / Studio / diagnostics surface**.

Target Creator-facing behavior is read-only:

- view Characters and their saved appearance
- view Equipment / Loadouts / stats
- view Babies and progress
- view Worlds and runtime state
- view Stories / Episodes / Shots
- view production jobs, diagnostics and generated media
- launch the relevant Godot Creator surface

Streamlit must not become the long-term realtime editor for Character appearance, Dressing Room, Equipment, World placement or Director blocking.

Existing Streamlit editors are migration-era legacy surfaces. They may remain temporarily so saved data stays accessible, but new Creator functionality must not deepen those editors.

## 2. One source of truth

There is exactly one canonical metadata model:

```text
                 Python Core
                     │
              Repository Contract
                     │
         SQLite local / durable backend later
                     │
          ┌──────────┴──────────┐
          │                     │
     Bridge API            Streamlit View
          │                   READ
          │
        Godot
     READ + WRITE
```

Rules:

1. Character IDs remain stable across Streamlit, Bridge and Godot.
2. Equipment Instances belong to CreatorCollection; CharacterLoadout stores references.
3. AvatarAppearance remains the canonical appearance payload.
4. Baby / World / Story IDs remain durable domain IDs.
5. Runtime JSON is a transport/cache representation, not a second database.
6. Godot `user://` may hold temporary session/cache/export files, never an independent canonical copy of Creator state.
7. Streamlit must not keep an editable shadow copy that can diverge from the repository.

## 3. Write policy

| Surface | Read | Write canonical Creator data |
|---|---:|---:|
| Python Core services | Yes | Yes |
| Godot Creator/Game | Yes | Yes, **through Bridge only** |
| Streamlit Studio | Yes | **No in target architecture** |
| Runtime/export JSON | Yes | No; transport only |
| Godot user:// cache | Yes | No; cache/session only |

Administrative Studio operations may still exist in Python Core, but Streamlit must call explicit service operations rather than mutate raw persistence payloads.

## 4. Bridge responsibility

The Mini Utopia Bridge is intentionally thin.

It translates HTTP/request payloads into existing domain services. It does not invent a second set of business rules.

Initial contract order:

1. health / version / session
2. Character read
3. Character update
4. Equipment collection / loadout
5. Baby
6. World
7. Story / Director as needed

Writes must be:

- validated with existing Pydantic/domain models,
- ID preserving,
- idempotent where Save may be repeated,
- backward compatible with existing persisted Creator assets,
- tested across process restart.

## 5. Character Creator contract

Godot Character Creator consumes the existing contracts:

- `AvatarAppearance`
- `humanoid_kaykit_v1`
- Slim / Standard / Chubby
- Species Head
- Surface / colors
- Eyes
- Hair
- nine-slot Equipment v2
- stable socket names
- semantic animations: Idle / Walk / Run / Jump

Changing Hair or Equipment in Godot must update the existing Character / Loadout, not create another Character.

## 6. Performance rule

Realtime Creator interactions must stay inside the persistent Godot scene.

A visual choice should mutate the existing runtime object, for example:

```text
set_hair("hair_bob_v1")
equip("weapon_main", ITEM_xxx)
set_body_type("chubby")
```

It must not require:

- rebuilding Streamlit,
- rebuilding a browser WebGL iframe,
- recreating the Character record,
- rewriting unchanged starter definitions.

AI generation and long-running asset production may show explicit loading states. Ordinary Creator choices should feel immediate.

## 7. Streamlit migration rule

During migration:

- do not delete existing saved Creator data,
- do not break legacy Character/Equipment readers,
- do not add new child-facing editing capability to Streamlit,
- replace Streamlit editors gradually with read-only views plus **Open in Mini Utopia** launch actions,
- remove legacy editor code only after the equivalent Godot path has been locally accepted.

## 8. Development / acceptance rule

CI proves contracts and persistence. It does not replace local Godot acceptance.

Godot milestones that change visible Creator behavior require local acceptance for:

- layout,
- readability,
- animation,
- attachment placement,
- responsiveness,
- child-facing interaction.

Routine Issue → branch → implementation → tests → PR → green CI → merge may proceed automatically under the approved roadmap. Stop only for material product decisions, destructive-data risk, blocked tooling, or a local visual acceptance gate.

## 9. Current migration sequence

The active migration sequence is:

1. ARCH-01 architecture lock
2. CLEAN-01 freeze Streamlit Creator expansion
3. BRIDGE-01 local Bridge
4. BRIDGE-02 Character read
5. BRIDGE-03 Character write
6. GODOT-CC01 Creator shell
7. GODOT-CC02 canonical 3D Avatar
8. GODOT-CC03 Species / Face / Surface
9. GODOT-CC04 Hair / Eyes / Colors
10. GODOT-CC05 animation preview
11. GODOT-EQ01 nine-slot runtime
12. GODOT-EQ02 socket / animation acceptance
13. GODOT-DR01 Dressing Room
14. GODOT-EF01 Equipment Factory
15. GODOT-EF02 rarity / stats / collection loop
16. GODOT-BABY01 Baby integration
17. LAUNCH-01 Streamlit → Godot launch
18. VIEW-01 Streamlit Character/Equipment read-only
19. WORLD-01 Godot World Builder foundation
20. PLAY-01 first complete child loop

## 10. Non-negotiable invariant

> **Streamlit may view. Godot may create and edit. Python Core owns the truth.**

Any implementation that introduces a second canonical Creator store or requires the child to use the Godot Editor violates this architecture.

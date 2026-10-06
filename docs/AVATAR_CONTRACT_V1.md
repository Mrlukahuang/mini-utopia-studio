# Mini Utopia Avatar Contract v1

**Track:** AV-01 — Humanoid Rig & Avatar Contract  
**Status:** Implementation contract  
**Runtime:** Godot 4.7.x  
**Rig family:** `humanoid_kaykit_v1`

---

## 1. Purpose

Mini Utopia v1 does not generate a unique skeleton for every Character.

All primary playable Characters share one humanoid rig contract so that:

- Idle / Walk / Run / Jump / combat animations can be reused,
- weapons attach once and work across compatible Characters,
- backpacks and wings use stable sockets,
- Slim / Standard / Chubby use the same animation set,
- future My Stuff / Equipment can depend on stable node names.

Character identity comes from modular appearance, not a unique rig.

---

## 2. Body Type

Playable v1 body types are locked to:

- `slim`
- `standard`
- `chubby`

The difference should stay visually readable but technically small.

The body variants must keep:

- the same skeleton hierarchy,
- the same bone names,
- the same normalized height,
- the same attachment socket names,
- the same animation contract.

Do not create separate animation libraries per Body Type.

---

## 3. Appearance contract

Persistent appearance is stored in `AvatarAppearance`.

Fields:

- `rig_family`
- `body_type`
- `species_head_id`
- `surface_type`
- `surface_color_hex`
- `eye_style_id`
- `eye_color_hex`
- `hair_style_id`
- `hair_color_hex`
- `compatible_tags`

The first-generation Character identity therefore focuses on:

1. Species Head / Head Shell
2. Skin / Fur / Surface type
3. Surface color
4. Eye style
5. Eye color
6. Hair style
7. Hair color
8. Body Type

Existing Character records remain valid. The modular Avatar layer is opt-in until Character Builder v2 marks `avatar.customized = true`.

---

## 4. Runtime socket names

These names are hard contracts:

```text
Socket_Weapon_R
Socket_Weapon_L
Socket_Backpack
Socket_Wings
Socket_Accessory
```

Future Equipment code must target these names rather than per-Character custom paths.

### Coordinate convention

Mini Utopia wrapper convention:

- Y = up
- Avatar root origin = floor contact under the Character
- Character faces the runtime forward direction after import normalization
- attachment meshes are authored around their own logical grip / mount point
- source-pack pivots may differ, but the Avatar wrapper must normalize them

Exact bone attachments for imported KayKit content are verified by the AV-01 local probe before we hardcode any source bone names.

---

## 5. Base animation names

The Mini Utopia contract exposes:

```text
Idle
Walk
Run
```

These are semantic runtime names.

The source animation clip names may differ.

If KayKit uses different imported clip names, a mapping layer should translate:

```text
Mini Utopia semantic animation
        ↓
source clip name
```

Future additions can include:

- Jump
- Attack_OneHanded
- Attack_TwoHanded
- Block
- Bow
- Magic
- Hit
- Death
- Wave
- Cheer

Do not make gameplay code depend directly on a source-pack filename.

---

## 6. KayKit Character Animations integration

The local Full Asset Vault is gitignored, so CI cannot see the user's installed KayKit animation ZIP.

AV-01 therefore contains a local Godot probe.

Scene:

```text
res://scenes/avatar_contract_smoke_test.tscn
```

The scene:

1. shows Slim / Standard / Chubby using one shared Idle / Walk / Run contract,
2. checks the local Asset Vault,
3. searches for a KayKit Character Animations candidate,
4. prints discovered Skeleton bone names,
5. prints discovered AnimationPlayer clip names.

### Local smoke-test output

Open Godot Output while running the scene.

Expected probe output will include lines such as:

```text
AV-01 probe: KayKit animation candidate = ...
AV-01 probe: Skeleton bones = ...
AV-01 probe: animations = ...
```

If the pack is not detected:

```text
AV-01 probe: KayKit Character Animations not detected.
```

In that case, place the KayKit Character Animations ZIP in one of the directories already scanned by:

```bash
python3 tools/install_full_asset_vault.py
```

The installer already accepts KayKit ZIPs containing `.gltf` / `.glb` assets.

---

## 7. Preview contract

The AV-01 preview deliberately uses simple procedural toy bodies.

It is not the final Character art.

Its purpose is to prove that:

- three body variants can share one contract,
- attachment sockets are stable,
- semantic animation switching works before appearance work begins.

The next milestone, AV-02, replaces the placeholder look with modular Species Head / Surface / Eyes / Hair choices.

---

## 8. Backward compatibility

Legacy Character Profiles do not need an Avatar block.

When a legacy Character loads:

- existing favorite/body colors remain the runtime fallback,
- existing hair color remains the runtime fallback,
- existing eye color remains the runtime fallback,
- default Avatar metadata does not override the Character until customized.

This protects existing Character assets while the new builder is introduced gradually.

---

## 9. Definition of Done for AV-01

AV-01 is complete only when:

- Python Avatar models serialize and reload,
- existing Character Profile payloads still validate,
- Slim / Standard / Chubby use one runtime contract,
- the five socket names are stable,
- Godot parses the smoke-test scene,
- Idle / Walk / Run semantic animations switch on all three preview bodies,
- local KayKit probe discovers and reports the actual rig / animation data, or reports that the pack is not installed,
- one local Godot smoke test is completed,
- CI is green.

The issue should stay open until the local KayKit probe is smoke-tested on the user's machine.

# Mini Utopia Local Bridge v1

**Track:** BRIDGE-01  
**Default URL:** `http://127.0.0.1:8765`

The Bridge is the local transport boundary between Godot Creator and Python
Core. It is **not** a second persistence layer.

## Run

From the repository root:

```bash
python -m studio.bridge.server
```

Optional overrides:

```bash
python -m studio.bridge.server --host 127.0.0.1 --port 8765
```

Environment equivalents:

- `MINI_UTOPIA_BRIDGE_HOST`
- `MINI_UTOPIA_BRIDGE_PORT`

The default host is loopback-only.

## BRIDGE-01 endpoints

### GET /health

Returns service health plus architecture invariants:

- service name
- Bridge protocol version
- canonical metadata owner
- Godot mutation policy

### GET /version

Returns Bridge / API schema versions.

### POST /session

Creates an in-memory Bridge client session:

```json
{"client":"godot"}
```

The returned session ID is transport/session identity only. It does not create
or duplicate a Character, Equipment collection, World or database record.

## Persistence

BRIDGE-01 deliberately performs no Creator metadata writes.

Later Character / Equipment / Baby / World endpoints must call existing Python
Core domain services and repository contracts. Godot must never become an
independent canonical store.

## CI proof

`godot/tests/bridge_health_smoke.gd` makes a real HTTP request from Godot to
the running Python Bridge. CI starts the Bridge on loopback and fails if Godot
cannot validate `/health`.


## BRIDGE-02 Character read contract

The Bridge now reads canonical Characters through the existing repository:

- `GET /characters` — active Character list
- `GET /characters/{CHAR_ID}` — one Character by stable ID

Each payload contains the Asset identity/revision and full canonical
`CharacterProfile`. `AvatarAppearance` remains nested at
`profile.avatar`; it is not copied into a second editable top-level object.

Archived Characters are omitted from the normal list but remain addressable by
stable ID for continuity and diagnostics.

The Godot contract fixture lives at:

`res://config/runtime/bridge_character_example.json`

and `bridge_character_contract_smoke.gd` verifies that Godot can parse Body,
Species, Surface, Eye, Hair and color fields.


## BRIDGE-03 Character write contract

Godot can update an existing canonical Character with:

- `PUT /characters/{CHAR_ID}`

The request contains:

- `schema_version: "1.0"`
- the `revision` returned by the last read
- `display_name`
- `description`
- full canonical `CharacterProfile`

The Character ID is owned by the URL path and is never accepted from the
request body.

Write safety:

- the existing Character ID is preserved;
- payloads validate through `CharacterProfile`;
- unrelated Asset metadata/files/status are preserved;
- a real mutation advances the Asset revision;
- replaying an identical Save is idempotent even if its original revision is
  now stale;
- a stale revision that would change current state returns HTTP 409 with the
  current revision instead of overwriting newer work;
- this milestone does not create Characters.

`bridge_character_write_smoke.gd` performs a real Godot HTTP PUT in CI and
verifies that the stable Character ID and updated Hair round-trip through the
Bridge transport.

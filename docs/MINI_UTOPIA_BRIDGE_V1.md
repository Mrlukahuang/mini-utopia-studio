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

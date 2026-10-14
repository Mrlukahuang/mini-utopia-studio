# FAMILY-01a — private multi-device Character service (contract + local tests)

This slice provides a **server-side, authenticated Character service** with two
independent child profiles and canonical Character assets. It does NOT deploy
the service and it is NOT a finished family login or playable iPad experience.

## Supported routes

Use the private service base URL. These routes are deliberately **separate**
from the unauthenticated desktop-only `studio.bridge.server`.

| Method | Route | Result |
| --- | --- | --- |
| GET | `/characters` | Only characters owned by the caller's child profile |
| POST | `/characters` | Creates a new canonical `CHAR_...` with an owned, validated `CharacterProfile` |
| GET | `/characters/{CHAR_ID}` | Reads only own character; cross-profile IDs return 404 |
| PUT | `/characters/{CHAR_ID}` | Revision-checked update through existing Character Core contract |
| GET | `/characters/{CHAR_ID}/equipment` | Nine slots and the current child's own inventory / runtime |
| PUT | `/characters/{CHAR_ID}/equipment/{slot}` | Equip or unequip the current child's item, using `{"item_instance_id": "ITEM_..."}` or `null` |
| OPTIONS | any | Strict, origin-scoped Web preflight |

Every non-OPTIONS request requires `Authorization: Bearer <child-token>`.
Tokens must be **independently generated, high-entropy secrets**. The server
configuration stores only their SHA-256 digests. The private API never returns
token values. Do not put tokens, service-role keys, or the child database in Git.

## Local development example only

1. Generate a different 32-byte token for each child locally with
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. Compute each SHA-256 digest locally with
   `python -c "import hashlib,getpass; print(hashlib.sha256(getpass.getpass('Token: ').encode()).hexdigest())"`.
3. Supply `FAMILY_CHILD_A_TOKEN_SHA256`,
   `FAMILY_CHILD_B_TOKEN_SHA256` and
   `FAMILY_ALLOWED_ORIGINS=http://localhost:8080` as environment variables
   to a private runtime, not to CI or exported Godot files.
4. Run `python -m studio.family_api --port 8766`. The application binds to
   loopback and will **refuse** a wildcard binding.
5. Run `python -m pytest -q tests/test_family_api.py`.

For a real Mac/iPad experience, an adult must first provision an HTTPS
endpoint and a private database with backups. TLS must be terminated by
a trusted reverse proxy; configure exact Web origins, access policies,
rate limiting and access logs that do not leak credentials. Never expose
the unauthenticated `studio.bridge.server` on a public interface.

## Security scope

- Profile ownership is stored server-side on the canonical Asset metadata,
  never trusted from a browser JSON request.
- Each child can list, create, read or update only their own CHAR assets.
  Legacy/unowned Character records are *not* imported into child profiles.
- Existing stable Character IDs and `CharacterProfile.avatar` are reused.
- Cross-profile reads and writes return 404, avoiding existence disclosure.
- Invalid tokens and disallowed browser origins fail closed.
- Response bodies are marked `Cache-Control: no-store`; CORS allows only
  explicitly approved origins, not `*` or credentialed cookies.
- No media upload or public sharing in this slice.
- This initial service is for **private testing behind TLS** only. Before
  production/children use, add parent-controlled provisioning and revocation,
  request rate limits, full backup/restore testing, secure HTTPS deployment,
  and short-lived/browser-safe family sign-in. Do not prefill tokens in an
  exported client or keep long-lived bearer tokens in localStorage.

## Follow-up interface

FAMILY-01b: parent-managed account/bootstrap and short-lived scoped credentials
with remote HTTPS deployment. Integrate the Godot Web Bridge client with
authenticated sessions, then FAMILY-02 two-child profile switcher and
end-to-end save/load on Mac and iPad. This infrastructure alone does not
claim live multi-device availability.

## Family equipment owner isolation

Equipment is not copied into a second game database. For each authenticated child,
`EquipmentService` uses a separate canonical CreatorCollection with ID
`COLL_FAMILY_<profile>` and owner_key matching the authenticated profile.
The existing desktop `COLL_DEFAULT` remains available for legacy development,
but **is never exposed by the family API**. Each child's starter item instances
have distinct stable `ITEM_...` IDs. A child cannot list, equip or even infer
the existence of another child's Character or Equipment. Game and Director
renderers should pass the server-supplied `runtime` payload through the shared
CreatorPlayRuntime; clients must not fabricate ownership or stats.

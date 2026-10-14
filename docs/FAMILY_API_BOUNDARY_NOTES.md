# FAMILY-01a — private family API boundary

This module is an **authenticated adapter**, not a hosted service and not a
claim that the Mac/iPad family experience is complete. Source of truth remains
Python Core. The legacy local Bridge is unchanged for desktop development.

## Fail-closed operation

Run `python -m studio.bridge.family_api` only on a **single-family,
dedicated** Python Core database. The service always binds
`127.0.0.1:8767`, never the LAN. Before any browser use, an adult must
provision a private HTTPS reverse proxy with TLS, rate limits, restrictive
firewall rules, and an exact HTTPS Origin allowlist. Do not expose the local
Bridge (`8765`) or the family listener (`8767`) directly.

Server-side environment (never commit actual values):

- `MINI_UTOPIA_FAMILY_ORIGINS`: comma-separated exact HTTPS origins.
- `MINI_UTOPIA_FAMILY_ACCESS_JSON`: JSON object with `principals` array.
  Each entry has `id`, `role` (`adult` or `child`), `token_sha256`, and
  for child roles an explicit `character_ids` list of stable `CHAR_...` IDs.

Generate long random bearer credentials outside the repo and store only their
SHA-256 digests in the server environment. The adult credential must **never**
enter a Godot export. Scoped child credentials are runtime-only credentials,
not embedded in static HTML, project settings, URLs or source. A secure
parent-provisioned login/session flow is still required for production use.

## Route boundary

Authenticated GET `/health`, `/version`, `/characters`,
`/characters/{id}`, `/characters/{id}/equipment`, and PUT
`/characters/{id}` or `/characters/{id}/equipment/{slot}` delegate to the
existing Python Core Bridge. Child listing is filtered to assigned IDs; all
cross-child character and equipment operations are forbidden before touching
the repository. Unknown routes, including unauthenticated Bridge `/session`,
are not exposed. No wildcard CORS, cookies, or public child records.

## Remaining acceptance gates

This is a **single-family** access model, not multi-tenant isolation. FAMILY-02
must persist profile-to-character ownership in canonical storage and implement
safe creation and recovery. FAMILY-01b must implement secure credential
provisioning/rotation and browser runtime auth without bundling secrets.
A parent must separately authorize HTTPS hosting/configuration. Mac/iPad
Safari testing and final physical-device acceptance remain outstanding.

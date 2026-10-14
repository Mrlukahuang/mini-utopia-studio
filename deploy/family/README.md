# Mini Utopia — private Mac + iPad HTTPS hosting package

**Prepared, not deployed.** This directory is a template for an adult-owned,
private domain/host. Do not publish the static Godot build on GitHub Pages and
do not use the public repository to store a child's creations or database.

## Architecture

```text
Mac/iPad Safari
  https://FAMILY_DOMAIN/
    ├── Godot Web (built privately by GitHub Actions; mounted read-only)
    └── HTTPS API /characters*, /family/sessions*
          Caddy TLS → 127.0.0.1:8766 (Docker shared network namespace)
                           ↓
              studio.family_api (no Streamlit, no AI providers)
                           ↓
              persistent named volume family_data/studio.db
```

Python binds **only** `127.0.0.1:8766` even inside its container. Caddy
shares that namespace and is the only service accepting public HTTPS. The
child receives a 30-minute per-profile token after the parent enters their
private unlock secret; only its digest is held on the server. The Godot Web
library detects its own HTTPS origin so the parent doesn't need to type the
API address. This is private-by-default hosting, *not* public multiplayer or
public content sharing.

## Adult-only configuration required before any real child uses it

1. Own/control a private HTTPS domain and Docker host, and point domain DNS
   to that host. HTTPS automatic certificate issuance requires the host to
   be reachable on ports 80 and 443.
2. Download the GitHub Actions **Godot Web Build** artifact (no user content)
   from a reviewed `main` commit and unpack its `index.html`, `index.js`,
   `index.wasm`, `index.pck` and associated files to
   `deploy/family/web/` **on the private host**. Do not commit that folder.
3. Copy `.env.example` to `.env` locally and replace the example domain.
   Generate **three separate 32-byte or longer random secrets** on the
   private host, one parent unlock, two legacy server-only child secrets:
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
   Hash each using `hashlib.sha256`, and put **only hex SHA-256 digests**
   into the three environment keys. Keep raw parent unlock secret in a
   secure password manager, never in Git/PR/CI or the exported Web app.
   The legacy child raw secrets must **never** be distributed to browsers.
   Restrict .env file permissions, e.g. `chmod 600 .env`.
4. Run `docker compose --env-file .env -f compose.yaml config --quiet`
   then `docker compose --env-file .env -f compose.yaml up -d --build`.
   TLS certificates are managed by Caddy; the Python API stores its SQLite
   data on the separate persistent `family_data` volume.
5. Visit `https://FAMILY_DOMAIN/` on Mac Safari and iPad Safari. The parent
   selects Child A/B, enters their parent unlock **once**, and receives the
   short-lived child session. Children's names, equipment, or films never
   enter the repository or GitHub Actions.

## Data recovery and backup

SQLite is in a named Docker volume, not in the Web artifact. To take a
consistent transactional snapshot while the API continues running, use:

```bash
umask 077
mkdir -p private-backups
docker compose --env-file .env -f compose.yaml exec -T api \
  python -m studio.family_backup /data/studio.db \
  > "private-backups/family-$(date +%Y%m%d-%H%M%S).sqlite"
```

Immediately move backups to encrypted, **off-host** adult-controlled storage.
Test restoration in an isolated disposable instance before any live migration.
Do not restore over the live DB without explicit adult approval. Backups are
plain SQLite unless encrypted by your secure backup system; never upload
them into GitHub artifacts, bug reports or chats.

## Technical limitations and safety gates

- One Python process holds short-lived child tokens in RAM. Restart revokes
  them all; run one process and one instance until shared session persistence
  and load balancing are explicitly designed.
- Rate-limiting on parent unlock is per server instance; place additional
  edge/network abuse limits on the private host.
- No credentials are checked into the Docker image or static Web bundle.
  Production secrets need adult provisioning and rotation policies.
- Production should include automatic off-host encrypted backups, recovery
  drill, dependency patching and server monitoring before regular use.
- No authenticated film download service or in-browser MP4 renderer has yet
  been deployed. Do not expose a writable upload directory via Caddy.
- This package doesn't create cloud accounts, DNS, firewall rules, or spend
  money. An adult must approve and complete that setup when requested.
- Final acceptance requires a real Mac/iPad test for save, outfits, play,
  film previews, performance, session expiry and backup/restore.

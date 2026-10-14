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
- An authenticated private MP4 download service is included but **not deployed**.
  A parent must separately approve rendering and release the exact encoded MP4.
  Do not expose the media directory via Caddy static files.
- This package doesn't create cloud accounts, DNS, firewall rules, or spend
  money. An adult must approve and complete that setup when requested.
- Final acceptance requires a real Mac/iPad test for save, outfits, play,
  film previews, performance, session expiry and backup/restore.


## Adult-run private MP4 rendering (offline first)

This is a **local/private-host command**, not a child-exposed HTTP endpoint
and not a GitHub Actions task. The host needs a checked-out trusted Godot
project, Godot 4.7.2, FFmpeg/FFprobe, `xvfb-run`, and read-only access to
its private SQLite database. The saved FILM ID comes from the child's
private `/family/films` list; all actors, equipment and handmade props are
loaded again from SQLite with the named child's owner scope.

An adult creates a private, non-world-readable output directory **outside
the repository** and starts the worker:

```bash
install -d -m 700 /srv/mini-utopia-private-movies
python -m studio.family_private_movie_worker \
  --db /srv/mini-utopia-private-data/studio.db \
  --godot-project ./godot \
  --owner child_a \
  --film-id FILM_REPLACE_WITH_OWNED_ID \
  --output /srv/mini-utopia-private-movies/episode-001.mp4 \
  --fps 6
```

The worker makes a restricted 0700 temporary copy of the Godot project,
**outside Git**, writes the minimum canonical render contract there,
imports assets, prepares the staged scene, captures the frames via virtual
display, runs FFmpeg to encode MP4, verifies the frame count and actual
duration, then writes the output file with mode 0600. Temporary copies,
character snapshots and PNG frames are removed on both success and failure.
The worker refuses to overwrite existing videos or write inside the public
Git repository, and its command-line entry refuses public GitHub Actions
execution. It has no access to paid video generation providers.

Only a trusted adult-operated process with access to the family DB may run
this command. It is **not** an in-browser MP4 button yet. Before making it
available to children, implement an adult-reviewed job queue, independent
render worker resource limits, owner-scoped private MP4 download, cleanup/
retention controls and real iPad Safari review. The public repository must
never contain a rendered household MP4, child audio or private film JSON.


## Private reviewed MP4 media store (adult-only configuration)

The Compose package now mounts `deploy/family/private-movies/` **read-only**
inside the API as `/movies`. This path is excluded from Git. Before any
real hosting, create it securely as the API runtime UID/GID 10001:

```bash
sudo install -d -m 700 -o 10001 -g 10001 deploy/family/private-movies
```

A trusted adult's private host requires a reviewed Godot 4.7.2 checkout,
Godot, FFmpeg/FFprobe/Xvfb and access to a current, protected SQLite state.
The offline movie worker may run as UID 10001 with
`--store-root /ABSOLUTE/HOST/PATH/deploy/family/private-movies` (instead of
`--output`). It creates 0700 owner/film folders and a fingerprint-named
0600 MP4. It MUST NOT send real child render payloads or videos to GitHub.

After the parent reviews the **actual locally rendered MP4**, they POST a
separate authenticated `/family/movie-releases` decision for the child,
FILM ID and revision, with `decision: "release"`. The private API verifies
the prior FILM approval and current actor/outfit fingerprint, hashes the
encoded MP4 and stores the release receipt only in SQLite. Child A can
retrieve ONLY Child A's media at `GET /family/films/{id}/download` with its
short-lived Authorization bearer. Access is denied after parent revocation,
film or wardrobe changes, changes to the MP4 bytes or lost owner access.
No public static files, signed URL in browser history or shared media are
created. The iPad Download button and live-host acceptance still require
real-device testing; this package remains prepared, not deployed.


## Verified synthetic end-to-end movie release regression

The GitHub test workflow runs a **synthetic-only** end-to-end acceptance
check using a temporary SQLite database and real Godot/Xvfb/FFmpeg:
create a Hero and a handcrafted prop, save a film, adult approve its exact
revision, render an isolated MP4 in a 0700 private folder, then confirm it
remains unavailable to the child until the adult separately releases the
finished file. It verifies the owner can download byte-identical MP4 data,
a sibling cannot, and revocation immediately denies further downloads.
Temporary synthetic footage is deleted and is never attached to GitHub.

The real private worker also reopens current canonical records and checks
parent approval **after encoding and before writing the finished MP4**:
a parent revocation, film edit or appearance/equipment change during the
lengthy render aborts publication. Output larger than the private download
limit (32 MiB) is rejected. Tests simulate both race conditions without
real family data. This does not replace private host deployment or adult
review of the actual finished household video.

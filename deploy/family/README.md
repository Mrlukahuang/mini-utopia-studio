# Mini Utopia — LAN-only HTTPS on adult-owned MacBook (A-006)

**Prepared, not deployed.** Home Wi-Fi only, no purchased domain, no router
port forwarding, no internet-facing ports or real child materials in Git/CI.

## Architecture

```text
Mac/iPad Safari --trusted HTTPS--> MacBook's private IPv4:443/tcp
    -> Docker port published only on FAMILY_LAN_IP
    -> Caddy "tls internal" (persistent private CA in caddy_data)
       ├── Godot Web artifact in ./web (read-only)
       └── family API -> 127.0.0.1:8766 -> SQLite family_data
```

## First real Mac + iPad deployment (adult-operated)

1. Keep the Mac plugged in, awake and lid open. Set one fixed RFC1918 Wi-Fi
   IPv4 (example 192.168.1.50) and confirm it does not overlap another DHCP
   lease. Connect iPad and Mac to the same home Wi-Fi, not an isolated guest LAN.
2. Install Docker Desktop for Apple Silicon, start the engine and clone the
   reviewed repository. Download a successful **Godot Web Build** artifact from
   GitHub Actions and extract index.html/index.js/index.wasm/index.pck into
   deploy/family/web/ on the Mac. Never commit web/ or real assets.
3. Copy .env.example to .env, set FAMILY_LAN_IP to the actual Mac Wi-Fi IP.
   Generate three separate 32-byte+ secrets on the Mac and write **only their
   SHA-256 hex digests** to .env (mode 0600). Store the original parent unlock
   in a LOCAL password manager. Legacy child raw secrets are server-only.
4. Create private-movies/ (mode 0700) locally, run read-only
   `python3 -m studio.family_deploy_preflight --deploy-dir deploy/family`,
   and verify `local_preflight_passed=true`. Confirm Compose contains only
   private-IP host binding with
   `docker compose --env-file deploy/family/.env -f deploy/family/compose.yaml config`.
5. Start containers with
   `docker compose --env-file deploy/family/.env -f deploy/family/compose.yaml up -d --build`.
   No public DNS or host port 80 mapping. Persist named volumes caddy_data and
   family_data; never delete them during routine updates.
6. Export **only** the Caddy public root cert using
   `docker compose --env-file deploy/family/.env -f deploy/family/compose.yaml cp web:/data/caddy/pki/authorities/local/root.crt ./mini-utopia-root.crt`.
   Install this public CA into each privately managed iPad and Mac trust store;
   on iPad enable full trust under Settings > General > About > Certificate
   Trust Settings. Never extract, copy or share root.key.
7. Visit `https://MAC_PRIVATE_IP/` on Mac + iPad Safari. Verify no TLS
   warning and separate Child A/B login. `window.isSecureContext` must be
   true for future W2 microphone APIs (W2 recording is not implemented yet).
   CI does not replace live Mac/iPad acceptance.

The MacBook lid should remain **open** when hosting; "prevent automatic sleep
with display off" does not override normal lid-closing sleep. The current
Compose starts Web/API only; production MP4 rendering with Linux/Xvfb on
Apple Silicon has not been validated by physical device testing.

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


## Adult-only private movie render queue

A new SQLite queue provides a single private, adult-operated renderer.
Only an already-approved film revision may be enqueued, and it checks
the parent's current approval and the saved character/wardrobe fingerprint
before claiming work and before marking completion.

\`\`\`bash
python -m studio.family_render_queue --db /PRIVATE/family.db --fps 6 enqueue --owner child_a --film-id FILM_APPROVED_ID
python -m studio.family_render_queue --db /PRIVATE/family.db --store-root /PRIVATE/movies --godot-project ./godot run-one
python -m studio.family_render_queue --db /PRIVATE/family.db list
\`\`\`

At most one active render runs across processes, with two outstanding per
child, four globally, eight new jobs per child per day, two attempts per
job, a 32 MiB MP4 limit and a minimum of 128 MiB free space.

A crashed job remains in the running state to block automatic duplicate
renders. An adult must ensure the original worker is stopped, explicitly
mark it interrupted-failed and choose to retry. A completed render does
not permit downloads: the parent must separately inspect and release
the final private MP4. There is no public HTTP queue or unattended cloud
scheduler, and real children's media never goes to GitHub CI.


## Restore integrity audit before real family hosting

The adult-only check below takes an ONLINE, transactionally consistent copy
of the private SQLite database into a chmod-700 temporary directory outside
the repository. It opens that restored copy, performs SQLite integrity and
foreign-key checks, reopens canonical Core FILM assets, and verifies current
parent-released MP4 permissions and hashes when a private media directory is
supplied. It prints only aggregate counts, never children's notes or files:

\`\`\`bash
python -m studio.family_backup_audit \
  --db /srv/mini-utopia-private-data/studio.db \
  --media-root /srv/mini-utopia-private-movies
\`\`\`

This command is read-only on the original database and does **not** create
a retained backup. Temporary plaintext snapshots are removed at exit;
there is no guarantee of physical secure erasure on SSDs. Before production,
adults still need scheduled encrypted off-host backups and a separate
approved restore rehearsal on an isolated host. Do not restore over a live
SQLite DB or export a copy into Git, CI artifacts or a shared folder.


## Local pre-deployment safety check (no network or accounts created)

After an adult has configured the private host, but **before** starting any
containers, run the following from the trusted repository directory:

\`\`\`bash
python -m studio.family_deploy_preflight --deploy-dir deploy/family
\`\`\`

The check is read-only. It validates that a private \`.env\` exists with
restrictive permissions, a configured RFC1918 LAN IPv4 is present,
three separate SHA-256 credential digests are present, the Godot Web export
contains \`index.html\`, \`index.js\`, \`index.wasm\`, and \`index.pck\`,
and the MP4 storage root is protected against other users and symlinks.
The Docker/Caddy package files must also exist.

Output is structured JSON containing **only check names and error codes**.
It deliberately never prints the LAN IP, any digest, secret, movie details,
or contents of the Web export. A failing check returns exit status 1.
Running the preflight does not create a cloud account, open firewall ports,
deploy a container or upload family material.

**Important:** passing this offline check does **not** prove that Caddy internal-CA issuance and trust, a real child's session, Safari/WebGL,
Mac/iPad touch controls, or private MP4 saving actually work. Those require
a separately authorized adult host and a real-device acceptance test.

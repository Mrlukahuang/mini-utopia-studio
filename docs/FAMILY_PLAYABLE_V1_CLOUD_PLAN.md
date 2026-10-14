# Mini Utopia — Family Playable v1 / GitHub-first development plan

Status: **execution plan**, not a claim that the iPad build is playable.
Owner: Mini Utopia product. Repo: `Mrlukahuang/mini-utopia-studio`.

## Product acceptance (one complete child loop)

On a Mac (developer review) and on a real iPad (child touch experience):

1. Each child can create a separate persistent character.
2. The character can change species/body/colors, wear a compatible outfit, and equip a simple prop.
3. The same saved character can enter a small playable village with touch movement, jump and interaction.
4. Both saved characters can appear in a Director scene using the same 3D assets, outfit and props.
5. A child can stage a 15–30 second story with preset animations, camera choices and dialogue/voice.
6. An adult can export an MP4; assets and character identity survive restart.
7. The UX exposes **no code, developer editor, localhost URL, Bridge diagnostics, or technical prompts** to children.

Do not call v1 complete until the full loop passes real Mac and iPad visual acceptance.
Automated CI/headless tests are necessary but cannot substitute for that last check.

## Cloud workflow / source of truth

- **GitHub is the sole source code repository.** Use Issue -> branch -> code/test -> PR -> green CI -> merge.
- **Godot 4.7.2** is still the engine and runtime, not a required local editing step.
- **GitHub Actions** parses/tests the Godot project and exports a Web build as a *private Actions artifact*. New work should be testable remotely without installing Godot locally.
- **Godot owns child UI and realtime rendering.** Streamlit is parent/producer VIEW ONLY.
- **Python Core owns canonical Creator metadata**, via an authenticated service when operating across devices. Do not create independent "truth" in Godot, user:// or Streamlit.
- **All user content is private by default.** Do not publish children's names, voices, media or data to public GitHub repo, public build artifacts, or a public static site. Never add credentials or provider API keys to the client.
- Prefer free/deterministic local art and animations before paid model calls. No unapproved spending.

## What this first infrastructure PR achieves

- Adds `godot/export_presets.cfg` with **Web / single-threaded / Compatibility** export settings; works toward iPad Safari compatibility.
- Adds `.github/workflows/godot-web-artifact.yml` for headless GitHub-built browser exports.
- Uploads artifacts for manual distribution after successful CI.
- No GitHub Pages deployment, child-facing claim, cloud-data change, credentials or production launch.
- Existing `.github/workflows/tests.yml` continues to validate Godot scenes, scripts, Python and video capture.

## Important platform constraints

1. Current Bridge listens on `127.0.0.1:8765`. That address is **not accessible from a child's iPad** and is not suitable as a cloud API.
2. A static Web build cannot run the Python Core or SQLite server in a browser. For family persistence across Mac/iPad, introduce an authenticated HTTPS backend with explicit parental access controls, CORS restrictions, backup/recovery, rate limits and versioned asset contracts.
3. Build artifacts only prove exportability; they do not prove touch/UI, browser WebGL, performance, Web memory use, media capture, or API integration. Test real iPad Safari.
4. Do not silently switch to per-device `user://` as permanent canonical storage. If offline guest mode is added, label it temporary/draft and implement deliberate server sync with conflict handling.
5. Avoid GDExtension-dependent runtime code in the first Web export. Use the Compatibility renderer and non-threaded Web templates.
6. A production native iOS app later needs a macOS/Xcode runner, Apple identity/provisioning and code-signing secrets. Do not start TestFlight until browser UX is validated.

## Delivery slices (PR-sized, independently verifiable)

| ID | Work | Proof / acceptance |
|----|------|--------------------|
| CLOUD-01 | GitHub Web export artifact (this PR) | Exported index.html, wasm, pck and JS are nonempty in CI |
| CLOUD-02 | Browser boot & touch compatibility hardening | Standalone Web scene starts in Safari; drag/tap/zoom controls work, no Godot editor needed |
| FAMILY-01 | Parent-managed HTTPS profile/character service design and contract tests | Authenticated test client reads/writes stable Character IDs; no localhost assumptions |
| FAMILY-02 | Separate child profiles with stable assets | Two child profiles stay separate after restart and across devices |
| CREATOR-01 | Child-facing Creator and outfit/item loop | Create/save/reload/change outfit and simple assembled prop |
| PLAY-01 | One village, selectable saved character, on-screen movement | Same character enters world, interacts, exits without loss |
| DIRECTOR-01 | Two-character staging + simple shot/action timeline | Same assets animate in staged story |
| MOVIE-01 | Adult-approved MP4 rendering/export path | Reproducible 15–30s clip with sound; no private media exposed in CI |
| FAMILY-03 | Integration, backups, security + real-device UX fixes | Tests green; Mac/iPad real-device acceptance; no private data exposed |

### Deliberate scope cuts for v1

No public uploads/sharing, multiplayer, open-ended AI 3D rigs, App Store releases, MMORPG world, or elaborate combat system. No requirement to modify local Godot for each PR.

### Blockers that require an adult

- Choosing/provisioning a private HTTPS host and secure account/secrets for cross-device persistence.
- Apple Developer credentials only if we move to native iOS/TestFlight.
- Final product acceptance from the two children on a physical iPad.

Everything else should go through the normal PR + CI workflow. No destructive data migration or secret-exposing public deployment without approval.

## Documentation / references

- `docs/MINI_UTOPIA_CREATOR_ARCHITECTURE_V1.md` (product boundary)
- `godot/README.md` (current Godot runtime assets/scenes)
- https://docs.godotengine.org/en/4.7/tutorials/export/exporting_projects.html
- https://docs.godotengine.org/en/4.7/tutorials/export/exporting_for_web.html
- https://docs.godotengine.org/en/4.7/tutorials/export/exporting_for_ios.html

# Mini Utopia · AI Creative Studio

> **Travel Around Every World.**  
> A Python-driven, AI-assisted, human-reviewed creative studio for building reusable characters, places, stories, and short-form video worlds.

---

## 1. Project Overview

**Mini Utopia** is the first content universe built on top of a more general system called **AI Creative Studio**.

The long-term goal is not simply to make a Xiaohongshu account, and not simply to teach a child how to use AI. The goal is to build a creative environment where imagination can be turned into reusable assets, stories, and eventually finished media.

The project is designed around three participants:

- **The child / creator** — imagines, chooses, names, reacts, edits, approves.
- **The adult / producer** — maintains the system, controls cost, permissions, safety, publishing and technical quality.
- **AI** — structures fuzzy ideas, proposes options, generates assets, performs repetitive production work and checks continuity.

The core principle is:

> **Let the creator think wildly without letting the production become chaotic.  
> Let the system carry the complexity, not the creator.**

---

## 2. What This Repository Is

This repository is the codebase for **AI Creative Studio**.

Mini Utopia is only the **first Universe** running inside the studio.

```text
AI Creative Studio
│
├── Universe: Mini Utopia
│
├── Universe: Future Project 02
│
├── Universe: Future Project 03
│
└── Playground
```

This distinction is important.

The software must remain reusable even if Mini Utopia changes direction, pauses, or is replaced by an entirely different creative series.

---

## 3. Creative Vision: Mini Utopia

### 3.1 Core Concept

Mini Utopia is a parallel universe made of countless **Mini Worlds**.

A recurring **Traveler** moves between worlds through a **Portal**.

These worlds may be:

- real places,
- fantasy places,
- historical settings,
- future cities,
- alien planets,
- surreal environments,
- or completely original worlds created by the child.

The idea is broader than “travel around the world”.

The creative promise is:

> **Travel Around Every World.**

---

## 4. Mini Utopia Canon

The official Mini Utopia series keeps a small number of stable anchors.

Everything else is allowed to change.

### 4.1 Visual DNA

Default visual direction:

**Miniature + Voxel / Block + Toy-like + Cinematic**

The visual style should feel like a charming miniature universe while remaining original.

The project should **not** depend on copied Minecraft characters, logos, textures, branded assets, or other directly recognizable protected design elements.

The goal is to create our own block / voxel miniature language.

### 4.1.1 Brand Canon, UI Shell & Typography

Mini Utopia also has a locked **Brand Canon** so the product UI and generated assets feel like one coherent creative game rather than unrelated screens.

**Logo system**
- Primary horizontal logo: main page header, Home, Character Factory, future Mini World Factory, Stories, covers and presentation headers.
- Square badge logo: top of the Streamlit sidebar, compact cards, app/avatar contexts, future image corner marks and future video watermark.
- Official logos are application assets. Image-generation models must not invent or redraw the logo.

**Typography Canon**
- Display / headings (English): **Fredoka**
- Display / headings (Chinese): **ZCOOL KuaiLe**
- Body / UI (English): **Nunito**
- Body / UI (Chinese): **Noto Sans SC**
- Unrelated decorative fonts should not be introduced into Canon UI.

**UI Shell Canon**
- Sidebar starts with the square badge logo and compact tagline.
- Main content starts with the primary horizontal logo.
- Soft cream / lavender / sky gradients, rounded navigation rows, consistent rounded cards, pill-like controls and gentle shadows.
- Core UI colors stay within the Mini Utopia macaron family: Strawberry Pink, Mint, Lavender, Sky Blue, Peach, Cream and Ink.
- Brand styling should stay playful, block-built, collectible and child-friendly without becoming visually cluttered.

The detailed source of truth is:

**[Mini Utopia Brand Canon v1.0](docs/MINI_UTOPIA_BRAND_CANON_V1.md)**

Changes to the Logo system, Typography Canon, or core UI shell require an explicit Brand Canon version bump.

---

### 4.2 The Traveler

The first recurring Traveler should be created collaboratively in the studio.

The Traveler becomes a long-term reusable `Character Asset`.

Later the universe may introduce:

- companions,
- rivals,
- recurring side characters,
- creatures,
- world-specific characters,
- callback characters from earlier episodes.

The Traveler acts as the audience anchor even when the world changes completely.

---

### 4.3 Story Formula

The initial story rhythm is:

```text
ARRIVE
  ↓
DISCOVER
  ↓
PROBLEM
  ↓
ADVENTURE
  ↓
SURPRISE
  ↓
PORTAL / NEXT WORLD
```

This is a starting framework, not a rigid rule.

The purpose is to stop episodes from becoming simple scenery showcases.

---

### 4.4 The Portal

The Portal is the universal narrative device connecting all Mini Worlds.

It can be used as:

- an episode opening,
- a transition,
- a mystery,
- a recurring object,
- a cliffhanger,
- a long-term lore device.

It also explains why radically different worlds can coexist naturally inside one series.

---

## 5. Canon Mode vs Playground Mode

The studio intentionally supports two creative spaces.

### Canon Mode

Used for official Mini Utopia production.

Canon Mode automatically loads:

- Universe rules,
- visual DNA,
- recurring Traveler,
- Portal logic,
- story formula,
- continuity,
- existing lore.

Output may proceed into official Episode / Production workflows.

### Playground Mode

Used for experimentation.

```text
No rules.
No canon.
Just create.
```

The creator can mix any:

- character,
- species,
- location,
- style,
- object,
- world,
- visual language,
- story idea.

Playground content does **not** automatically affect Mini Utopia Canon.

A successful experiment may later be promoted into an official Universe asset.

---

## 6. The Core Architecture Principle

### Assets do not belong to Stories

This is the most important rule in the system.

A Character is not created “inside an episode”.

A Location is not owned by a Story.

A Style is not owned by a Universe.

They are reusable assets.

```text
ASSET LIBRARY

Characters
Locations
Props
Vehicles
Styles
Voices
Music
Worlds
```

A Story simply references existing assets.

Example:

```text
CHAR_PANDA
+
LOC_CANDY_MOON
+
PROP_TALKING_FRIDGE
+
STYLE_MINI_VOXEL
+
Premise
=
STORY_0012
```

The same panda may appear tomorrow in Auckland, next week underwater, and later on Mars without rebuilding the character.

---

## 7. Domain Model

The system is based on the following main objects.

### Asset

A reusable creative object with a permanent machine ID.

Examples:

```text
CHAR_<ULID>
LOC_<ULID>
PROP_<ULID>
VEH_<ULID>
STYLE_<ULID>
VOICE_<ULID>
MUSIC_<ULID>
```

Common fields include:

```text
asset_id
asset_type
display_name
slug
description
tags
version
status
created_at
updated_at
metadata
files
source_job_id
```

`asset_id` never changes.

The display name may change freely.

---

### Universe

A content series with its own Canon.

Example:

```text
UNIV_MINI_UTOPIA
```

A Universe contains or references:

- Canon rules,
- default styles,
- recurring characters,
- recurring objects,
- lore,
- continuity rules,
- story conventions.

A Universe organizes assets.

It does not permanently own them.

---

### Story

A narrative idea.

A Story stores references to Asset IDs rather than duplicating those assets.

A World / Universe association is optional.

This allows both Canon stories and totally free Playground stories.

---

### Episode

A production instance derived from a Story.

An Episode may contain:

```text
Story
Script
Scenes
Shots
Storyboard
Video
Audio
Subtitles
Final Output
```

---

### Recipe

A reusable workflow.

Examples:

```text
Create Character
Create Location
Create Story
Create Storyboard
Make Short Video
```

Recipes define **how capabilities are chained together**.

---

### Job

A single execution task.

Examples:

```text
character.parse
character.turnaround
story.generate
video.generate
```

A Job should record:

```text
job_id
capability
provider
input_asset_ids
parameters
status
attempt
created_at
started_at
finished_at
output_asset_ids
error
estimated_cost
actual_cost
```

---

### Plugin

A replaceable implementation of a capability.

Examples:

```text
character.parse
character.master_image
character.turnaround
character.expressions
location.generate
story.generate
script.generate
storyboard.generate
video.generate
audio.generate
edit.compose
```

Providers and models can change without changing the rest of the studio.

---

## 8. Character Factory

Character Factory is the first major creator-facing workflow.

The child should not be required to write technical prompts.

The experience should begin with natural language.

Example:

> “I want a chubby panda with a yellow hat and blue overalls. He is scared easily but really loves adventures.”

The workflow:

```text
Free description
      ↓
AI Parse
      ↓
Editable Character Profile
      ↓
Human Review
      ↓
Master Character Generation
      ↓
Human Confirm
      ↓
Character Lock
      ↓
Turnaround Generation
      ↓
Expressions / Poses / Outfits
      ↓
Character Asset Library
```

### Character Profile dimensions may include

- name,
- species,
- age / perceived age,
- body type,
- height,
- proportions,
- face,
- eyes,
- hair / fur,
- clothing,
- accessories,
- color palette,
- personality,
- strengths,
- weaknesses,
- habits,
- abilities,
- fears,
- immutable visual traits.

---

## 9. Character Reference Pack

After a Character Master is approved, the Character becomes reusable.

Example structure:

```text
CHAR_xxx/
│
├── manifest.json
│
├── references/
│   └── master.png
│
├── turnaround/
│   ├── front.png
│   ├── side.png
│   └── back.png
│
├── expressions/
│   ├── happy.png
│   ├── sad.png
│   ├── angry.png
│   └── surprised.png
│
├── poses/
│   ├── standing.png
│   ├── sitting.png
│   └── walking.png
│
└── outfits/
    └── default/
```

The approved Master Reference is the consistency anchor for future generation.

---

## 10. Location / Object / Style Factories

Character Factory establishes a reusable interaction pattern.

Other asset factories should follow the same logic:

```text
Free description
      ↓
AI parses dimensions
      ↓
Creator edits dimensions
      ↓
Reference generation
      ↓
Human approval
      ↓
Permanent Asset
```

This pattern should be shared by:

- Locations,
- Props,
- Vehicles,
- Styles,
- later World / Environment assets.

This keeps the UI familiar for the child and reduces technical duplication.

---

## 11. Human-in-the-loop

This project is deliberately **semi-automated**.

AI should generate.

Humans should approve the important creative decisions.

Typical state flow:

```text
DRAFT
  ↓
GENERATED
  ↓
NEEDS_REVIEW
  ↓
APPROVED
  ↓
NEXT_STAGE
```

Failure path:

```text
FAILED
  ↓
RETRY
or
MANUAL_FIX
```

Important approval gates:

1. Character Master
2. Story
3. Script
4. Storyboard
5. Final Video

The system should avoid rebuilding an entire episode because one shot failed.

---

## 12. Creator Mode vs Studio Mode

### Creator Mode

Designed for the child / creator.

Should expose:

- My Creations,
- Characters,
- Places,
- Objects,
- Styles,
- Stories,
- Movies,
- large visual cards,
- simple natural-language inputs,
- editable creative dimensions,
- clear Approve / Try Again controls.

Should **not** expose:

- API keys,
- raw JSON,
- tokens,
- model routing,
- database internals,
- stack traces,
- detailed cost logs.

---

### Studio Mode

Designed for the adult / producer / developer.

May expose:

- provider,
- model version,
- system prompt,
- raw structured output,
- Job Queue,
- errors,
- retries,
- duration,
- cost,
- Asset Inspector,
- Canon configuration,
- database state,
- debugging information.

---

## 13. Technical Architecture

The current architecture target is:

```text
Creator UI
     ↓
Creative Engine
     ↓
┌─────────────────────────────────┐
│ Asset Library                   │
│ Universe / Canon                │
│ Stories                         │
│ Recipes                         │
└─────────────────────────────────┘
     ↓
Job Engine
     ↓
Plugin Registry
     ↓
Providers
     ↓
OpenAI / Gemini / Image / Video / Voice / FFmpeg
```

---

## 14. Replaceable Layers

The project must keep four infrastructure concerns replaceable.

### Repository

**Question:** Where is structured data stored?

Current:

```text
SQLite
```

Future possibilities:

```text
PostgreSQL
Supabase
Other database
```

---

### Storage

**Question:** Where are images, video and large media files stored?

Current:

```text
Local filesystem
```

Future:

```text
Cloud object storage
```

---

### Provider

**Question:** Which external AI service is used?

Examples:

```text
OpenAI
Gemini
Future providers
```

Providers must not leak into core business logic.

---

### Plugin

**Question:** What capability is being performed?

Examples:

```text
character.parse
character.turnaround
story.generate
video.generate
```

A capability may later be implemented by a different model without changing the Studio.

---

## 15. Recommended V0.x Stack

Current foundation:

- Python 3.12
- Streamlit
- Pydantic
- SQLite
- pytest
- GitHub
- GitHub Actions

Planned integrations:

- OpenAI
- Gemini
- image generation providers
- video generation providers
- TTS
- FFmpeg
- cloud storage
- PostgreSQL / Supabase when remote persistence becomes necessary

We are intentionally **not** introducing complex agent frameworks yet.

No LangChain / CrewAI / AutoGen unless orchestration complexity later justifies them.

---

## 16. Repository Structure

Current target structure:

```text
mini-utopia-studio/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── .streamlit/
│   └── config.toml
│
├── studio/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── ids.py
│   │   └── enums.py
│   │
│   ├── models/
│   │   ├── asset.py
│   │   ├── character.py
│   │   ├── location.py
│   │   ├── prop.py
│   │   ├── style.py
│   │   ├── universe.py
│   │   ├── story.py
│   │   ├── episode.py
│   │   └── job.py
│   │
│   ├── repositories/
│   │   ├── base.py
│   │   └── sqlite.py
│   │
│   ├── storage/
│   │   ├── base.py
│   │   └── local.py
│   │
│   ├── providers/
│   │   ├── base.py
│   │   ├── openai.py
│   │   └── gemini.py
│   │
│   ├── plugins/
│   │   ├── base.py
│   │   ├── registry.py
│   │   └── mock/
│   │
│   ├── recipes/
│   │   ├── character_factory.py
│   │   └── story_builder.py
│   │
│   ├── services/
│   │   ├── asset_service.py
│   │   ├── universe_service.py
│   │   ├── story_service.py
│   │   └── job_service.py
│   │
│   └── ui/
│       ├── creator/
│       ├── studio/
│       └── components/
│
├── prompts/
│   ├── character/
│   ├── story/
│   └── director/
│
├── data/
│   ├── assets/
│   ├── universes/
│   ├── stories/
│   ├── episodes/
│   └── jobs/
│
└── tests/
```

---

## 17. Data Boundary

The intended boundary is:

### Database

Stores:

- indexes,
- relationships,
- current state,
- IDs,
- statuses,
- metadata.

### Filesystem / Object Storage

Stores:

- images,
- character references,
- storyboards,
- video clips,
- audio,
- final media.

### JSON Snapshots

Preserve:

- generated structured output,
- portable asset manifests,
- debugging snapshots,
- versionable intermediate results.

---

## 18. Development Order

The development roadmap is intentionally staged.

### A. Foundation

Must include:

- config,
- SQLite,
- Pydantic,
- permanent IDs,
- Asset base model,
- Repository interface.

**Acceptance test:** assets survive app restart and can be created / read / updated.

---

### B. Asset Library

Must include:

- Characters,
- Locations,
- Props,
- Styles,
- detail views,
- tags / favourites.

**Acceptance test:** Creator Mode can find and reuse existing assets by permanent ID.

---

### C. Character Factory

Must include:

- free description,
- `character.parse`,
- editable dimensions,
- Master Reference interface,
- Turnaround interface.

**Acceptance test:** even with Mock providers, a complete flow can produce a permanent `CHAR_ID` and Reference Pack.

---

### D. Universe

Must include Mini Utopia Canon:

- visual DNA,
- Traveler,
- Portal,
- Story Formula,
- default Style,
- continuity rules.

**Acceptance test:** Canon stories load Universe defaults while Playground remains unrestricted.

---

### E. Story Builder

Must include:

- Asset selection,
- premise,
- Story JSON,
- review state.

**Acceptance test:** the same Character can be referenced by multiple unrelated Stories without duplication.

---

### F. Script / Director

Must include:

- Script schema,
- Scene schema,
- Shot schema,
- human review.

**Acceptance test:** an approved Story can reliably become a structured Shot List.

---

### G. Real AI

Must include:

- OpenAI Provider,
- Gemini Provider,
- structured output,
- validation,
- retry logic.

**Acceptance test:** switching Provider does not require rewriting Asset or Story business logic.

---

### H. Media

Later:

- image generation,
- storyboard generation,
- video generation,
- voice,
- music / SFX,
- FFmpeg composition.

**Acceptance test:** production works at Shot level, allowing failed shots to regenerate without rebuilding the whole episode.

---

## 19. V1 Definition of Done

V1 is complete when:

- [ ] Creator Mode can create an original Traveler.
- [ ] The Traveler is saved as a permanent Character Asset.
- [ ] One Character can be reused in multiple completely different Stories.
- [ ] Mini Utopia Canon exists.
- [ ] Playground works without Canon restrictions.
- [ ] A Story can reference Character / Location / Prop / Style assets.
- [ ] Story review exists.
- [ ] Approved Stories can become structured Scripts and Shot Lists.
- [ ] Character Turnaround exists as a standard Plugin capability.
- [ ] Changing a Provider does not change the Character ID or asset structure.
- [ ] Every external generation action has a Job record.
- [ ] Failed Jobs can retry safely.
- [ ] Creator Mode hides technical internals.
- [ ] Studio Mode exposes enough information for debugging.
- [ ] The Studio still works even if video generation is not yet connected.

---

## 20. Short-Term Goals — 0 to 4 Weeks

Primary objective:

> **Make creation actually happen.**

Deliverables:

- Studio foundation,
- Asset Protocol,
- Asset Library,
- Universe,
- Playground,
- Job / Plugin interfaces,
- first original Traveler,
- at least 2 Locations,
- at least 1 Prop,
- at least 1 official Story,
- Idea / Story → Review → Script → Shot List,
- Mini Utopia Canon v1.

Short-term success is **not** measured mainly by followers or revenue.

The important questions are:

- Does the creator want to keep using it?
- Can assets be reused?
- Can we reliably finish work?
- Can the system preserve continuity?

---

## 21. Mid-Term Goals — 1 to 3 Months

- Character Master generation
- Turnaround
- Expressions
- Storyboard generation
- at least one Video Provider
- TTS
- FFmpeg composition
- 10–20 reusable assets
- recurring characters and locations
- Episode Memory / Continuity
- callback / unresolved thread tracking
- stable publishing rhythm
- performance feedback collection
- Cost Dashboard
- retry / failure analytics
- model cost per episode
- average production time
- average human review time

Content data may influence format, but should not fully control the child's creativity.

---

## 22. Long-Term Goals — 3 to 12+ Months

- deeper Mini Utopia lore,
- recurring characters,
- world map,
- Portal rules,
- long-running story threads,
- automatic continuity checks,
- automated visual QC,
- additional Universes,
- reusable production Recipes,
- plugin-style image / video / voice / 3D integrations,
- possible commercial experiments if a stable audience emerges.

Possible future commercial paths may include:

- platform revenue,
- brand partnerships,
- original IP,
- merchandise,
- digital products,
- education-related content.

Commercialization is a possible outcome, not the original purpose.

---

## 23. Decision Guardrails

When the project starts to drift, come back to these rules.

### 1. Asset First

Anything that deserves long-term reuse should not be buried inside a one-off prompt.

### 2. Composition First

Stories reference Assets.

They do not clone them.

Universes organize Assets.

They do not permanently own them.

### 3. Creator First

The child should see creativity and choice, not infrastructure complexity.

### 4. Canon Has Boundaries, Freedom Has an Exit

Official Mini Utopia content keeps continuity.

Playground remains unrestricted.

### 5. Interface Before Vendor

Models will change.

Providers will change.

Asset IDs, Stories, approved creative history and project structure must survive those changes.

---

## 24. Current Repository Baseline

Current baseline:

```text
Version: v0.3 GitHub Foundation
Status: Foundation / pre-Character Factory v1
```

Current focus:

```text
Asset Protocol
↓
Repository
↓
Local Storage
↓
Universe / Canon
↓
Story references
↓
Job / Plugin interfaces
↓
Character Factory v1
```

The repository should remain deployable even before real AI credentials are configured.

Mock implementations are acceptable while the architecture is being validated.

---

## 25. Local Development

Recommended setup:

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env

streamlit run app.py
```

Run tests:

```bash
pytest
```

---

## 26. GitHub Workflow

The repository uses GitHub as the source of truth.

Recommended workflow:

```text
Local change
    ↓
Commit
    ↓
Push
    ↓
GitHub Actions
    ↓
Tests
    ↓
Merge / deploy
```

Suggested branch approach later:

```text
main
  stable working version

feature/character-factory
feature/story-builder
feature/gemini-provider
...
```

For now, direct commits to `main` are acceptable while the repository is still small, provided Actions remain green.

---

## 27. Secrets

Never commit:

```text
.env
API keys
tokens
service credentials
private cloud secrets
```

Only commit:

```text
.env.example
```

Deployment credentials should later use:

- GitHub Secrets,
- Streamlit Secrets,
- or another appropriate secret manager.

---

## 28. GitHub Actions

Every meaningful code change should eventually verify:

```text
Install dependencies
↓
Python import / compile check
↓
pytest
↓
schema validation
↓
repository tests
↓
plugin registry tests
```

As the project grows, add regression tests whenever a previously fixed bug could return.

---

## 29. Remote Deployment Note

SQLite and local media storage are appropriate for early local development.

They are **not** the final persistent architecture for a hosted multi-session application.

The interfaces must therefore remain replaceable:

```text
SQLiteRepository
        ↓
Future PostgreSQL / Supabase Repository
```

and:

```text
LocalStorage
        ↓
Future Cloud Object Storage
```

The Creator and Story layers should not care which backend is currently used.

---

## 30. Product Philosophy

We are not building a prompt collection.

We are building a **small creative operating system**.

A good result is not only:

> “AI generated a nice image.”

A better result is:

> “We created a Character once, approved it, saved it, reused it in many worlds, built stories around it, and can still find and reproduce the production decisions later.”

That is the difference between an AI toy and a production tool.

---

## 31. Working Agreement for Future Development

Before adding a feature, ask:

1. Is it an Asset, Story, Universe rule, Job, Plugin, Recipe or UI concern?
2. Should it survive model changes?
3. Should the child see this complexity?
4. Does it belong in Canon or Playground?
5. Can it be reused later?
6. Does it require a human review gate?
7. Can failure be retried without destroying approved work?
8. Does this feature move the current milestone forward?

If the answer to the last question is **no**, it can usually wait.

---

## 32. Next Milestone

### Character Factory v1

Next implementation target:

```text
Creator describes a character
        ↓
AI / Mock parses dimensions
        ↓
Editable Character Profile
        ↓
Save permanent CHAR_ID
        ↓
Generate / attach Master Reference
        ↓
Human approval
        ↓
Turnaround Job
        ↓
Front / Side / Back
        ↓
Character Library
```

This is the next major creator-facing feature and the first workflow that should feel genuinely magical to use.

---

## 33. Source of Truth

This README is the repository-level operational summary.

The formal strategic scope remains defined by:

**Mini Utopia / AI Creative Studio — Project Charter v1.0**

If README and Charter ever conflict on a major architectural principle, stop and explicitly version the decision rather than silently changing direction.

---

## 34. Final Principle

> **We want imagination to stay free,  
> while the system makes creativity reusable, continuous and producible.**


---

## Godot World Baseline

The current playable-world source of truth is:

**[Newbie Village 100×100 World Baseline](docs/WORLD_BASELINE_NEWBIE_VILLAGE_V1.md)**

Current smoke-test scene:

`res://scenes/newbie_village_100x100_v0_2.tscn`

The baseline locks the simple road hierarchy, yellow/green Block Bits language,
layered Forest Nature mountain treatment, larger road-facing houses, solid
collision, Resource Bits work areas and two separated skeleton encounters.

# ✨ Mini Utopia · AI Creative Studio

**Foundation v0.3 — GitHub baseline**

A Python/Streamlit creative studio for building reusable characters, places, objects, styles and stories. `Mini Utopia` is the first Universe running on the studio; it is not hard-coded as the whole product.

## Architecture principles

- Assets are independent and reusable. A Character does **not** belong to a Story.
- Stories reference Asset IDs instead of copying assets.
- Mini Utopia is `Universe_001`; Playground is intentionally non-canon.
- Repository, Storage, Provider and Plugin are separate interfaces so infrastructure can change later.
- Human review remains a first-class stage of the future generation pipeline.

## Repository tree

```text
mini-utopia-studio/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
├── .github/workflows/tests.yml
├── .streamlit/config.toml
├── studio/
│   ├── core/
│   ├── models/
│   ├── repositories/
│   ├── storage/
│   ├── providers/
│   ├── plugins/
│   ├── recipes/
│   ├── services/
│   └── ui/
├── prompts/
├── data/
└── tests/
```

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

## Tests

```bash
pytest -q
```

GitHub Actions runs tests and Python compilation on every push/PR to `main`.

## Streamlit Cloud

- Repository: this GitHub repository
- Branch: `main`
- Main file path: `app.py`
- Add API keys later via Streamlit Secrets; do not commit `.env`.

## Current capabilities

- `character.parse` — mock structured parser
- `character.turnaround` — interface/placeholder
- SQLite repository
- Local object storage
- Mini Utopia bootstrap Canon
- Playground story creation
- Reusable Character assets
- Studio Inspector

## Next milestone

**Character Factory v1**

1. OpenAI/Gemini structured parsing
2. editable character dimensions
3. Master Reference generation interface
4. human confirm/lock
5. three-view turnaround Job
6. Character asset pack storage

The first confirmed Traveler should remain usable in any future world or story without changing its permanent `CHAR_*` identity.

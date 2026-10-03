# Mini Utopia Durable Metadata Repository

M5 keeps the existing `StudioRepository` interface and makes the metadata backend configurable.

## One-time Supabase SQL setup

Run this once in the Supabase SQL editor:

```sql
create table if not exists public.studio_records (
  record_id text not null,
  kind text not null,
  name text not null default '',
  data jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (kind, record_id)
);

create index if not exists idx_studio_records_kind_updated
  on public.studio_records (kind, updated_at desc);
```

The app uses the server-side service-role key through PostgREST. Do not expose that key to client/browser code.

## Streamlit secrets / environment

```text
STUDIO_REPOSITORY_BACKEND=supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-side secret>
SUPABASE_METADATA_TABLE=studio_records
```

Object storage is configured independently:

```text
OBJECT_STORAGE_BACKEND=supabase
SUPABASE_STORAGE_BUCKET=mini-utopia-assets
```

## What becomes durable

When both Supabase repository and Supabase object storage are enabled:

- Character profiles and metadata
- Character Master file references
- World profiles
- World Blueprints
- World Concept file references
- Stories
- Jobs
- Character runtime GLB metadata
- Binary/media assets in the Supabase Storage bucket

## Local development

Default remains:

```text
STUDIO_REPOSITORY_BACKEND=sqlite
OBJECT_STORAGE_BACKEND=local
```

This keeps development simple and preserves existing tests/workflows.

## Existing local data

This milestone does not automatically recover a Streamlit-local SQLite database that has already disappeared after a redeploy. If a local database/file still exists, it can be migrated later; otherwise those missing records need to be recreated.

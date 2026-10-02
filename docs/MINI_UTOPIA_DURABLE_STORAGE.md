# Mini Utopia Durable Object Storage

M4.4 keeps the existing `ObjectStorage` contract and makes the backend configurable.

## Backends

### Local

Default for local development:

```text
OBJECT_STORAGE_BACKEND=local
```

Files are written under `DATA_DIR`.

### Supabase Storage

For durable binary/media assets:

```text
OBJECT_STORAGE_BACKEND=supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-side secret>
SUPABASE_STORAGE_BUCKET=mini-utopia-assets
```

Create the bucket in the Supabase dashboard before enabling the backend. A private bucket is recommended.

The service-role key is used only by the server-side Streamlit process. It must never be exposed in browser JavaScript or committed to Git.

## Assets covered

The same storage service is already used by:

- Character Master images
- World Concept images
- Character GLB runtime assets
- reference-character media

No service-specific code is required in those features.

## Current persistence boundary

M4.4 makes binary/media objects durable when Supabase Storage is configured.

The Studio metadata repository is still SQLite. On Streamlit Community Cloud, that SQLite database remains ephemeral. The next persistence milestone should move the repository layer to durable Postgres so metadata and object keys survive together.

## Migration

Existing local files are not automatically copied to Supabase. New writes use whichever backend is selected at startup.

A later migration utility can enumerate asset file references and copy reachable local objects into the durable bucket.

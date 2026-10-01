from __future__ import annotations
import sqlite3
from pathlib import Path
from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.universe import Universe
from studio.models.story import Story
from studio.models.job import Job
from studio.repositories.base import StudioRepository

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
CREATE TABLE IF NOT EXISTS universes (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stories (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  mode TEXT NOT NULL,
  universe_id TEXT,
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  capability TEXT NOT NULL,
  status TEXT NOT NULL,
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""


class SQLiteStudioRepository(StudioRepository):
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self):
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _json(obj):
        return obj.model_dump_json()

    def save_asset(self, asset: Asset) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO assets VALUES (?,?,?,?,?)",
                (asset.asset_id, asset.asset_type.value, asset.display_name, self._json(asset), asset.updated_at.isoformat()),
            )

    def get_asset(self, asset_id: str) -> Asset | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data FROM assets WHERE id=?", (asset_id,)).fetchone()
        return Asset.model_validate_json(row[0]) if row else None

    def list_assets(self, asset_type: AssetType | None = None) -> list[Asset]:
        query = "SELECT data FROM assets"
        args: tuple = ()
        if asset_type:
            query += " WHERE type=?"
            args = (asset_type.value,)
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, args).fetchall()
        return [Asset.model_validate_json(row[0]) for row in rows]

    def save_universe(self, universe: Universe) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO universes VALUES (?,?,?,?)",
                (universe.universe_id, universe.name, self._json(universe), universe.updated_at.isoformat()),
            )

    def get_universe(self, universe_id: str) -> Universe | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data FROM universes WHERE id=?", (universe_id,)).fetchone()
        return Universe.model_validate_json(row[0]) if row else None

    def list_universes(self) -> list[Universe]:
        with self._connect() as conn:
            rows = conn.execute("SELECT data FROM universes ORDER BY updated_at DESC").fetchall()
        return [Universe.model_validate_json(row[0]) for row in rows]

    def save_story(self, story: Story) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO stories VALUES (?,?,?,?,?,?)",
                (story.story_id, story.title, story.mode.value, story.universe_id, self._json(story), story.updated_at.isoformat()),
            )

    def get_story(self, story_id: str) -> Story | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data FROM stories WHERE id=?", (story_id,)).fetchone()
        return Story.model_validate_json(row[0]) if row else None

    def list_stories(self) -> list[Story]:
        with self._connect() as conn:
            rows = conn.execute("SELECT data FROM stories ORDER BY updated_at DESC").fetchall()
        return [Story.model_validate_json(row[0]) for row in rows]

    def save_job(self, job: Job) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?)",
                (job.job_id, job.capability, job.status.value, self._json(job), job.created_at.isoformat()),
            )

    def list_jobs(self) -> list[Job]:
        with self._connect() as conn:
            rows = conn.execute("SELECT data FROM jobs ORDER BY updated_at DESC").fetchall()
        return [Job.model_validate_json(row[0]) for row in rows]

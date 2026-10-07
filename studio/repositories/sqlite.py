from __future__ import annotations
import sqlite3
from pathlib import Path
from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.universe import Universe
from studio.models.story import Story
from studio.models.job import Job
from studio.models.equipment import CreatorCollection
from studio.models.baby import BabyRoster
from studio.models.quest import QuestDefinition
from studio.models.universe_memory import UniverseMemoryRecord
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
CREATE TABLE IF NOT EXISTS quests (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  world_asset_id TEXT NOT NULL,
  story_id TEXT,
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS universe_memories (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  source_key TEXT NOT NULL,
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_universe_memories_universe
  ON universe_memories(universe_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_universe_memories_source
  ON universe_memories(universe_id, source_key);
CREATE TABLE IF NOT EXISTS collections (
  id TEXT PRIMARY KEY,
  owner_key TEXT NOT NULL,
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS baby_rosters (
  id TEXT PRIMARY KEY,
  owner_key TEXT NOT NULL,
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

    def save_quest(self, quest: QuestDefinition) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO quests VALUES (?,?,?,?,?,?)",
                (
                    quest.quest_id,
                    quest.title,
                    quest.world_asset_id,
                    quest.story_id,
                    self._json(quest),
                    quest.updated_at.isoformat(),
                ),
            )

    def get_quest(self, quest_id: str) -> QuestDefinition | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM quests WHERE id=?",
                (quest_id,),
            ).fetchone()
        return QuestDefinition.model_validate_json(row[0]) if row else None

    def list_quests(self) -> list[QuestDefinition]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT data FROM quests ORDER BY updated_at DESC"
            ).fetchall()
        return [QuestDefinition.model_validate_json(row[0]) for row in rows]

    def save_universe_memory(self, memory: UniverseMemoryRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO universe_memories VALUES (?,?,?,?,?,?)",
                (
                    memory.memory_id,
                    memory.universe_id,
                    memory.kind.value,
                    memory.source_key,
                    self._json(memory),
                    memory.updated_at.isoformat(),
                ),
            )

    def get_universe_memory(
        self,
        memory_id: str,
    ) -> UniverseMemoryRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM universe_memories WHERE id=?",
                (memory_id,),
            ).fetchone()
        return (
            UniverseMemoryRecord.model_validate_json(row[0])
            if row
            else None
        )

    def list_universe_memories(
        self,
        universe_id: str | None = None,
    ) -> list[UniverseMemoryRecord]:
        query = "SELECT data FROM universe_memories"
        args: tuple = ()
        if universe_id is not None:
            query += " WHERE universe_id=?"
            args = (universe_id,)
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, args).fetchall()
        return [
            UniverseMemoryRecord.model_validate_json(row[0])
            for row in rows
        ]

    def save_collection(self, collection: CreatorCollection) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO collections VALUES (?,?,?,?)",
                (
                    collection.collection_id,
                    collection.owner_key,
                    self._json(collection),
                    collection.updated_at.isoformat(),
                ),
            )

    def get_collection(self, collection_id: str) -> CreatorCollection | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM collections WHERE id=?",
                (collection_id,),
            ).fetchone()
        return CreatorCollection.model_validate_json(row[0]) if row else None

    def save_baby_roster(self, roster: BabyRoster) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO baby_rosters VALUES (?,?,?,?)",
                (
                    roster.roster_id,
                    roster.owner_key,
                    self._json(roster),
                    roster.updated_at.isoformat(),
                ),
            )

    def get_baby_roster(self, roster_id: str) -> BabyRoster | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM baby_rosters WHERE id=?",
                (roster_id,),
            ).fetchone()
        return BabyRoster.model_validate_json(row[0]) if row else None

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

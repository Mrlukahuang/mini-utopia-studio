from __future__ import annotations

from urllib.parse import quote

import requests

from studio.core.enums import AssetType
from studio.models.asset import Asset
from studio.models.job import Job
from studio.models.equipment import CreatorCollection
from studio.models.baby import BabyRoster
from studio.models.story import Story
from studio.models.universe import Universe
from studio.repositories.base import StudioRepository


class SupabaseStudioRepository(StudioRepository):
    """PostgREST-backed durable metadata repository.

    A single table stores canonical model JSON by record kind and id. This keeps
    the Python repository contract stable while avoiding duplicate relational
    schemas for rapidly evolving Pydantic models.
    """

    def __init__(
        self,
        *,
        url: str,
        service_role_key: str,
        table: str = "studio_records",
        timeout_seconds: float = 30.0,
    ):
        if not url:
            raise ValueError("Supabase URL is required.")
        if not service_role_key:
            raise ValueError("Supabase service-role key is required.")
        if not table:
            raise ValueError("Supabase metadata table is required.")

        self.url = url.rstrip("/")
        self.service_role_key = service_role_key
        self.table = table
        self.timeout_seconds = timeout_seconds

    @property
    def backend_name(self) -> str:
        return "supabase"

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    @property
    def _table_url(self) -> str:
        return f"{self.url}/rest/v1/{quote(self.table, safe='')}"

    def _upsert(
        self,
        *,
        record_id: str,
        kind: str,
        name: str,
        data: dict,
        updated_at: str,
    ) -> None:
        response = requests.post(
            self._table_url,
            params={"on_conflict": "kind,record_id"},
            headers=self._headers(prefer="resolution=merge-duplicates"),
            json={
                "record_id": record_id,
                "kind": kind,
                "name": name,
                "data": data,
                "updated_at": updated_at,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

    def _get_one(self, *, kind: str, record_id: str) -> dict | None:
        response = requests.get(
            self._table_url,
            params={
                "select": "data",
                "kind": f"eq.{kind}",
                "record_id": f"eq.{record_id}",
                "limit": "1",
            },
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return None
        return rows[0]["data"]

    def _list(self, *, kind: str) -> list[dict]:
        response = requests.get(
            self._table_url,
            params={
                "select": "data",
                "kind": f"eq.{kind}",
                "order": "updated_at.desc",
            },
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return [row["data"] for row in response.json()]

    def save_asset(self, asset: Asset) -> None:
        self._upsert(
            record_id=asset.asset_id,
            kind="asset",
            name=asset.display_name,
            data=asset.model_dump(mode="json"),
            updated_at=asset.updated_at.isoformat(),
        )

    def get_asset(self, asset_id: str) -> Asset | None:
        data = self._get_one(kind="asset", record_id=asset_id)
        return Asset.model_validate(data) if data else None

    def list_assets(self, asset_type: AssetType | None = None) -> list[Asset]:
        assets = [Asset.model_validate(data) for data in self._list(kind="asset")]
        if asset_type is not None:
            assets = [asset for asset in assets if asset.asset_type == asset_type]
        return assets

    def save_universe(self, universe: Universe) -> None:
        self._upsert(
            record_id=universe.universe_id,
            kind="universe",
            name=universe.name,
            data=universe.model_dump(mode="json"),
            updated_at=universe.updated_at.isoformat(),
        )

    def get_universe(self, universe_id: str) -> Universe | None:
        data = self._get_one(kind="universe", record_id=universe_id)
        return Universe.model_validate(data) if data else None

    def list_universes(self) -> list[Universe]:
        return [Universe.model_validate(data) for data in self._list(kind="universe")]

    def save_story(self, story: Story) -> None:
        self._upsert(
            record_id=story.story_id,
            kind="story",
            name=story.title,
            data=story.model_dump(mode="json"),
            updated_at=story.updated_at.isoformat(),
        )

    def get_story(self, story_id: str) -> Story | None:
        data = self._get_one(kind="story", record_id=story_id)
        return Story.model_validate(data) if data else None

    def list_stories(self) -> list[Story]:
        return [Story.model_validate(data) for data in self._list(kind="story")]

    def save_collection(self, collection: CreatorCollection) -> None:
        self._upsert(
            record_id=collection.collection_id,
            kind="collection",
            name=collection.owner_key,
            data=collection.model_dump(mode="json"),
            updated_at=collection.updated_at.isoformat(),
        )

    def get_collection(self, collection_id: str) -> CreatorCollection | None:
        data = self._get_one(kind="collection", record_id=collection_id)
        return CreatorCollection.model_validate(data) if data else None

    def save_baby_roster(self, roster: BabyRoster) -> None:
        self._upsert(
            record_id=roster.roster_id,
            kind="baby_roster",
            name=roster.owner_key,
            data=roster.model_dump(mode="json"),
            updated_at=roster.updated_at.isoformat(),
        )

    def get_baby_roster(self, roster_id: str) -> BabyRoster | None:
        data = self._get_one(kind="baby_roster", record_id=roster_id)
        return BabyRoster.model_validate(data) if data else None

    def save_job(self, job: Job) -> None:
        self._upsert(
            record_id=job.job_id,
            kind="job",
            name=job.capability,
            data=job.model_dump(mode="json"),
            updated_at=job.updated_at.isoformat(),
        )

    def list_jobs(self) -> list[Job]:
        return [Job.model_validate(data) for data in self._list(kind="job")]

from __future__ import annotations

from studio.core.enums import AssetType, ReviewStatus, StoryMode
from studio.models.asset import now_utc
from studio.models.story import Story
from studio.models.universe_memory import (
    UniverseMemoryKind,
    UniverseMemoryRecord,
)
from studio.repositories.base import StudioRepository
from studio.services.baby_service import DEFAULT_BABY_ROSTER_ID
from studio.services.equipment_service import DEFAULT_COLLECTION_ID


class LivingUniverseMemoryService:
    """Durable, idempotent Canon memory built from stable source IDs."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def _upsert(
        self,
        record: UniverseMemoryRecord,
    ) -> UniverseMemoryRecord:
        existing = self.repository.get_universe_memory(record.memory_id)
        if existing is not None:
            record.created_at = existing.created_at
        record.updated_at = now_utc()
        self.repository.save_universe_memory(record)
        return record

    def ingest_story(self, story: Story) -> UniverseMemoryRecord | None:
        if story.mode != StoryMode.CANON:
            return None
        if story.status in (ReviewStatus.REJECTED, ReviewStatus.ARCHIVED):
            return None
        if not story.universe_id:
            return None

        world_asset_id = next(
            (
                asset_id
                for asset_id in story.asset_ids
                if (
                    (asset := self.repository.get_asset(asset_id)) is not None
                    and asset.asset_type == AssetType.LOCATION
                )
            ),
            None,
        )
        beat_parts = [
            value.strip()
            for value in (
                story.hook,
                story.discovery,
                story.conflict,
                story.adventure,
                story.twist,
                story.ending,
            )
            if value.strip()
        ]
        beat_summary = " → ".join(beat_parts[:3])
        summary = f"Canon Story: {story.title}. {story.premise}"
        if beat_summary:
            summary += f" Key beats: {beat_summary}"

        return self._upsert(
            UniverseMemoryRecord.create(
                universe_id=story.universe_id,
                source_key=f"story:{story.story_id}",
                kind=UniverseMemoryKind.CANON_STORY,
                summary=summary,
                asset_ids=list(story.asset_ids),
                story_id=story.story_id,
                world_asset_id=world_asset_id,
                metadata={"story_status": story.status.value},
            )
        )

    def sync_known_state(
        self,
        *,
        universe_id: str,
    ) -> list[UniverseMemoryRecord]:
        """Materialize durable Canon-relevant signals without duplicating them."""

        for story in self.repository.list_stories():
            if story.universe_id == universe_id:
                self.ingest_story(story)

        for world in self.repository.list_assets(AssetType.LOCATION):
            if world.status == ReviewStatus.ARCHIVED:
                continue
            self._upsert(
                UniverseMemoryRecord.create(
                    universe_id=universe_id,
                    source_key=f"world:{world.asset_id}:discovered",
                    kind=UniverseMemoryKind.WORLD_DISCOVERY,
                    summary=f"World discovered: {world.display_name}.",
                    asset_ids=[world.asset_id],
                    world_asset_id=world.asset_id,
                )
            )

        roster = self.repository.get_baby_roster(DEFAULT_BABY_ROSTER_ID)
        if roster is not None:
            baby = roster.active_baby()
            if baby is not None:
                self._upsert(
                    UniverseMemoryRecord.create(
                        universe_id=universe_id,
                        source_key=f"baby:{baby.baby_id}:state",
                        kind=UniverseMemoryKind.BABY_MILESTONE,
                        summary=(
                            f"Active Baby {baby.display_name} is Lv.{baby.level} "
                            f"with XP {baby.xp} and Bond {baby.bond}."
                        ),
                        baby_id=baby.baby_id,
                        metadata={
                            "species_id": baby.species_id,
                            "level": baby.level,
                            "xp": baby.xp,
                            "bond": baby.bond,
                        },
                    )
                )

        collection = self.repository.get_collection(DEFAULT_COLLECTION_ID)
        if collection is not None:
            equipment_assets = {
                asset.asset_id: asset
                for asset in self.repository.list_assets(AssetType.EQUIPMENT)
                if asset.metadata.get("equipment_definition")
            }
            for item in collection.items:
                definition_asset = equipment_assets.get(item.definition_id)
                if (
                    definition_asset is None
                    or not definition_asset.slug.startswith("reward_")
                ):
                    continue
                self._upsert(
                    UniverseMemoryRecord.create(
                        universe_id=universe_id,
                        source_key=f"item:{item.item_instance_id}:acquired",
                        kind=UniverseMemoryKind.ITEM_ACQUIRED,
                        summary=(
                            f"Reward acquired: {definition_asset.display_name} "
                            f"({item.rarity.value.title()})."
                        ),
                        asset_ids=[definition_asset.asset_id],
                        item_instance_id=item.item_instance_id,
                        metadata={
                            "definition_id": item.definition_id,
                            "rarity": item.rarity.value,
                        },
                    )
                )

        return self.list(universe_id=universe_id)

    def list(
        self,
        *,
        universe_id: str,
    ) -> list[UniverseMemoryRecord]:
        return self.repository.list_universe_memories(universe_id)

    def query(
        self,
        *,
        universe_id: str,
        asset_ids: list[str] | None = None,
        world_asset_id: str | None = None,
        limit: int = 20,
    ) -> list[UniverseMemoryRecord]:
        wanted = set(asset_ids or [])
        result: list[UniverseMemoryRecord] = []
        for memory in self.repository.list_universe_memories(universe_id):
            if world_asset_id and memory.world_asset_id == world_asset_id:
                result.append(memory)
                continue
            if wanted and wanted.intersection(memory.asset_ids):
                result.append(memory)
                continue
            if not wanted and world_asset_id is None:
                result.append(memory)
        return result[:limit]

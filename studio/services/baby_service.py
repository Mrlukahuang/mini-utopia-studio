from __future__ import annotations

from studio.models.asset import now_utc
from studio.models.baby import (
    BabyCompanion,
    BabyRoster,
    BabyRuntimeSpec,
    create_baby_companion,
)
from studio.repositories.base import StudioRepository


DEFAULT_BABY_ROSTER_ID = "BABIES_DEFAULT"
BABY_XP_PER_LEVEL = 100

BABY_ARCHETYPES = {
    "cloud_baby": "Cloud Baby / 云朵宝宝",
    "sheep_baby": "Sheep Baby / 小羊宝宝",
    "star_baby": "Star Baby / 星星宝宝",
    "robot_baby": "Robot Baby / 机器人宝宝",
    "forest_baby": "Forest Baby / 森林宝宝",
}


class BabyService:
    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def get_roster(self) -> BabyRoster:
        roster = self.repository.get_baby_roster(DEFAULT_BABY_ROSTER_ID)
        if roster is None:
            roster = BabyRoster(roster_id=DEFAULT_BABY_ROSTER_ID)
            self.repository.save_baby_roster(roster)
        return roster

    def active_baby(self) -> BabyCompanion | None:
        return self.get_roster().active_baby()

    def create_initial_baby(
        self,
        *,
        display_name: str,
        species_id: str,
    ) -> BabyRoster:
        roster = self.get_roster()
        if roster.babies:
            raise ValueError("Initial Baby already exists.")
        if species_id not in BABY_ARCHETYPES:
            raise ValueError(f"Unknown Baby archetype: {species_id}")
        name = display_name.strip()
        if not name:
            raise ValueError("Baby name cannot be empty.")
        if len(name) > 40:
            raise ValueError("Baby name must be 40 characters or fewer.")

        baby = create_baby_companion(display_name=name, species_id=species_id)
        baby.active = True
        roster.babies.append(baby)
        roster.active_baby_id = baby.baby_id
        roster.updated_at = now_utc()
        self.repository.save_baby_roster(roster)
        return roster

    def rename(self, *, baby_id: str, display_name: str) -> BabyRoster:
        roster = self.get_roster()
        baby = roster.baby_by_id(baby_id)
        if baby is None:
            raise ValueError(f"Baby not found: {baby_id}")
        name = display_name.strip()
        if not name:
            raise ValueError("Baby name cannot be empty.")
        if len(name) > 40:
            raise ValueError("Baby name must be 40 characters or fewer.")
        baby.display_name = name
        baby.updated_at = now_utc()
        roster.updated_at = baby.updated_at
        self.repository.save_baby_roster(roster)
        return roster

    def set_active(self, *, baby_id: str) -> BabyRoster:
        roster = self.get_roster()
        target = roster.baby_by_id(baby_id)
        if target is None:
            raise ValueError(f"Baby not found: {baby_id}")
        for baby in roster.babies:
            baby.active = baby.baby_id == baby_id
            baby.updated_at = now_utc()
        roster.active_baby_id = baby_id
        roster.updated_at = now_utc()
        self.repository.save_baby_roster(roster)
        return roster

    def add_xp(self, *, baby_id: str, amount: int = 25) -> BabyRoster:
        if amount <= 0:
            raise ValueError("XP amount must be positive.")
        roster = self.get_roster()
        baby = roster.baby_by_id(baby_id)
        if baby is None:
            raise ValueError(f"Baby not found: {baby_id}")
        baby.xp += amount
        baby.level = 1 + baby.xp // BABY_XP_PER_LEVEL
        baby.updated_at = now_utc()
        roster.updated_at = baby.updated_at
        self.repository.save_baby_roster(roster)
        return roster

    def add_bond(self, *, baby_id: str, amount: int = 5) -> BabyRoster:
        if amount <= 0:
            raise ValueError("Bond amount must be positive.")
        roster = self.get_roster()
        baby = roster.baby_by_id(baby_id)
        if baby is None:
            raise ValueError(f"Baby not found: {baby_id}")
        baby.bond += amount
        baby.updated_at = now_utc()
        roster.updated_at = baby.updated_at
        self.repository.save_baby_roster(roster)
        return roster

    def runtime_spec(self, baby_id: str | None = None) -> BabyRuntimeSpec | None:
        roster = self.get_roster()
        baby = (
            roster.baby_by_id(baby_id)
            if baby_id is not None
            else roster.active_baby()
        )
        if baby is None:
            return None
        return BabyRuntimeSpec(
            baby_id=baby.baby_id,
            display_name=baby.display_name,
            species_id=baby.species_id,
            appearance_seed=baby.appearance_seed,
            growth_stage=baby.growth_stage,
            level=baby.level,
            active=baby.active,
            cosmetic_item_ids=list(baby.cosmetic_item_ids),
        )

    def export_runtime_spec(self, *, target_path, baby_id: str | None = None):
        spec = self.runtime_spec(baby_id)
        if spec is None:
            raise ValueError("No Baby is available for runtime export.")
        return spec.save_json(target_path)

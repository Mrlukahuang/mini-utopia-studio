from __future__ import annotations

from pydantic import BaseModel


class FirstAdventureStatus(BaseModel):
    character_asset_id: str | None = None
    character_name: str | None = None

    character_ready: bool = False
    baby_ready: bool = False
    loadout_ready: bool = False
    play_session_ready: bool = False
    reward_waiting: bool = False
    reward_claimed: bool = False
    reward_equipped: bool = False
    stronger_session_ready: bool = False

    @property
    def completed_steps(self) -> int:
        return sum(
            int(value)
            for value in (
                self.character_ready,
                self.baby_ready,
                self.loadout_ready,
                self.play_session_ready,
                self.reward_claimed,
                self.reward_equipped,
                self.stronger_session_ready,
            )
        )

    @property
    def total_steps(self) -> int:
        return 7

    @property
    def complete(self) -> bool:
        return self.completed_steps == self.total_steps

from __future__ import annotations

from pydantic import BaseModel, Field


class EpisodeBatchRenderResult(BaseModel):
    episode_id: str
    total_shots: int = 0
    eligible_shots: int = 0
    rendered_now: int = 0
    already_rendered: int = 0
    failed_shots: list[str] = Field(default_factory=list)
    blocked_shots: list[str] = Field(default_factory=list)

    @property
    def complete(self) -> bool:
        return (
            self.total_shots > 0
            and self.rendered_now + self.already_rendered == self.total_shots
            and not self.failed_shots
            and not self.blocked_shots
        )

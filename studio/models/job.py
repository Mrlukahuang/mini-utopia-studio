from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from studio.core.enums import JobStatus
from studio.models.asset import now_utc


class Job(BaseModel):
    job_id: str
    capability: str
    provider: str
    input_asset_ids: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.QUEUED
    attempt: int = 0
    output_asset_ids: list[str] = Field(default_factory=list)
    error: str | None = None
    estimated_cost: float | None = None
    actual_cost: float | None = None
    created_at: datetime = Field(default_factory=now_utc)
    started_at: datetime | None = None
    finished_at: datetime | None = None

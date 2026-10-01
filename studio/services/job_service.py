from studio.core.ids import new_id
from studio.models.job import Job
from studio.repositories.base import StudioRepository


class JobService:
    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def queue(self, *, capability: str, provider: str, input_asset_ids: list[str] | None = None, parameters: dict | None = None) -> Job:
        job = Job(
            job_id=new_id("JOB"),
            capability=capability,
            provider=provider,
            input_asset_ids=input_asset_ids or [],
            parameters=parameters or {},
        )
        self.repository.save_job(job)
        return job

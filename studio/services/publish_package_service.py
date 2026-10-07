from __future__ import annotations

import hashlib
import json
from pathlib import Path

from studio.models.asset import now_utc
from studio.models.publish_package import PublishPackageRecord
from studio.repositories.base import StudioRepository
from studio.services.episode_assembly_service import EpisodeAssemblyService
from studio.services.subtitle_track_service import SubtitleTrackService


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PublishPackageService:
    """Create a restart-safe shareable package from a ready Episode assembly."""

    def __init__(
        self,
        repository: StudioRepository,
        assembly: EpisodeAssemblyService,
        *,
        project_root: str | Path | None = None,
    ):
        self.repository = repository
        self.assembly = assembly
        self.project_root = (
            Path(project_root)
            if project_root is not None
            else PROJECT_ROOT
        )
        self.subtitles = SubtitleTrackService(
            repository,
            project_root=self.project_root,
        )

    def status_for(self, episode_id: str) -> PublishPackageRecord:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        existing = episode.publish_package
        expected = self._expected_record(
            episode_id,
            title=(existing.title if existing is not None else None),
            description=(
                existing.description
                if existing is not None
                else None
            ),
        )
        if existing is None:
            return expected

        if existing.source_fingerprint != expected.source_fingerprint:
            return existing.model_copy(update={"status": "stale"})

        required = [
            self.project_root / existing.final_video_path,
            self.project_root / existing.subtitle_srt_path,
            self.project_root / existing.transcript_path,
            self.project_root / existing.metadata_path,
            self.project_root / existing.manifest_path,
        ]
        if existing.status == "ready" and any(
            not path.exists() for path in required
        ):
            return existing.model_copy(update={"status": "missing"})
        return existing

    def generate(
        self,
        episode_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> PublishPackageRecord:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        assembly = self.assembly.status_for(episode_id)
        if assembly.status != "ready":
            raise ValueError(
                "Publish Package requires a current assembled Episode video."
            )

        record = self._expected_record(
            episode_id,
            title=title,
            description=description,
        )
        package_dir = (
            self.project_root
            / "godot"
            / "runtime_state"
            / "publish"
            / episode_id
        )
        package_dir.mkdir(parents=True, exist_ok=True)

        try:
            # The final video remains the current assembly output. Package files
            # reference it instead of copying a potentially large MP4.
            srt_path = self.subtitles.export_srt(episode_id)
            transcript = self._transcript_text(episode_id)
            transcript_path = self.project_root / record.transcript_path
            transcript_path.write_text(transcript, encoding="utf-8")

            metadata = {
                "title": record.title,
                "description": record.description,
                "episode_id": episode.episode_id,
                "story_id": episode.story_id,
                "world_asset_id": episode.world_asset_id,
                "asset_ids": list(episode.asset_ids),
                "duration_seconds": assembly.total_duration_seconds,
                "clip_count": assembly.clip_count,
                "cover_frame_path": record.cover_frame_path,
                "subtitle_srt_path": str(
                    srt_path.relative_to(self.project_root)
                ),
            }
            metadata_path = self.project_root / record.metadata_path
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            manifest = {
                "schema_version": "1.0",
                "source_fingerprint": record.source_fingerprint,
                "episode_id": episode.episode_id,
                "story_id": episode.story_id,
                "world_asset_id": episode.world_asset_id,
                "asset_ids": list(episode.asset_ids),
                "final_video_path": record.final_video_path,
                "subtitle_srt_path": record.subtitle_srt_path,
                "transcript_path": record.transcript_path,
                "metadata_path": record.metadata_path,
                "cover_frame_path": record.cover_frame_path,
                "assembly_fingerprint": assembly.source_fingerprint,
            }
            manifest_path = self.project_root / record.manifest_path
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            record = record.model_copy(
                update={
                    "status": "ready",
                    "generated_at": now_utc(),
                    "error": "",
                }
            )
        except Exception as exc:
            record = record.model_copy(
                update={
                    "status": "failed",
                    "error": str(exc),
                }
            )

        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(
                f"Episode not found after package generation: {episode_id}"
            )
        episode.publish_package = record
        episode.final_package_ready = record.status == "ready"
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return record

    def file_bytes(
        self,
        relative_path: str,
    ) -> bytes | None:
        if not relative_path:
            return None
        path = self.project_root / relative_path
        if not path.exists() or not path.is_file():
            return None
        return path.read_bytes()

    def _expected_record(
        self,
        episode_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> PublishPackageRecord:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        assembly = self.assembly.status_for(episode_id)

        package_title = (title or episode.title).strip()
        story = self.repository.get_story(episode.story_id)
        package_description = (
            description
            if description is not None
            else (story.premise if story is not None else "")
        ).strip()

        subtitle_payload = [
            cue.model_dump(mode="json")
            for cue in episode.subtitle_track
        ]
        audio_payload = [
            line.model_dump(mode="json")
            for line in episode.audio_timeline
        ]
        fingerprint_payload = {
            "assembly": assembly.source_fingerprint,
            "title": package_title,
            "description": package_description,
            "subtitles": subtitle_payload,
            "audio": audio_payload,
            "story_id": episode.story_id,
            "world_asset_id": episode.world_asset_id,
            "asset_ids": list(episode.asset_ids),
        }
        digest = hashlib.sha256(
            json.dumps(
                fingerprint_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest().upper()

        prefix = f"godot/runtime_state/publish/{episode_id}"
        return PublishPackageRecord(
            episode_id=episode_id,
            source_fingerprint=digest,
            status="missing",
            final_video_path=assembly.video_path,
            subtitle_srt_path=(
                f"godot/runtime_state/subtitles/{episode_id}.srt"
            ),
            transcript_path=f"{prefix}/transcript.txt",
            metadata_path=f"{prefix}/metadata.json",
            manifest_path=f"{prefix}/package.json",
            cover_frame_path=self._cover_frame_path(episode),
            title=package_title,
            description=package_description,
            story_id=episode.story_id,
            world_asset_id=episode.world_asset_id,
            asset_ids=list(episode.asset_ids),
        )

    @staticmethod
    def _cover_frame_path(episode) -> str:
        for scene in episode.scenes:
            for shot in scene.shots:
                frame = episode.storyboard_frames.get(shot.shot_id)
                if (
                    frame is not None
                    and frame.status == "ready"
                    and frame.approved_current
                ):
                    return frame.frame_path
        return ""

    def _transcript_text(self, episode_id: str) -> str:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        lines: list[str] = []
        for line in sorted(
            episode.audio_timeline,
            key=lambda item: (item.start_seconds, item.line_id),
        ):
            speaker = "Narrator"
            if line.speaker_kind == "character":
                speaker = line.speaker_asset_id or "Character"
            lines.append(
                f"[{line.start_seconds:.1f}s] {speaker}: {line.text}"
            )
        return "\n".join(lines) + ("\n" if lines else "")

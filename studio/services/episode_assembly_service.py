from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from studio.models.asset import now_utc
from studio.models.episode_assembly import (
    EpisodeAssemblyClip,
    EpisodeAssemblyRecord,
)
from studio.repositories.base import StudioRepository
from studio.services.shot_render_service import ShotRenderService


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class EpisodeAssemblyService:
    """Assemble current Shot MP4s into one ordered Episode video."""

    def __init__(
        self,
        repository: StudioRepository,
        shot_renderer: ShotRenderService,
        *,
        assembly_runner: Callable[[list[Path], Path], None] | None = None,
        project_root: str | Path | None = None,
    ):
        self.repository = repository
        self.shot_renderer = shot_renderer
        self.assembly_runner = assembly_runner
        self.project_root = (
            Path(project_root)
            if project_root is not None
            else PROJECT_ROOT
        )

    def status_for(self, episode_id: str) -> EpisodeAssemblyRecord:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        expected = self._build_expected(episode_id)
        existing = episode.episode_assembly
        if existing is None:
            return expected

        if existing.source_fingerprint != expected.source_fingerprint:
            return existing.model_copy(update={"status": "stale"})

        video_path = self.project_root / existing.video_path
        manifest_path = self.project_root / existing.manifest_path
        if (
            existing.status == "ready"
            and (
                not self.shot_renderer._valid_mp4(video_path)
                or not manifest_path.exists()
            )
        ):
            return existing.model_copy(update={"status": "missing"})
        return existing

    def assemble(self, episode_id: str) -> EpisodeAssemblyRecord:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        expected = self._build_expected(episode_id)
        if not expected.clips:
            raise ValueError("Episode has no rendered Shots to assemble.")

        expected_ids = [
            shot.shot_id
            for scene in episode.scenes
            for shot in scene.shots
        ]
        clip_ids = [clip.shot_id for clip in expected.clips]
        missing = [
            shot_id
            for shot_id in expected_ids
            if shot_id not in clip_ids
        ]
        if missing:
            raise ValueError(
                "Episode assembly requires current rendered Shots: "
                + ", ".join(missing)
            )

        video_path = self.project_root / expected.video_path
        manifest_path = self.project_root / expected.manifest_path
        video_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        record = expected.model_copy(update={"status": "assembling"})
        episode.episode_assembly = record
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)

        clip_paths = [
            self.project_root / clip.video_path
            for clip in record.clips
        ]

        try:
            if video_path.exists():
                video_path.unlink()
            if self.assembly_runner is not None:
                self.assembly_runner(clip_paths, video_path)
            else:
                self._concat_mp4s(clip_paths, video_path)

            if not self.shot_renderer._valid_mp4(video_path):
                raise RuntimeError(
                    "Episode assembly did not produce a valid MP4."
                )

            manifest = {
                "schema_version": "1.0",
                "episode_id": episode.episode_id,
                "story_id": episode.story_id,
                "world_asset_id": episode.world_asset_id,
                "asset_ids": list(episode.asset_ids),
                "source_fingerprint": record.source_fingerprint,
                "clips": [
                    clip.model_dump(mode="json")
                    for clip in record.clips
                ],
                "audio_line_ids": record.audio_line_ids,
                "subtitle_cue_ids": record.subtitle_cue_ids,
                "total_duration_seconds": record.total_duration_seconds,
            }
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
                f"Episode not found after assembly: {episode_id}"
            )
        episode.episode_assembly = record
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return record

    def video_bytes(
        self,
        record: EpisodeAssemblyRecord,
    ) -> bytes | None:
        path = self.project_root / record.video_path
        if not self.shot_renderer._valid_mp4(path):
            return None
        return path.read_bytes()

    def manifest_bytes(
        self,
        record: EpisodeAssemblyRecord,
    ) -> bytes | None:
        path = self.project_root / record.manifest_path
        if not path.exists():
            return None
        return path.read_bytes()

    def _build_expected(
        self,
        episode_id: str,
    ) -> EpisodeAssemblyRecord:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        clips: list[EpisodeAssemblyClip] = []
        cursor = 0.0
        fingerprint_parts: list[str] = []

        for scene in episode.scenes:
            for shot in scene.shots:
                render = self.shot_renderer.status_for(
                    episode_id=episode_id,
                    scene_id=scene.scene_id,
                    shot_id=shot.shot_id,
                )
                if render.status != "rendered":
                    continue
                clips.append(
                    EpisodeAssemblyClip(
                        scene_id=scene.scene_id,
                        shot_id=shot.shot_id,
                        source_fingerprint=render.source_fingerprint,
                        video_path=render.video_path,
                        start_seconds=cursor,
                        duration_seconds=render.duration_seconds,
                    )
                )
                cursor += render.duration_seconds
                fingerprint_parts.append(
                    "|".join(
                        [
                            scene.scene_id,
                            shot.shot_id,
                            render.source_fingerprint,
                            render.storyboard_approval_fingerprint,
                        ]
                    )
                )

        subtitle_ids = [
            cue.cue_id
            for cue in episode.subtitle_track
            if cue.approved
        ]
        audio_ids = [
            line.line_id
            for line in episode.audio_timeline
            if line.approved
        ]
        fingerprint_parts.extend(
            "SUB:" + cue_id for cue_id in subtitle_ids
        )
        fingerprint_parts.extend(
            "AUD:" + line_id for line_id in audio_ids
        )
        digest = hashlib.sha256(
            "\n".join(fingerprint_parts).encode("utf-8")
        ).hexdigest().upper()

        return EpisodeAssemblyRecord(
            episode_id=episode_id,
            source_fingerprint=digest,
            status="missing",
            video_path=(
                "godot/runtime_state/episodes/"
                + episode_id
                + "/episode.mp4"
            ),
            manifest_path=(
                "godot/runtime_state/episodes/"
                + episode_id
                + "/assembly.json"
            ),
            subtitle_srt_path=(
                "godot/runtime_state/subtitles/"
                + episode_id
                + ".srt"
            ),
            clip_count=len(clips),
            total_duration_seconds=cursor,
            clips=clips,
            audio_line_ids=audio_ids,
            subtitle_cue_ids=subtitle_ids,
        )

    def _concat_mp4s(
        self,
        clip_paths: list[Path],
        output_path: Path,
    ) -> None:
        ffmpeg = self._resolve_ffmpeg_binary()
        if ffmpeg is None:
            raise RuntimeError(
                "Video encoder is unavailable. Install ffmpeg to assemble Episode."
            )

        concat_file = output_path.parent / "concat.txt"
        concat_file.write_text(
            "\n".join(
                "file '"
                + str(path.resolve()).replace("'", "'\\''")
                + "'"
                for path in clip_paths
            )
            + "\n",
            encoding="utf-8",
        )
        try:
            completed = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_file),
                    "-c",
                    "copy",
                    "-movflags",
                    "+faststart",
                    str(output_path),
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            if completed.returncode != 0:
                details = (
                    completed.stderr or completed.stdout
                ).strip()
                raise RuntimeError(
                    "Episode MP4 assembly failed"
                    + (
                        f": {details[-1000:]}"
                        if details
                        else "."
                    )
                )
        finally:
            concat_file.unlink(missing_ok=True)

    @staticmethod
    def _resolve_ffmpeg_binary() -> str | None:
        explicit = os.environ.get("MINI_UTOPIA_FFMPEG_BIN")
        candidates = [
            explicit,
            shutil.which("ffmpeg"),
            "/opt/homebrew/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ]
        return next(
            (
                str(value)
                for value in candidates
                if value and Path(value).exists()
            ),
            None,
        )

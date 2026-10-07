from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from studio.models.asset import now_utc
from studio.models.shot_render import ShotRenderRecord
from studio.repositories.base import StudioRepository
from studio.services.director_shot_session_service import (
    DirectorShotSessionService,
)
from studio.services.storyboard_service import StoryboardService


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ShotRenderService:
    """Render one approved Director Shot into a derived MP4 clip."""

    def __init__(
        self,
        repository: StudioRepository,
        director: DirectorShotSessionService,
        storyboard: StoryboardService,
        *,
        render_runner: Callable[[Path, Path], None] | None = None,
        project_root: str | Path | None = None,
        fps: int = 24,
        width: int = 960,
        height: int = 540,
    ):
        self.repository = repository
        self.director = director
        self.storyboard = storyboard
        self.render_runner = render_runner
        self.project_root = (
            Path(project_root)
            if project_root is not None
            else PROJECT_ROOT
        )
        self.godot_root = self.project_root / "godot"
        self.fps = int(fps)
        self.width = int(width)
        self.height = int(height)
        self.request_path = (
            self.godot_root
            / "runtime_state"
            / "shot_capture_request.json"
        )

    def status_for(
        self,
        *,
        episode_id: str,
        scene_id: str,
        shot_id: str,
    ) -> ShotRenderRecord:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        scene = next(
            (value for value in episode.scenes if value.scene_id == scene_id),
            None,
        )
        if scene is None:
            raise ValueError(f"Scene not found: {scene_id}")
        shot = next(
            (value for value in scene.shots if value.shot_id == shot_id),
            None,
        )
        if shot is None:
            raise ValueError(f"Shot not found: {shot_id}")

        frame = self.storyboard.status_for(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
        )
        existing = episode.shot_renders.get(shot_id)
        expected_path = self._video_relative_path(
            episode_id=episode_id,
            shot_id=shot_id,
        )

        # No durable render receipt means there is nothing to compare against.
        # Avoid building the full Director runtime merely to display
        # "Not Rendered" in Creator UI.
        if existing is None:
            return ShotRenderRecord(
                episode_id=episode_id,
                scene_id=scene_id,
                shot_id=shot_id,
                source_fingerprint="",
                storyboard_approval_fingerprint=(
                    frame.review_source_fingerprint
                ),
                status="missing",
                video_path=expected_path,
                duration_seconds=shot.duration_seconds,
                fps=self.fps,
                width=self.width,
                height=self.height,
                frame_count=max(
                    1,
                    round(shot.duration_seconds * self.fps),
                ),
            )

        session = self.director.build(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
        )
        if (
            existing.source_fingerprint != session.source_fingerprint
            or not frame.approved_current
            or existing.storyboard_approval_fingerprint
            != frame.review_source_fingerprint
        ):
            return existing.model_copy(update={"status": "stale"})

        video_path = self.project_root / existing.video_path
        if existing.status == "rendered" and not self._valid_mp4(video_path):
            return existing.model_copy(update={"status": "missing"})
        return existing

    def render_shot(
        self,
        *,
        episode_id: str,
        scene_id: str,
        shot_id: str,
    ) -> ShotRenderRecord:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        frame = self.storyboard.status_for(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
        )
        if not frame.approved_current:
            raise ValueError(
                "Storyboard must be current and Approved before rendering."
            )

        session = self.director.build(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
        )
        relative_video = self._video_relative_path(
            episode_id=episode_id,
            shot_id=shot_id,
        )
        video_path = self.project_root / relative_video
        video_path.parent.mkdir(parents=True, exist_ok=True)

        frame_count = max(
            1,
            round(session.duration_seconds * self.fps),
        )
        record = ShotRenderRecord(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
            source_fingerprint=session.source_fingerprint,
            storyboard_approval_fingerprint=(
                frame.review_source_fingerprint
            ),
            status="rendering",
            video_path=relative_video,
            duration_seconds=session.duration_seconds,
            fps=self.fps,
            width=self.width,
            height=self.height,
            frame_count=frame_count,
        )
        episode.shot_renders[shot_id] = record
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)

        frame_dir = self._frame_dir(
            episode_id=episode_id,
            shot_id=shot_id,
        )
        if frame_dir.exists():
            shutil.rmtree(frame_dir)
        frame_dir.mkdir(parents=True, exist_ok=True)

        request = {
            "schema_version": "1.0",
            "output_dir": (
                "res://runtime_state/shot_frames/"
                + episode_id
                + "/"
                + shot_id
            ),
            "fps": self.fps,
            "frame_count": frame_count,
            "width": self.width,
            "height": self.height,
            "director_session": session.model_dump(mode="json"),
        }
        self.request_path.parent.mkdir(parents=True, exist_ok=True)
        self.request_path.write_text(
            json.dumps(request, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        try:
            if video_path.exists():
                video_path.unlink()
            if self.render_runner is not None:
                self.render_runner(self.request_path, video_path)
            else:
                self._capture_frames()
                self._encode_mp4(frame_dir, video_path)

            if not self._valid_mp4(video_path):
                raise RuntimeError(
                    "Shot render did not produce a valid MP4."
                )
            record = record.model_copy(
                update={
                    "status": "rendered",
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
        finally:
            if frame_dir.exists():
                shutil.rmtree(frame_dir, ignore_errors=True)

        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found after render: {episode_id}")
        episode.shot_renders[shot_id] = record
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return record

    def video_bytes(self, record: ShotRenderRecord) -> bytes | None:
        path = self.project_root / record.video_path
        if not self._valid_mp4(path):
            return None
        return path.read_bytes()

    def _capture_frames(self) -> None:
        godot = self._resolve_godot_binary()
        if godot is None:
            raise RuntimeError(
                "Godot capture engine is unavailable on this computer."
            )
        completed = subprocess.run(
            [
                godot,
                "--path",
                str(self.godot_root),
                "--rendering-method",
                "gl_compatibility",
                "--resolution",
                f"{self.width}x{self.height}",
                "--script",
                "res://scripts/shot_frame_capture.gd",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                "Godot Shot capture failed"
                + (f": {details[-1000:]}" if details else ".")
            )

    def _encode_mp4(self, frame_dir: Path, video_path: Path) -> None:
        ffmpeg = self._resolve_ffmpeg_binary()
        if ffmpeg is None:
            raise RuntimeError(
                "Video encoder is unavailable. Install ffmpeg to render MP4."
            )
        completed = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-framerate",
                str(self.fps),
                "-i",
                str(frame_dir / "frame_%05d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(video_path),
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                "MP4 encoding failed"
                + (f": {details[-1000:]}" if details else ".")
            )

    @staticmethod
    def _resolve_godot_binary() -> str | None:
        explicit = (
            os.environ.get("MINI_UTOPIA_GODOT_BIN")
            or os.environ.get("GODOT_BIN")
        )
        candidates = [
            explicit,
            shutil.which("godot"),
            shutil.which("godot4"),
            "/Applications/Godot.app/Contents/MacOS/Godot",
        ]
        return next(
            (
                str(value)
                for value in candidates
                if value and Path(value).exists()
            ),
            None,
        )

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

    def _frame_dir(self, *, episode_id: str, shot_id: str) -> Path:
        return (
            self.godot_root
            / "runtime_state"
            / "shot_frames"
            / episode_id
            / shot_id
        )

    @staticmethod
    def _video_relative_path(*, episode_id: str, shot_id: str) -> str:
        return (
            "godot/runtime_state/renders/"
            + episode_id
            + "/"
            + shot_id
            + ".mp4"
        )

    @staticmethod
    def _valid_mp4(path: Path) -> bool:
        if not path.exists() or path.stat().st_size < 12:
            return False
        try:
            header = path.read_bytes()[:32]
        except OSError:
            return False
        return b"ftyp" in header

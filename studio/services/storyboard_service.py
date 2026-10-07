from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from studio.models.asset import now_utc
from studio.models.storyboard import StoryboardFrameRecord
from studio.repositories.base import StudioRepository
from studio.services.director_shot_session_service import (
    DirectorShotSessionService,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GODOT_ROOT = PROJECT_ROOT / "godot"
STORYBOARD_ROOT = GODOT_ROOT / "runtime_state" / "storyboards"
CAPTURE_REQUEST_PATH = (
    GODOT_ROOT / "runtime_state" / "storyboard_capture_request.json"
)


class StoryboardService:
    """Create and track deterministic Godot storyboard frames per Shot."""

    def __init__(
        self,
        repository: StudioRepository,
        director: DirectorShotSessionService,
        *,
        capture_runner: Callable[[Path], None] | None = None,
        project_root: str | Path | None = None,
    ):
        self.repository = repository
        self.director = director
        self.capture_runner = capture_runner
        self.project_root = (
            Path(project_root)
            if project_root is not None
            else PROJECT_ROOT
        )
        self.godot_root = self.project_root / "godot"
        self.capture_request_path = (
            self.godot_root
            / "runtime_state"
            / "storyboard_capture_request.json"
        )

    def status_for(
        self,
        *,
        episode_id: str,
        scene_id: str,
        shot_id: str,
    ) -> StoryboardFrameRecord:
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

        existing = episode.storyboard_frames.get(shot_id)
        expected_path = self._frame_relative_path(
            episode_id=episode_id,
            shot_id=shot_id,
        )

        # A not-yet-generated planning frame has no durable source artifact to
        # invalidate. Keep this read-only status path lightweight: Episodes can
        # show progress without materializing the full Character/World runtime
        # (including GLB bytes) once per Shot.
        if existing is None:
            return StoryboardFrameRecord(
                episode_id=episode_id,
                scene_id=scene_id,
                shot_id=shot_id,
                source_fingerprint="",
                status="missing",
                frame_path=expected_path,
                capture_time_seconds=round(shot.duration_seconds * 0.5, 3),
                camera_summary=self._camera_summary_from_shot(shot),
                blocking_summary=self._blocking_summary_from_shot(shot),
            )

        session = self.director.build(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
        )
        frame_exists = self._valid_png(self.project_root / existing.frame_path)
        if existing.source_fingerprint != session.source_fingerprint:
            return existing.model_copy(
                update={
                    "status": "stale",
                    "error": "",
                }
            )
        if existing.status == "ready" and not frame_exists:
            return existing.model_copy(
                update={
                    "status": "missing",
                    "error": "",
                }
            )
        if frame_exists and existing.status != "failed":
            return existing.model_copy(update={"status": "ready"})
        return existing

    def generate_frame(
        self,
        *,
        episode_id: str,
        scene_id: str,
        shot_id: str,
    ) -> StoryboardFrameRecord:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        session = self.director.build(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
        )
        relative_path = self._frame_relative_path(
            episode_id=episode_id,
            shot_id=shot_id,
        )
        output_path = self.project_root / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        record = StoryboardFrameRecord(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
            source_fingerprint=session.source_fingerprint,
            status="missing",
            frame_path=relative_path,
            capture_time_seconds=round(session.duration_seconds * 0.5, 3),
            camera_summary=self._camera_summary(session),
            blocking_summary=self._blocking_summary(session),
        )
        episode.storyboard_frames[shot_id] = record
        self.repository.save_episode(episode)

        request = {
            "schema_version": "1.0",
            "output_path": (
                "res://runtime_state/storyboards/"
                + episode_id
                + "/"
                + shot_id
                + ".png"
            ),
            "capture_time_seconds": record.capture_time_seconds,
            "director_session": session.model_dump(mode="json"),
        }
        self.capture_request_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.capture_request_path.write_text(
            json.dumps(request, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        try:
            if self.capture_runner is not None:
                self.capture_runner(self.capture_request_path)
            else:
                self._run_godot_capture()

            if not self._valid_png(output_path):
                raise RuntimeError("Storyboard capture did not produce a valid PNG.")

            record = record.model_copy(
                update={
                    "status": "ready",
                    "generated_at": now_utc(),
                    "error": "",
                    "review_status": "unreviewed",
                    "review_note": "",
                    "review_source_fingerprint": "",
                    "reviewed_at": None,
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
            raise ValueError(f"Episode not found after capture: {episode_id}")
        episode.storyboard_frames[shot_id] = record
        self.repository.save_episode(episode)
        return record

    def review_frame(
        self,
        *,
        episode_id: str,
        scene_id: str,
        shot_id: str,
        review_status: str,
        note: str = "",
    ) -> StoryboardFrameRecord:
        if review_status not in {"approved", "needs_change"}:
            raise ValueError(
                "review_status must be approved or needs_change."
            )

        frame = self.status_for(
            episode_id=episode_id,
            scene_id=scene_id,
            shot_id=shot_id,
        )
        if frame.status != "ready":
            raise ValueError(
                "Storyboard frame must be current and Ready before review."
            )

        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        reviewed = frame.model_copy(
            update={
                "review_status": review_status,
                "review_note": note.strip(),
                "review_source_fingerprint": frame.source_fingerprint,
                "reviewed_at": now_utc(),
            }
        )
        episode.storyboard_frames[shot_id] = reviewed
        self.repository.save_episode(episode)
        return reviewed

    def frame_bytes(self, record: StoryboardFrameRecord) -> bytes | None:
        path = self.project_root / record.frame_path
        if not self._valid_png(path):
            return None
        return path.read_bytes()

    def _run_godot_capture(self) -> None:
        binary = self._resolve_godot_binary()
        if binary is None:
            raise RuntimeError(
                "Storyboard capture engine is unavailable on this computer."
            )
        completed = subprocess.run(
            [
                binary,
                "--path",
                str(self.godot_root),
                "--rendering-method",
                "gl_compatibility",
                "--resolution",
                "960x540",
                "--script",
                "res://scripts/storyboard_capture.gd",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                "Storyboard capture failed"
                + (f": {details[-800:]}" if details else ".")
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
                str(candidate)
                for candidate in candidates
                if candidate and Path(candidate).exists()
            ),
            None,
        )

    @staticmethod
    def _frame_relative_path(*, episode_id: str, shot_id: str) -> str:
        return (
            "godot/runtime_state/storyboards/"
            + episode_id
            + "/"
            + shot_id
            + ".png"
        )

    @staticmethod
    def _valid_png(path: Path) -> bool:
        if not path.exists() or path.stat().st_size <= 8:
            return False
        try:
            return path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        except OSError:
            return False

    @staticmethod
    def _camera_summary(session) -> str:
        camera = session.camera
        return (
            f"{camera.movement_mode} · "
            f"FOV {camera.fov:.0f}"
            + (f" → {camera.end_fov:.0f}" if camera.end_fov else "")
        )

    @staticmethod
    def _camera_summary_from_shot(shot) -> str:
        motion = shot.camera_motion
        if motion is None:
            return shot.camera.strip() or shot.shot_type or "Planned camera"
        return (
            f"{motion.movement_mode} · "
            f"FOV {motion.start_fov:.0f}"
            + (
                f" → {motion.end_fov:.0f}"
                if motion.end_fov != motion.start_fov
                else ""
            )
        )

    @staticmethod
    def _blocking_summary(session) -> str:
        return StoryboardService._blocking_summary_from_shot(session.shot)

    @staticmethod
    def _blocking_summary_from_shot(shot) -> str:
        blocking = shot.blocking
        if blocking is None:
            return "No blocking"
        start = blocking.actor_start
        end = blocking.actor_end
        return (
            f"{blocking.movement_style} · "
            f"({start.x:.1f},{start.z:.1f}) → "
            f"({end.x:.1f},{end.z:.1f})"
        )

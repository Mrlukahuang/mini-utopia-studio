from __future__ import annotations

import hashlib
from pathlib import Path

from studio.models.asset import now_utc
from studio.models.audio_timeline import EpisodeAudioLine
from studio.models.subtitle_track import (
    SubtitleCue,
    SubtitleTrackSummary,
)
from studio.repositories.base import StudioRepository


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class SubtitleTrackService:
    """Deterministic subtitles derived from the Episode Audio Timeline."""

    def __init__(
        self,
        repository: StudioRepository,
        *,
        project_root: str | Path | None = None,
    ):
        self.repository = repository
        self.project_root = (
            Path(project_root)
            if project_root is not None
            else PROJECT_ROOT
        )

    def ensure_track(
        self,
        episode_id: str,
        *,
        replace_stale: bool = False,
    ):
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        existing = {
            cue.source_audio_line_id: cue
            for cue in episode.subtitle_track
        }
        cues: list[SubtitleCue] = []
        for line in sorted(
            episode.audio_timeline,
            key=lambda item: (item.start_seconds, item.line_id),
        ):
            fingerprint = self.audio_fingerprint(line)
            old = existing.get(line.line_id)
            if (
                old is not None
                and old.source_fingerprint == fingerprint
            ):
                cues.append(old)
                continue
            if old is not None and not replace_stale:
                cues.append(old)
                continue
            cues.append(
                self._cue_from_audio(
                    line,
                    fingerprint=fingerprint,
                )
            )

        episode.subtitle_track = sorted(
            cues,
            key=lambda cue: (cue.start_seconds, cue.cue_id),
        )
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return episode

    def refresh_cue(
        self,
        *,
        episode_id: str,
        cue_id: str,
    ) -> SubtitleCue:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        cue = next(
            (
                value
                for value in episode.subtitle_track
                if value.cue_id == cue_id
            ),
            None,
        )
        if cue is None:
            raise ValueError(f"Subtitle cue not found: {cue_id}")
        line = next(
            (
                value
                for value in episode.audio_timeline
                if value.line_id == cue.source_audio_line_id
            ),
            None,
        )
        if line is None:
            raise ValueError(
                f"Source audio line not found: {cue.source_audio_line_id}"
            )

        refreshed = self._cue_from_audio(
            line,
            fingerprint=self.audio_fingerprint(line),
        )
        episode.subtitle_track = [
            refreshed if value.cue_id == cue_id else value
            for value in episode.subtitle_track
        ]
        episode.subtitle_track.sort(
            key=lambda value: (value.start_seconds, value.cue_id)
        )
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return refreshed

    def update_cue(
        self,
        *,
        episode_id: str,
        cue_id: str,
        start_seconds: float,
        end_seconds: float,
        text: str,
        speaker_label: str,
        approved: bool,
    ) -> SubtitleCue:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        clean = text.strip()
        if not clean:
            raise ValueError("Subtitle text is required.")
        if float(end_seconds) <= float(start_seconds):
            raise ValueError("Subtitle end must be after start.")

        updated: SubtitleCue | None = None
        values: list[SubtitleCue] = []
        for cue in episode.subtitle_track:
            if cue.cue_id != cue_id:
                values.append(cue)
                continue
            updated = cue.model_copy(
                update={
                    "start_seconds": float(start_seconds),
                    "end_seconds": float(end_seconds),
                    "text": clean,
                    "speaker_label": speaker_label.strip(),
                    "approved": bool(approved),
                    "source": "creator",
                }
            )
            values.append(updated)
        if updated is None:
            raise ValueError(f"Subtitle cue not found: {cue_id}")

        episode.subtitle_track = sorted(
            values,
            key=lambda cue: (cue.start_seconds, cue.cue_id),
        )
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return updated

    def status_for(
        self,
        *,
        episode_id: str,
        cue: SubtitleCue,
    ) -> str:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        line = next(
            (
                value
                for value in episode.audio_timeline
                if value.line_id == cue.source_audio_line_id
            ),
            None,
        )
        if line is None:
            return "stale"
        return (
            "ready"
            if cue.source_fingerprint == self.audio_fingerprint(line)
            else "stale"
        )

    def summary(self, episode_id: str) -> SubtitleTrackSummary:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        statuses = [
            self.status_for(
                episode_id=episode_id,
                cue=cue,
            )
            for cue in episode.subtitle_track
        ]
        return SubtitleTrackSummary(
            cue_count=len(episode.subtitle_track),
            ready_count=sum(status == "ready" for status in statuses),
            stale_count=sum(status == "stale" for status in statuses),
            approved_count=sum(
                cue.approved and status == "ready"
                for cue, status in zip(episode.subtitle_track, statuses)
            ),
        )

    def srt_text(self, episode_id: str) -> str:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")

        blocks: list[str] = []
        index = 1
        for cue in sorted(
            episode.subtitle_track,
            key=lambda value: (value.start_seconds, value.cue_id),
        ):
            if self.status_for(episode_id=episode_id, cue=cue) != "ready":
                continue
            blocks.append(
                "\n".join(
                    [
                        str(index),
                        (
                            f"{self._srt_time(cue.start_seconds)} --> "
                            f"{self._srt_time(cue.end_seconds)}"
                        ),
                        cue.text,
                    ]
                )
            )
            index += 1
        return "\n\n".join(blocks) + ("\n" if blocks else "")

    def export_srt(self, episode_id: str) -> Path:
        text = self.srt_text(episode_id)
        target = (
            self.project_root
            / "godot"
            / "runtime_state"
            / "subtitles"
            / f"{episode_id}.srt"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def _cue_from_audio(
        self,
        line: EpisodeAudioLine,
        *,
        fingerprint: str,
    ) -> SubtitleCue:
        return SubtitleCue(
            cue_id=self._cue_id(line.line_id),
            source_audio_line_id=line.line_id,
            source_fingerprint=fingerprint,
            start_seconds=line.start_seconds,
            end_seconds=line.end_seconds,
            text=line.text,
            speaker_label=self._speaker_label(line),
            approved=False,
            source="generated",
        )

    def _speaker_label(self, line: EpisodeAudioLine) -> str:
        if line.speaker_kind == "narrator":
            return "Narrator"
        if line.speaker_asset_id:
            asset = self.repository.get_asset(line.speaker_asset_id)
            if asset is not None:
                return asset.display_name
        return ""

    @staticmethod
    def audio_fingerprint(line: EpisodeAudioLine) -> str:
        raw = "|".join(
            [
                line.line_id,
                line.speaker_kind,
                line.speaker_asset_id or "",
                line.text,
                f"{line.start_seconds:.3f}",
                f"{line.duration_seconds:.3f}",
                line.emotion,
                line.delivery_note,
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()

    @staticmethod
    def _cue_id(audio_line_id: str) -> str:
        digest = hashlib.sha256(
            audio_line_id.encode("utf-8")
        ).hexdigest()[:12].upper()
        return f"SUB_{digest}"

    @staticmethod
    def _srt_time(seconds: float) -> str:
        milliseconds = max(0, round(float(seconds) * 1000))
        hours, milliseconds = divmod(milliseconds, 3_600_000)
        minutes, milliseconds = divmod(milliseconds, 60_000)
        whole_seconds, milliseconds = divmod(milliseconds, 1000)
        return (
            f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},"
            f"{milliseconds:03d}"
        )

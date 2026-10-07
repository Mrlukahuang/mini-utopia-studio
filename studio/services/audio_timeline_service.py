from __future__ import annotations

import hashlib
import re

from studio.models.asset import now_utc
from studio.models.audio_timeline import (
    AudioTimelineSummary,
    EpisodeAudioLine,
)
from studio.repositories.base import StudioRepository


DEFAULT_SCENE_NOTE = (
    "Add dialogue or narration only where it helps the beat."
)


class AudioTimelineService:
    """Provider-neutral, deterministic Episode dialogue/narration timeline."""

    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def ensure_baseline(
        self,
        episode_id: str,
        *,
        replace: bool = False,
    ):
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        if episode.audio_timeline and not replace:
            return episode

        existing = {
            line.line_id: line
            for line in episode.audio_timeline
        }
        lines: list[EpisodeAudioLine] = []
        episode_cursor = 0.0

        for scene in episode.scenes:
            scene_start = episode_cursor
            scene_shots = list(scene.shots)
            for shot in scene_shots:
                shot_start = episode_cursor
                dialogue = list(shot.dialogue)
                if dialogue:
                    slot = max(
                        0.35,
                        shot.duration_seconds / max(1, len(dialogue)),
                    )
                    for index, dialogue_line in enumerate(dialogue):
                        text = dialogue_line.text.strip()
                        if not text:
                            continue
                        line_id = self._line_id(
                            scene.scene_id,
                            shot.shot_id,
                            "dialogue",
                            index,
                        )
                        start = shot_start + min(
                            shot.duration_seconds - 0.2,
                            0.15 + index * slot,
                        )
                        duration = min(
                            self._estimate_duration(text),
                            max(0.2, shot_start + shot.duration_seconds - start),
                        )
                        prior = existing.get(line_id)
                        lines.append(
                            EpisodeAudioLine(
                                line_id=line_id,
                                scene_id=scene.scene_id,
                                shot_id=shot.shot_id,
                                speaker_kind="character",
                                speaker_asset_id=dialogue_line.character_asset_id,
                                text=text,
                                start_seconds=round(start, 3),
                                duration_seconds=round(duration, 3),
                                emotion=dialogue_line.emotion,
                                source="generated",
                                approved=(
                                    prior.approved
                                    if prior is not None
                                    and prior.text == text
                                    else False
                                ),
                            )
                        )
                episode_cursor += shot.duration_seconds

            note = scene.dialogue_notes.strip()
            if (
                note
                and note != DEFAULT_SCENE_NOTE
                and scene_shots
            ):
                first_shot = scene_shots[0]
                line_id = self._line_id(
                    scene.scene_id,
                    first_shot.shot_id,
                    "narration",
                    0,
                )
                available = max(
                    0.2,
                    min(
                        first_shot.duration_seconds,
                        episode_cursor - scene_start,
                    ),
                )
                duration = min(
                    self._estimate_duration(note),
                    available,
                )
                prior = existing.get(line_id)
                lines.append(
                    EpisodeAudioLine(
                        line_id=line_id,
                        scene_id=scene.scene_id,
                        shot_id=first_shot.shot_id,
                        speaker_kind="narrator",
                        text=note,
                        start_seconds=round(scene_start + 0.1, 3),
                        duration_seconds=round(duration, 3),
                        delivery_note="Scene narration",
                        source="generated",
                        approved=(
                            prior.approved
                            if prior is not None
                            and prior.text == note
                            else False
                        ),
                    )
                )

        episode.audio_timeline = sorted(
            lines,
            key=lambda line: (line.start_seconds, line.line_id),
        )
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return episode

    def add_narration(
        self,
        *,
        episode_id: str,
        scene_id: str,
        shot_id: str,
        text: str,
    ):
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        clean = text.strip()
        if not clean:
            raise ValueError("Narration text is required.")

        shot_start = self._shot_start_seconds(
            episode,
            scene_id=scene_id,
            shot_id=shot_id,
        )
        shot = self._shot(
            episode,
            scene_id=scene_id,
            shot_id=shot_id,
        )
        salt = 0
        used = {line.line_id for line in episode.audio_timeline}
        while True:
            line_id = self._line_id(
                scene_id,
                shot_id,
                "creator_narration",
                salt,
            )
            if line_id not in used:
                break
            salt += 1

        episode.audio_timeline.append(
            EpisodeAudioLine(
                line_id=line_id,
                scene_id=scene_id,
                shot_id=shot_id,
                speaker_kind="narrator",
                text=clean,
                start_seconds=round(shot_start + 0.1, 3),
                duration_seconds=round(
                    min(
                        self._estimate_duration(clean),
                        max(0.2, shot.duration_seconds - 0.1),
                    ),
                    3,
                ),
                source="creator",
            )
        )
        episode.audio_timeline.sort(
            key=lambda line: (line.start_seconds, line.line_id)
        )
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return episode

    def update_line(
        self,
        *,
        episode_id: str,
        line_id: str,
        speaker_kind: str,
        speaker_asset_id: str | None,
        text: str,
        start_seconds: float,
        duration_seconds: float,
        emotion: str,
        delivery_note: str,
        approved: bool,
    ):
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        clean = text.strip()
        if not clean:
            raise ValueError("Audio line text is required.")
        if speaker_kind not in {"character", "narrator"}:
            raise ValueError("Invalid audio speaker kind.")

        found = False
        updated = []
        for line in episode.audio_timeline:
            if line.line_id != line_id:
                updated.append(line)
                continue
            found = True
            updated.append(
                EpisodeAudioLine(
                    line_id=line.line_id,
                    scene_id=line.scene_id,
                    shot_id=line.shot_id,
                    speaker_kind=speaker_kind,
                    speaker_asset_id=(
                        speaker_asset_id
                        if speaker_kind == "character"
                        else None
                    ),
                    text=clean,
                    start_seconds=float(start_seconds),
                    duration_seconds=float(duration_seconds),
                    emotion=emotion.strip(),
                    delivery_note=delivery_note.strip(),
                    source="creator",
                    approved=bool(approved),
                )
            )
        if not found:
            raise ValueError(f"Audio line not found: {line_id}")

        episode.audio_timeline = sorted(
            updated,
            key=lambda line: (line.start_seconds, line.line_id),
        )
        episode.updated_at = now_utc()
        self.repository.save_episode(episode)
        return episode

    def summary(self, episode_id: str) -> AudioTimelineSummary:
        episode = self.repository.get_episode(episode_id)
        if episode is None:
            raise ValueError(f"Episode not found: {episode_id}")
        lines = sorted(
            episode.audio_timeline,
            key=lambda line: (line.start_seconds, line.line_id),
        )
        overlaps: set[str] = set()
        for index, left in enumerate(lines):
            for right in lines[index + 1 :]:
                if right.start_seconds >= left.end_seconds:
                    break
                if (
                    right.start_seconds < left.end_seconds
                    and right.end_seconds > left.start_seconds
                ):
                    overlaps.add(left.line_id)
                    overlaps.add(right.line_id)

        return AudioTimelineSummary(
            line_count=len(lines),
            approved_count=sum(line.approved for line in lines),
            total_spoken_seconds=round(
                sum(line.duration_seconds for line in lines),
                3,
            ),
            episode_end_seconds=round(
                max(
                    (
                        line.end_seconds
                        for line in lines
                    ),
                    default=0.0,
                ),
                3,
            ),
            overlap_line_ids=sorted(overlaps),
        )

    def _shot_start_seconds(
        self,
        episode,
        *,
        scene_id: str,
        shot_id: str,
    ) -> float:
        cursor = 0.0
        for scene in episode.scenes:
            for shot in scene.shots:
                if (
                    scene.scene_id == scene_id
                    and shot.shot_id == shot_id
                ):
                    return cursor
                cursor += shot.duration_seconds
        raise ValueError(f"Shot not found: {shot_id}")

    @staticmethod
    def _shot(episode, *, scene_id: str, shot_id: str):
        for scene in episode.scenes:
            if scene.scene_id != scene_id:
                continue
            for shot in scene.shots:
                if shot.shot_id == shot_id:
                    return shot
        raise ValueError(f"Shot not found: {shot_id}")

    @staticmethod
    def _line_id(
        scene_id: str,
        shot_id: str,
        kind: str,
        index: int,
    ) -> str:
        raw = f"{scene_id}|{shot_id}|{kind}|{index}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()
        return f"AUDIO_{digest}"

    @staticmethod
    def _estimate_duration(text: str) -> float:
        cjk_count = len(re.findall(r"[\u3400-\u9fff]", text))
        latin_words = len(
            re.findall(r"[A-Za-z0-9']+", text)
        )
        punctuation_pause = min(
            1.4,
            len(re.findall(r"[,.!?;，。！？；]", text)) * 0.12,
        )
        seconds = (
            cjk_count / 4.2
            + latin_words / 2.6
            + punctuation_pause
        )
        return max(0.8, min(20.0, seconds))

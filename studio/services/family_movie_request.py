"""Validate a private 15-30 second Director capture."""

def family_capture_request(session: dict, fps: int = 6) -> dict:
    duration = session.get("duration_seconds")
    if not isinstance(duration, (float, int)) or isinstance(duration, bool):
        raise ValueError("Invalid duration")
    if not 15 <= duration <= 30 or not 1 <= fps <= 12:
        raise ValueError("Family movie must be 15-30 seconds")
    return {"fps": fps, "frame_count": round(duration * fps), "director_session": session}
